"""App configuration for twox.assets."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AssetsConfig(AppConfig):
    name = "twox.assets"
    verbose_name = _("Structure")
