import os
import sys

# Ruta absoluta al proyecto
PROJECT_ROOT = '/home/maverixt/repositories/serviuapp'
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "serviu.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
