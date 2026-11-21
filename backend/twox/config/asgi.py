"""ASGI entry point."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "twox.config.settings")

django_application = get_asgi_application()

# Imported once Django is set up: the module loads DRF and its settings.
from twox.files.uploads import RequestBodyLimitMiddleware  # noqa: E402

# Django reads a whole request body into a temporary file before any view
# runs. The middleware refuses bodies above the upload limit first.
application = RequestBodyLimitMiddleware(django_application)
