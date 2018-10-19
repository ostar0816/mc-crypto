import json
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    """
    Command for auto-trading.

    Parameters: a complete trade plan payload

    Example usage::

        python manage.py autotrade "{'loop': [['gdax','USD','BTC'], ['gdax','BTC','USD'], ['gemini', 'USD', 'BTC'], ['gemini', 'BTC', 'USD']], 'amount': [['gdax', '100'], ['gemini', '20']], 'exec_type': 'parallel', 'check_balance': true, 'user_id': 1}"
    """
    help = 'python manage.py autotrade payload'

    def add_arguments(self, parser):
        parser.add_argument('args', metavar='params', nargs='*')

    def handle(self, *params, **options):
        try:
            # Expecting property name enclosed in double quotes
            payload = params[0].replace("'", '"')
            start_ws_client(payload)
        except (json.JSONDecodeError, IndexError) as e:
            raise CommandError("Invalid arguments")


from autobahn.asyncio.websocket import WebSocketClientProtocol, \
    WebSocketClientFactory

global_payload = ""
class MyClientProtocol(WebSocketClientProtocol):
    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    def onOpen(self):
        print("WebSocket connection open.")
        global global_payload
        self.sendMessage(global_payload.encode('utf8'), isBinary=False)

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            print("Text message received: {0}".format(payload.decode('utf8')))

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))

def start_ws_client(payload):
    try:
        import asyncio
    except ImportError:
        # Trollius >= 0.3 was renamed
        import trollius as asyncio

    global global_payload
    global_payload = payload
    port_num = 9999
    factory = WebSocketClientFactory(f"ws://127.0.0.1:{port_num}")
    factory.protocol = MyClientProtocol

    loop = asyncio.get_event_loop()
    coro = loop.create_connection(factory, '127.0.0.1', port_num)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()
