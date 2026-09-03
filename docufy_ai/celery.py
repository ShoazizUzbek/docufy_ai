import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docufy_ai.settings')

app = Celery('docufy_ai')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
