"""Root URL configuration. Routes are added by later work orders."""

from django.urls import URLPattern, URLResolver

urlpatterns: list[URLPattern | URLResolver] = []
