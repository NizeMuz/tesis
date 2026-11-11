"""
Comando para esperar a que la base de datos esté lista antes de iniciar la app.
Útil en Docker para sincronizar el inicio del contenedor web con el de la BD.
"""
import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Espera a que la base de datos esté disponible'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-retries',
            type=int,
            default=30,
            help='Número máximo de intentos (default: 30)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=2,
            help='Segundos entre intentos (default: 2)'
        )

    def handle(self, *args, **options):
        max_retries = options['max_retries']
        interval = options['interval']

        self.stdout.write(self.style.NOTICE('Esperando a que la base de datos esté lista...'))

        for attempt in range(1, max_retries + 1):
            try:
                # Intentar conectar a la base de datos por defecto
                db_conn = connections['default']
                db_conn.ensure_connection()

                # Si llegamos aquí, la conexión fue exitosa
                self.stdout.write(
                    self.style.SUCCESS(
                        f'¡Base de datos disponible! (intento {attempt}/{max_retries})'
                    )
                )
                return

            except OperationalError as e:
                if attempt == max_retries:
                    self.stdout.write(
                        self.style.ERROR(
                            f'No se pudo conectar a la base de datos después de {max_retries} intentos.'
                        )
                    )
                    self.stdout.write(self.style.ERROR(f'Último error: {e}'))
                    raise
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Intento {attempt}/{max_retries}: BD no lista, '
                            f'esperando {interval}s... ({e})'
                        )
                    )
                    time.sleep(interval)