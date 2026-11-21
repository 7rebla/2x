"""The user model in the admin, which admits superusers only (E-39)."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from twox.accounts.models import User

admin.site.register(User, UserAdmin)
