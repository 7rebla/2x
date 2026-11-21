"""Static file finders.

Only the admin's app folder is searched for static files. The other installed
apps stay out; above all the assets of the DRF browsable API, which is
switched off (JSON only), must not be shipped.
"""

from collections.abc import Sequence

from django.contrib.staticfiles.finders import AppDirectoriesFinder

ADMIN_APP_NAME = "django.contrib.admin"


class AdminAppDirectoriesFinder(AppDirectoriesFinder):
    """Find the static files of ``django.contrib.admin`` and of no other app.

    The admin's folder includes the licence files of the libraries it ships
    (``admin/js/vendor/jquery``, ``select2``, ``xregexp``); they are collected
    and served along with the code.
    """

    def __init__(self, app_names: Sequence[str] | None = None) -> None:
        # Whatever the caller asks for, only the admin is searched.
        super().__init__([ADMIN_APP_NAME])
