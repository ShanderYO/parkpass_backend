from __future__ import absolute_import

import os

from parkpass_backend import settings
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parkpass_backend.settings')

app = Celery('parkpass_backend')
app.config_from_object('django.conf:settings')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)