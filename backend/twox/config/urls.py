"""Root URL configuration."""

from django.urls import URLPattern, URLResolver, path

from twox.config.health import HealthView

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/v1/health/", HealthView.as_view(), name="health"),
]
