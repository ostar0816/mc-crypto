import os
import time
import pickle
import configurations

from django.utils import timezone
from celery import Celery, Task
from decimal import Decimal as D

from yosei import get_exchange_instance
from yosei.ua_const import UA_RES, OrderStatus
from romulus import MG
from pankow.const import TaskState, OrderRetry, LoopTag, DebugLevel

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shore.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Dev')

configurations.setup()

app = Celery('pankow_server')
app.conf.update(
    task_serializer='pickle',
    result_serializer='pickle',
    accept_content=['pickle'],
    result_backend='rpc://localhost//',
    backend='rpc://localhost//',
    broker='amqp://localhost//',
)

# Don't move this import before calling configurations.setup(), otherwise
# pankow tasks can't access shore.settings because they run independentely
# with manage.py
from pankow.models import ActionLog

DEBUG_LV = DebugLevel.INTERNAL


class Balance:
    trade_type = 'balance'

    def __init__(self, **kwargs):
        self.update_request(**kwargs)

    def update_request(self, **kwargs):
        self.exch = kwargs['exch']
        self.ticker = kwargs['ticker']
        self.exch_api = get_exchange_instance(self.exch)

    def check_balance(self):
        # yosei def balance(self, currency, debug=False):
        res = self.exch_api.balance(
            self.ticker, DEBUG_LV >= DebugLevel.INTERNAL)
        return res


class Order:
    trade_type = 'order'

    def __init__(self, **kwargs):
        self.update_request(**kwargs)

    def update_request(self, **kwargs):
        loop = kwargs['loop']
        exch, ticker1, ticker2 = loop[0]
        pairs = MG.get(exch)['pairs']

        self.exch = exch
        self.amount = kwargs['amount']
        self.side = None
        if (ticker1, ticker2) in pairs:
            self.side = 'sell'
            self.pair = (ticker1, ticker2)
        elif (ticker2, ticker1) in pairs:
            self.side = 'buy'
            self.pair = (ticker2, ticker1)

        if self.side is not None:
            self.exch_api = get_exchange_instance(self.exch)
            return True

        return False

    def do_trade(self):
        # Place an order
        # yosei def place_order(self, currency_pair, amount, side='buy',
        # order_type='market', debug=False):
        res = self.exch_api.place_order(self.pair, str(
            self.amount), self.side, DEBUG_LV >= DebugLevel.INTERNAL)
        return res

    # Check status until it fails or completed after placing an order
    def check_order_status(self, order_id=0):
        if order_id != 0:
            self.order_id = order_id

        res = None
        status_loop_count = 0
        kwargs = {
            'side': self.side,
            'currency_pair': self.pair,
        }
        while status_loop_count < OrderRetry.STATUS_LOOP_COUNT:
            # yosei def order_status(self, order_id):
            res = self.exch_api.order_status(
                self.order_id, DEBUG_LV >= DebugLevel.INTERNAL, **kwargs)
            order_status = res['order_status']
            if res['code'] != UA_RES.ERR_NONE or order_status == OrderStatus.COMPLETED or order_status == OrderStatus.CANCELED:
                break

            status_loop_count += 1
            time.sleep(OrderRetry.STATUS_INTERVAL)

        if status_loop_count == OrderRetry.STATUS_LOOP_COUNT:
            res = self.exch_api.cancel_order(
                self.order_id, DEBUG_LV >= DebugLevel.INTERNAL)

        return status_loop_count, res


class BaseTask(Task):
    # Send a message to the client and update database
    def update_action_log(self, **kwargs):
        status = kwargs['status']
        retry_count = kwargs['retry_count']
        start_time = kwargs['start_time']
        exchange = kwargs['exchange']
        loop_num = kwargs['loop_num']
        loop_tag = kwargs['loop_tag']
        additional_info = kwargs['additional_info']
        trade_plan = kwargs['trade_plan']

        status = status.value
        loop_tag = loop_tag.value
        if additional_info.get('code') is not None:
            del additional_info['code']
        if additional_info.get('message') is not None:
            del additional_info['message']
        if additional_info.get('order_status') is not None:
            additional_info['order_status'] = additional_info['order_status'].value

        additional_info['status'] = status
        additional_info['loop_num'] = loop_num
        additional_info['loop_tag'] = loop_tag
        additional_info['retry_count'] = retry_count
        additional_info['timestamp'] = time.time()

        # Send a message to the client
        self.update_state(state=status, meta=additional_info)

        # Update postgresql
        action_log = ActionLog(
            start_time=start_time,
            exchange=exchange,
            loop_num=loop_num,
            loop_tag=loop_tag,
            additional_info=additional_info,
            trade_plan=trade_plan)
        action_log.save()

        trade_plan.status = status
        trade_plan.save()


