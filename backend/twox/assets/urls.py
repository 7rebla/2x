"""API endpoints of the assets app, mounted below /api/v1/."""

from django.urls import URLPattern, URLResolver
from rest_framework.routers import SimpleRouter

from twox.assets.views import AreaViewSet, DeviceViewSet, PlantViewSet, SiteViewSet

# SimpleRouter: no API root view and no format suffixes, only the four paths
# and their detail paths.
router = SimpleRouter()
router.register("sites", SiteViewSet, basename="site")
router.register("areas", AreaViewSet, basename="area")
router.register("plants", PlantViewSet, basename="plant")
router.register("devices", DeviceViewSet, basename="device")

urlpatterns: list[URLPattern | URLResolver] = [*router.urls]
