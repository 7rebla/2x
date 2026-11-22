"""Structure of the operation: site > area > plant > device.

The depth is fixed, so plain foreign keys are enough. The device fields follow
the columns of ``testfactory/layout/devices.csv`` one to one as free text; only
the IP address is a checked field. Keys of plants and devices are unique in the
whole system (one operation, no tenants).
"""

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

KEY_MAX_LENGTH = 64
NAME_MAX_LENGTH = 200

validate_key = RegexValidator(
    regex=r"^[a-z0-9-]+$",
    message=_("Use only lowercase letters, digits and hyphens."),
    code="invalid_key",
)


class TimestampedModel(models.Model):
    """Adds creation and change time to a model."""

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True


class Site(TimestampedModel):
    """A location of the operation, for example a factory."""

    name = models.CharField(_("name"), max_length=NAME_MAX_LENGTH)

    class Meta:
        ordering = ("name",)
        verbose_name = _("site")
        verbose_name_plural = _("sites")
        constraints = (models.UniqueConstraint(fields=["name"], name="assets_site_name_unique"),)

    def __str__(self) -> str:
        return self.name


class Area(TimestampedModel):
    """A part of a site, for example a production line."""

    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="areas",
        verbose_name=_("site"),
    )
    name = models.CharField(_("name"), max_length=NAME_MAX_LENGTH)

    class Meta:
        ordering = ("name",)
        verbose_name = _("area")
        verbose_name_plural = _("areas")
        constraints = (
            models.UniqueConstraint(fields=["site", "name"], name="assets_area_site_name_unique"),
        )

    def __str__(self) -> str:
        return self.name


class Plant(TimestampedModel):
    """A plant (module, cell) within an area; it holds the devices."""

    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="plants",
        verbose_name=_("area"),
    )
    key = models.CharField(_("key"), max_length=KEY_MAX_LENGTH, validators=[validate_key])
    name = models.CharField(_("name"), max_length=NAME_MAX_LENGTH)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        ordering = ("key",)
        verbose_name = _("plant")
        verbose_name_plural = _("plants")
        constraints = (models.UniqueConstraint(fields=["key"], name="assets_plant_key_unique"),)

    def __str__(self) -> str:
        return f"{self.name} ({self.key})"


class DeviceClass(models.TextChoices):
    """The kind of a device, a fixed choice (E-53); the web UI picks its icon by it."""

    PLC = "plc", _("PLC")
    CONTROLLER = "controller", _("Controller / embedded")
    COMPUTER = "computer", _("Computer / edge")
    ROUTER = "router", _("Router")
    FIREWALL = "firewall", _("Firewall")
    ROBOT = "robot", _("Robot")
    OTHER = "other", _("Other")


#: Longest value of :class:`DeviceClass`, with room for a few more.
DEVICE_CLASS_MAX_LENGTH = 20


class Device(TimestampedModel):
    """A device of a plant, for example a PLC or a controller."""

    plant = models.ForeignKey(
        Plant,
        on_delete=models.PROTECT,
        related_name="devices",
        verbose_name=_("plant"),
    )
    key = models.CharField(_("key"), max_length=KEY_MAX_LENGTH, validators=[validate_key])
    name = models.CharField(_("name"), max_length=NAME_MAX_LENGTH)
    device_class = models.CharField(
        _("device class"),
        max_length=DEVICE_CLASS_MAX_LENGTH,
        choices=DeviceClass.choices,
        default=DeviceClass.OTHER,
    )
    manufacturer = models.TextField(_("manufacturer"), blank=True)
    model = models.TextField(_("model"), blank=True)
    software_version = models.TextField(_("software version"), blank=True)
    # An empty address is stored as NULL; an empty string is no valid inet value.
    ip_address = models.GenericIPAddressField(_("IP address"), blank=True, null=True)
    address_source = models.TextField(_("address source"), blank=True)
    protocols = models.TextField(_("protocols"), blank=True)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        ordering = ("key",)
        verbose_name = _("device")
        verbose_name_plural = _("devices")
        constraints = (models.UniqueConstraint(fields=["key"], name="assets_device_key_unique"),)

    def __str__(self) -> str:
        return f"{self.name} ({self.key})"
