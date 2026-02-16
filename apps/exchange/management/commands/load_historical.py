from datetime import date
from django.core.management.base import BaseCommand, CommandError

from apps.exchange.application.tasks import load_historical_data


class Command(BaseCommand):
    help = 'Load historical exchange rate data for a date range'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from',
            dest='date_from',
            type=str,
            required=True,
            help='Start date in YYYY-MM-DD format'
        )
        parser.add_argument(
            '--to',
            dest='date_to',
            type=str,
            required=True,
            help='End date in YYYY-MM-DD format'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Execute synchronously instead of using Celery task queue'
        )

    def handle(self, **options):
        date_from_str = options['date_from']
        date_to_str = options['date_to']
        sync_mode = options['sync']

        try:
            date_from = date.fromisoformat(date_from_str)
            date_to = date.fromisoformat(date_to_str)
        except ValueError:
            raise CommandError('Invalid date format. Use YYYY-MM-DD')

        if date_from > date_to:
            raise CommandError('date_from must be before or equal to date_to')

        self.stdout.write(
            self.style.SUCCESS(
                f'Loading historical data from {date_from_str} to {date_to_str}...'
            )
        )

        if sync_mode:
            self.stdout.write('Running in synchronous mode...')
            result = load_historical_data(date_from_str, date_to_str)

            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully loaded {result['rates_loaded']} rates"
                    )
                )
                if result.get('errors'):
                    self.stdout.write(
                        self.style.WARNING(
                            f"Errors: {len(result['errors'])}"
                        )
                    )
            else:
                raise CommandError(f"Failed: {result.get('message', 'Unknown error')}")
        else:
            self.stdout.write('Dispatching Celery task...')
            task = load_historical_data.delay(date_from_str, date_to_str)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Task dispatched with ID: {task.id}'
                )
            )
            self.stdout.write(
                'Use "celery -A core inspect active" to check task status'
            )
