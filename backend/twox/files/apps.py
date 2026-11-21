"""App configuration for twox.files."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FilesConfig(AppConfig):
    name = "twox.files"
    verbose_name = _("Files")
