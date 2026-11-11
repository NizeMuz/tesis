"""
Configuración de Celery para el proyecto Serviu.
Usa la base de datos como broker y backend de resultados.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Establecer el módulo de configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serviu.settings')

app = Celery('serviu')

# Cargar configuración desde Django settings con namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubrir tareas automáticamente en todas las apps instaladas
app.autodiscover_tasks(['serviuapp'])

# Importar tareas explícitamente para asegurar registro
# Esto se ejecuta cuando Django ya está configurado
import serviuapp.tasks

# Configuración de beat (tareas periódicas) - se gestiona desde admin con django-celery-beat
app.conf.beat_schedule = {
    # Ejemplo: limpiar logs antiguos cada día a las 3 AM
    # 'limpiar-logs-diario': {
    #     'task': 'serviuapp.tasks.limpiar_logs_antiguos',
    #     'schedule': crontab(hour=3, minute=0),
    # },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tarea de depuración para verificar que Celery funciona"""
    print(f'Request: {self.request!r}')