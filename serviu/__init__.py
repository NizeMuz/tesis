# This file is intentionally left empty to mark the directory as a Python package.
# It allows Python to import modules from this directory.

from .celery import app as celery_app

__all__ = ('celery_app',)