class ExchangeTask(BaseTask):
    def init_task(self, trade_plan, req, amount):
        self.trade_plan = pickle.loads(trade_plan)
        self.loop = req
        self.amount = D(amount)
        self.payload = {}
        self.loop_num = 0
        self.order_retry_count = 0
        self.start_time = timezone.now()

    def get_payload(self):
        self.payload['loop'] = self.loop
        self.payload['amount'] = self.amount
        return self.payload

    def gen_active_loop(self):
        if len(self.loop) == 0:
            return False

        payload = self.get_payload()
        self.active_trade = Order(**payload)

        return True

    def pop_active_loop(self):
        if len(self.loop) == 0:
            return False

        del self.loop[0]
        self.loop_num += 1
        self.order_retry_count = 0

        return True

    def is_task_finished(self):
        return len(self.loop) == 0

    def is_last_loop(self):
        return len(self.loop) == 1

    def build_action_log(self, status, loop_tag, additional_info):
        action_log = {
            'status': status,
            'retry_count': self.order_retry_count,
            'start_time': self.start_time,
            'exchange': self.active_trade.exch,
            'loop_num': self.loop_num,
            'loop_tag': loop_tag,
            'additional_info': additional_info,
            'trade_plan': self.trade_plan,
        }
        return action_log


@app.task(bind=True, base=ExchangeTask)
def run_trades(self, could_continue, trade_plan, req, amount):
    if not could_continue:
        return False

    self.init_task(trade_plan, req, amount)

    # Trading main loop
    while not self.is_task_finished():
        if not self.gen_active_loop():
            return False

        if self.active_trade.trade_type == 'order':
            order_res = self.active_trade.do_trade()
            # Post market order. Success?
            if order_res['code'] == UA_RES.ERR_NONE:
                action_log = self.build_action_log(
                    TaskState.STATE_PROGRESS, LoopTag.PLACE_ORDER, order_res)
                self.update_action_log(**action_log)
                self.status_retry_count, order_res = self.active_trade.check_order_status(
                    order_res['order_id'])
                # Finally completed the order
                if order_res['code'] == UA_RES.ERR_NONE and order_res['order_status'] == OrderStatus.COMPLETED:
                    self.amount = D(order_res['net_profit'])
                    if self.is_last_loop():
                        action_log = self.build_action_log(
                            TaskState.STATE_SUCCESS, LoopTag.ORDER_STATUS, order_res)
                        self.update_action_log(**action_log)
                        return True
                    else:
                        action_log = self.build_action_log(
                            TaskState.STATE_STEP_PASSED, LoopTag.ORDER_STATUS, order_res)
                        self.update_action_log(**action_log)
                        self.pop_active_loop()

                    self.order_retry_count = 0
                elif order_res['code'] != UA_RES.ERR_NONE:
                    action_log = self.build_action_log(
                        TaskState.STATE_FAILED, LoopTag.ORDER_STATUS, order_res)
                    self.update_action_log(**action_log)
                    return False
                else:  # order was canceled, try again
                    if self.order_retry_count + 1 >= OrderRetry.ORDER_COUNT:
                        action_log = self.build_action_log(
                            TaskState.STATE_FAILED, LoopTag.ORDER_STATUS, order_res)
                        self.update_action_log(**action_log)
                        return False
                    else:
                        action_log = self.build_action_log(
                            TaskState.STATE_PROGRESS, LoopTag.ORDER_STATUS, order_res)
                        self.update_action_log(**action_log)

                    self.order_retry_count += 1

            # Post market order, Fail!
            else:
                action_log = self.build_action_log(
                    TaskState.STATE_FAILED, LoopTag.PLACE_ORDER, order_res)
                self.update_action_log(**action_log)
                return False  # Finsh task


class CheckBalanceTask(BaseTask):
    def init_task(self, trade_plan, req):
        self.trade_plan = pickle.loads(trade_plan)
        self.exch, self.ticker, self.amount = req
        self.amount = D(self.amount)
        self.start_time = timezone.now()

        balance_payload = {
            'exch': self.exch,
            'ticker': self.ticker,
        }
        # Check balance of source exchange before placing order
        self.balance = Balance(**balance_payload)

    def build_action_log(self, status, loop_tag, additional_info):
        action_log = {
            'status': status,
            'retry_count': 0,
            'start_time': self.start_time,
            'exchange': self.exch,
            'loop_num': 0,
            'loop_tag': loop_tag,
            'additional_info': additional_info,
            'trade_plan': self.trade_plan,
        }
        return action_log


@app.task(bind=True, base=CheckBalanceTask)
def check_balance(self, trade_plan, payload):
    self.init_task(trade_plan, payload)
    balance_res = self.balance.check_balance()
    # Check balance at source exchange. Good?
    if balance_res['code'] != UA_RES.ERR_NONE:
        action_log = self.build_action_log(
            TaskState.STATE_FAILED, LoopTag.BALANCE, balance_res)
        self.update_action_log(**action_log)
        return False  # Finish task
    else:
        available = D(balance_res['available'])
        # Check balance at source exchange, No!
        if available < self.amount:
            action_log = self.build_action_log(
                TaskState.STATE_FAILED, LoopTag.BALANCE, balance_res)
            self.update_action_log(**action_log)
            return False  # Finish task
        # Check balance at source exchange, Good!
        else:
            action_log = self.build_action_log(
                TaskState.STATE_PROGRESS, LoopTag.BALANCE, balance_res)
            self.update_action_log(**action_log)

    return True
