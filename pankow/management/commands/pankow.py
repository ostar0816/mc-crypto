from django.core.management.base import BaseCommand, CommandError

from pankow.pankow_server import main


class Command(BaseCommand):
    help = 'Run pankow server'

    def add_argument(self, parser):
        pass

    def handle(self, *args, **options):
        try:
            main()
        except Exception as e:
            CommandError(repr(e))
