from autobahn.asyncio.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory
import asyncio
import pickle
import json
from decimal import Decimal as D
import copy

from celery import chain, group

from pankow.const import TaskState, LoopTag, ExecutionType
from pankow.models import TradePlan
import pankow.exch_tasks as PANKOW_TASKS


class PankowServerProtocol(WebSocketServerProtocol):
    def __init__(self):
        super().__init__()

    def onConnect(self, request):
        print("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        print("WebSocket connection open.")

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            try:
                req = json.loads(payload.decode('utf8'))
                print(f"Payload received: {req}")
            except json.JSONDecodeError:
                print(f"Invalid payload: {payload}")
                self._send_payload_error()
            else:
                self.run_celery_task(req)

    def on_task_message(self, body):
        result = body['result']
        if isinstance(result, ConnectionError):
            self._send_connection_error()
        elif isinstance(result, dict):
            print(result)
            if result.get('org_res') is not None:
                del result['org_res']
            self.sendMessage(json.dumps(result).encode('utf8'))

    def _send_connection_error(self):
        res = {
            'status': TaskState.STATE_FAILED.value,
            'loop_num': 0,
            'loop_tag': LoopTag.CONNECTION_ERROR.value,
        }
        self.sendMessage(json.dumps(res).encode('utf8'))

    def _send_payload_error(self):
        res = {
            'status': TaskState.STATE_FAILED.value,
            'loop_num': 0,
            'loop_tag': LoopTag.VERIFY_PAYLOAD.value,
        }
        self.sendMessage(json.dumps(res).encode('utf8'))

    def _serialize_obj(self, obj):
        return pickle.dumps(obj, -1)

    def _init_trade_plan(self, req):
        success = True
        try:
            # Create trade plan with request from the frontend
            self.trade_plan = self._create_trade_plan(**req)
            if self.trade_plan is not None:
                loop = copy.deepcopy(self.trade_plan.loop)
                self.amount_list = copy.deepcopy(self.trade_plan.amount)
                self.exec_type = self.trade_plan.exec_type
                self.check_balance = self.trade_plan.check_balance

                # Verify payload
                loop_len = len(loop)
                amount_len = len(self.amount_list)
                success = loop_len > 1 and amount_len > 0
                for exch, ticker1, ticker2 in loop:
                    if len(exch) == 0 or ticker1 == ticker2:
                        success = False
                        break
                for exch, amount in self.amount_list:
                    amount = D(amount)
                    if len(exch) == 0 or amount <= 0:
                        success = False
                        break
                if not success:
                    return success

                # Split loop per exchange
                sub_loop_index, exch_index, start_currency_index = 0, 0, 1
                prev_exch = loop[sub_loop_index][exch_index]
                sub_loop = []
                self.loop_list = []
                self.amount_list[sub_loop_index].insert(
                    start_currency_index, loop[sub_loop_index][start_currency_index])
                for li in loop:
                    exch = li[exch_index]
                    if prev_exch != exch:
                        prev_exch = exch
                        self.loop_list.append(sub_loop)
                        sub_loop = []
                        sub_loop.append(li)
                        sub_loop_index += 1
                        self.amount_list[sub_loop_index].insert(
                            start_currency_index, li[start_currency_index])
                    else:
                        sub_loop.append(li)
                self.loop_list.append(sub_loop)
                print(
                    f"loop_list = {self.loop_list}\n amount_list = {self.amount_list}")
            else:
                success = False
        except (KeyError, AttributeError, IndexError, TradePlan.DoesNotExist) as e:
            print(e)
            success = False

        return success

    def _create_trade_plan(self, **kwargs):
        loop = kwargs['loop']
        amount = kwargs['amount']
        exec_type = kwargs['exec_type']
        check_balance = kwargs['check_balance']
        user_id = kwargs['user_id']
        trade_plan = TradePlan.objects.create(
            loop=loop, amount=amount,
            exec_type=exec_type,
            check_balance=check_balance,
            user_id=user_id
        )
        return trade_plan

    def _update_trade_plan(self, status):
        self.trade_plan.status = status
        self.trade_plan.save()

    def _update_final_status(self, status):
        res = {
            'status': status,
            'loop_num': 0,
            'loop_tag': LoopTag.FINAL_STATUS.value,
        }
        self.sendMessage(json.dumps(res).encode('utf8'))
        self._update_trade_plan(status)

    def run_celery_task(self, req):
        if self._init_trade_plan(req):
            serialized_trade_plan = self._serialize_obj(self.trade_plan)
            could_continue = True
            # Check balances for all exchanges
            if self.check_balance:
                check_balance_list = []
                for amount in self.amount_list:
                    task = PANKOW_TASKS.check_balance.s(
                        serialized_trade_plan, amount)
                    check_balance_list.append(task)
                check_balance_job = group(check_balance_list)
                res = check_balance_job.apply_async()
                res_list = res.get(
                    on_message=self.on_task_message,
                    propagate=False)
                could_continue = all(res_list)
            # Continue auto-trading if check_balances are success
            if could_continue:
                trade_list = []
                i, amount_index = 0, 2
                while i < len(self.loop_list):
                    loop = self.loop_list[i]
                    amount = self.amount_list[i][amount_index]
                    if i == 0 or self.exec_type == ExecutionType.PARALLEL.value:
                        task = PANKOW_TASKS.run_trades.s(
                            True, serialized_trade_plan, loop, amount)
                    else:  # SEQUENTIAL
                        task = PANKOW_TASKS.run_trades.s(
                            serialized_trade_plan, loop, amount)
                    trade_list.append(task)
                    i += 1

                if self.exec_type == ExecutionType.PARALLEL.value:
                    trade_job = group(trade_list)
                else:  # SEQUENTIAL
                    trade_job = chain(trade_list)
                res = trade_job.apply_async()
                res_list = res.get(
                    on_message=self.on_task_message,
                    propagate=False)

                # Check the final status
                completed = False
                print(f"res_list = {res_list}")
                if self.exec_type == ExecutionType.PARALLEL.value:
                    completed = all(res_list)
                else:  # SEQUENTIAL
                    completed = res_list
                if completed:
                    final_status = TaskState.STATE_COMPLETED.value
                else:
                    final_status = TaskState.STATE_FAILED.value
                self._update_final_status(final_status)
        else:
            self._send_payload_error()


def main():
    port_num = 9999
    factory = WebSocketServerFactory(f"ws://127.0.0.1:{port_num}")
    factory.protocol = PankowServerProtocol

    loop = asyncio.get_event_loop()
    coro = loop.create_server(factory, '0.0.0.0', port_num)
    server = loop.run_until_complete(coro)
    print(f"listening port ws://127.0.0.1:{port_num}")

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.close()
