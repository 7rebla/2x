"""Celery application of twox.

Start a worker with ``celery -A twox.config worker``. All settings come from
the Django settings with the prefix ``CELERY_``.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "twox.config.settings")

# twox.config is not a Django app, so its tasks are listed here by hand.
app = Celery("twox", include=["twox.config.tasks"])
app.config_from_object("django.conf:settings", namespace="CELERY")
# Finds the module ``tasks`` of every installed app.
app.autodiscover_tasks()
