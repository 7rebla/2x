"""Project configuration. Importing it makes the Celery application available."""

from twox.config.celery import app as celery_app

__all__ = ("celery_app",)
