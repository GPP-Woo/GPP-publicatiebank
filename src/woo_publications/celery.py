from celery import Celery

from .setup import setup_env

setup_env()

app = Celery("woo_publications")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
