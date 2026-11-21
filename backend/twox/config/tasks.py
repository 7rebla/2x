"""Tasks that belong to no app."""

from twox.config.celery import app


@app.task(name="twox.config.ping")
def ping() -> str:
    """Return ``pong``: proves that a task reaches a worker and its result comes back."""
    return "pong"
