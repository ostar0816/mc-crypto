import json

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from pankow.models import TradePlan


class Command(BaseCommand):
    """
    Command to create TradePlan.

    Parameters: user_id, loop, amount, exec_type, check_balance in order

    Example usage::

        manage.py create_tradeplan 1 '[["gdax","USD","BTC"],["gdax","BTC","USD"],["gemini","USD","BTC"],["gemini","BTC","USD"]]' '[["gdax","250"],["gemini","20"]]' sequential True
    """
    help = 'Create TradePlan model with user_id, loop, amount, exec_type, check_balance'

    def add_arguments(self, parser):
        parser.add_argument('args', metavar='params', nargs='*')

    def handle(self, *params, **options):
        user_id, loop, amount, exec_type, check_balance = params
        try:
            loop = json.loads(loop)
            amount = json.loads(amount)
            check_balance = check_balance == 'True' or check_balance == 'true'
            TradePlan.objects.create(
                user_id=user_id,
                loop=loop,
                amount=amount,
                exec_type=exec_type,
                check_balance=check_balance
            )
        except (DatabaseError, json.JSONDecodeError) as e:
            raise CommandError("Invalid arguments")
