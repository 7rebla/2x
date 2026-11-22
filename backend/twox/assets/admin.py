"""The structure in the admin, which admits superusers only (E-39).

Deleting is possible here only (E-41); PROTECT keeps a site, area or plant
that still has children.
"""

from typing import TYPE_CHECKING

from django.contrib import admin

from twox.assets.models import Area, Device, Plant, Site

# ModelAdmin is generic for the type checker only; at runtime it cannot be
# subscripted (that would need django-stubs-ext in the runtime image).
if TYPE_CHECKING:
    SiteAdminBase = admin.ModelAdmin[Site]
    AreaAdminBase = admin.ModelAdmin[Area]
    PlantAdminBase = admin.ModelAdmin[Plant]
    DeviceAdminBase = admin.ModelAdmin[Device]
else:
    SiteAdminBase = AreaAdminBase = PlantAdminBase = DeviceAdminBase = admin.ModelAdmin


@admin.register(Site)
class SiteAdmin(SiteAdminBase):
    list_display = ("name", "updated_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Area)
class AreaAdmin(AreaAdminBase):
    list_display = ("name", "site", "updated_at")
    list_filter = ("site",)
    list_select_related = ("site",)
    search_fields = ("name", "site__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Plant)
class PlantAdmin(PlantAdminBase):
    list_display = ("key", "name", "area", "updated_at")
    list_filter = ("area__site", "area")
    list_select_related = ("area",)
    search_fields = ("key", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Device)
class DeviceAdmin(DeviceAdminBase):
    list_display = (
        "key",
        "name",
        "device_class",
        "plant",
        "manufacturer",
        "ip_address",
        "updated_at",
    )
    list_filter = ("device_class", "plant__area__site", "plant__area", "plant")
    list_select_related = ("plant",)
    search_fields = ("key", "name", "ip_address")
    readonly_fields = ("created_at", "updated_at")
