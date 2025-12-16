import sys
import os

sys.path.insert(0, "/home/maverixt/repositories/serviuapp")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "serviu.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()