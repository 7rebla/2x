"""API views of the structure: sites, areas, plants and devices.

Reading needs the role ``read`` or ``manage``, writing the role ``manage``
(E-40). There is no delete in M1 (E-41): only superusers delete, in the admin.
Lists are not paginated; the structure of one operation is small.

The operation ids come from drf-spectacular (``sites_list``, ``sites_create``,
``sites_retrieve``, ``sites_update``, ``sites_partial_update`` and so on);
tests/assets/test_api.py pins them, because the web client is named after them.

Writes run in a savepoint: a unique constraint that a request running at the
same time hit first gives 400 at the field, not 500 (:func:`save_checked`).

The CSV import of the device list (:class:`DeviceImportView`) needs the role
``manage``.
"""

from typing import cast

from django.db import IntegrityError, transaction
from django.db.models import Model, QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from twox.accounts.models import User
from twox.accounts.permissions import CanManage, CanManageOrReadOnly
from twox.assets.csv_import import apply, parse
from twox.assets.integrity import unique_violation
from twox.assets.models import Area, Device, Plant, Site
from twox.assets.serializers import (
    AreaSerializer,
    DeviceImportFormSerializer,
    DeviceSerializer,
    DeviceWriteSerializer,
    ImportReportSerializer,
    PlantSerializer,
    SiteSerializer,
)
from twox.files.serializers import ErrorDetailSerializer
from twox.files.uploads import LimitedUploadView

# Largest value of a bigint column; larger ids cannot exist.
MAX_ID = 2**63 - 1


def id_parameter(name: str, description: str) -> OpenApiParameter:
    """A query parameter that filters a list by the id of a parent."""
    return OpenApiParameter(name, OpenApiTypes.INT, OpenApiParameter.QUERY, description=description)


def query_id(request: Request, name: str) -> int | None:
    """Return the id in the query parameter ``name``, or ``None`` if it is not given.

    A value that is no valid id gives 400 with an error at ``name``.
    """
    raw = request.query_params.get(name)
    if raw is None:
        return None
    field = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    try:
        value: int = field.run_validation(raw)
    except serializers.ValidationError as error:
        raise serializers.ValidationError({name: error.detail}) from error
    return value


def save_checked[M: Model](serializer: serializers.ModelSerializer[M]) -> M:
    """Save a validated serializer; a unique constraint hit at the same time gives 400.

    The serializer checked uniqueness already, but a request running at the
    same time can save the same name or key in between. The database
    constraint then refuses the write. The savepoint keeps the rest of the
    request usable, and the error is reported at the field, with the message
    of the serializer's own check. Any other integrity error stays a 500.
    """
    try:
        with transaction.atomic():
            return serializer.save()
    except IntegrityError as error:
        violation = unique_violation(error)
        if violation is None:
            raise
        raise serializers.ValidationError({violation.field: [str(violation.message)]}) from error


class StructureViewSet[M: Model](
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet[M],
):
    """List, read, create and change; no delete."""

    permission_classes = (CanManageOrReadOnly,)

    def perform_create(self, serializer: serializers.BaseSerializer[M]) -> None:
        save_checked(cast("serializers.ModelSerializer[M]", serializer))

    def perform_update(self, serializer: serializers.BaseSerializer[M]) -> None:
        save_checked(cast("serializers.ModelSerializer[M]", serializer))


class SiteViewSet(StructureViewSet[Site]):
    """Sites of the operation."""

    queryset = Site.objects.all()
    serializer_class = SiteSerializer


@extend_schema_view(
    list=extend_schema(parameters=[id_parameter("site", "Only areas of the site with this id.")]),
)
class AreaViewSet(StructureViewSet[Area]):
    """Areas of the sites."""

    queryset = Area.objects.all()
    serializer_class = AreaSerializer

    def get_queryset(self) -> QuerySet[Area]:
        queryset = super().get_queryset()
        if self.action == "list":
            site = query_id(self.request, "site")
            if site is not None:
                queryset = queryset.filter(site_id=site)
        return queryset


@extend_schema_view(
    list=extend_schema(parameters=[id_parameter("area", "Only plants of the area with this id.")]),
)
class PlantViewSet(StructureViewSet[Plant]):
    """Plants of the areas."""

    queryset = Plant.objects.all()
    serializer_class = PlantSerializer

    def get_queryset(self) -> QuerySet[Plant]:
        queryset = super().get_queryset()
        if self.action == "list":
            area = query_id(self.request, "area")
            if area is not None:
                queryset = queryset.filter(area_id=area)
        return queryset


@extend_schema_view(
    list=extend_schema(
        parameters=[
            id_parameter("plant", "Only devices of the plant with this id."),
            id_parameter("site", "Only devices of the site with this id (through area and plant)."),
        ],
    ),
    create=extend_schema(
        request=DeviceWriteSerializer,
        responses={status.HTTP_201_CREATED: DeviceSerializer},
    ),
    update=extend_schema(request=DeviceWriteSerializer, responses=DeviceSerializer),
    partial_update=extend_schema(request=DeviceWriteSerializer, responses=DeviceSerializer),
)
class DeviceViewSet(StructureViewSet[Device]):
    """Devices of the plants, each with its chain plant > area > site.

    Writes take the plant as an id (``DeviceWrite``); every answer shows the
    device as it is read (``Device``).
    """

    # One query for a whole list: the chain comes with the device.
    queryset = Device.objects.select_related("plant__area__site")
    serializer_class = DeviceSerializer

    def get_queryset(self) -> QuerySet[Device]:
        queryset = super().get_queryset()
        if self.action == "list":
            plant = query_id(self.request, "plant")
            if plant is not None:
                queryset = queryset.filter(plant_id=plant)
            site = query_id(self.request, "site")
            if site is not None:
                queryset = queryset.filter(plant__area__site_id=site)
        return queryset

    def answer(self, device: Device, status_code: int = status.HTTP_200_OK) -> Response:
        """The device as it is read, with the chain loaded in the same query."""
        loaded = self.get_queryset().get(pk=device.pk)
        return Response(
            DeviceSerializer(loaded, context=self.get_serializer_context()).data,
            status=status_code,
        )

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        serializer = DeviceWriteSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        return self.answer(save_checked(serializer), status.HTTP_201_CREATED)

    def update(self, request: Request, *args: object, **kwargs: object) -> Response:
        # partial_update() of the mixin calls this with partial=True.
        serializer = DeviceWriteSerializer(
            self.get_object(),
            data=request.data,
            partial=kwargs.get("partial") is True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        return self.answer(save_checked(serializer))


class DeviceImportView(LimitedUploadView):
    """Import of a device list as CSV (E-44); see ``twox.assets.csv_import``."""

    permission_classes = (CanManage,)

    @extend_schema(
        operation_id="devices_import",
        request={"multipart/form-data": DeviceImportFormSerializer},
        responses={
            200: ImportReportSerializer,
            400: OpenApiResponse(description="Invalid form: no file, or dry_run no boolean."),
            403: OpenApiResponse(ErrorDetailSerializer, description="Not the role manage."),
            413: OpenApiResponse(
                ErrorDetailSerializer, description="Larger than TWOX_UPLOAD_MAX_BYTES."
            ),
        },
    )
    def post(self, request: Request) -> Response:
        """Check a device list and, without dry run, save it.

        A dry run (the default) checks the file and counts what an import
        would create, update or leave unchanged, and saves nothing. Without
        dry run everything is saved in one transaction, or nothing if any row
        has an error. Errors in the file come back in ``errors`` with line and
        column, with status 200; ``saved`` tells whether anything was saved.
        """
        form = DeviceImportFormSerializer(data=self.upload_data(request))
        form.is_valid(raise_exception=True)
        user = request.user
        if not isinstance(user, User):  # CanManage lets only accounts through
            raise PermissionDenied
        parsed = parse(form.validated_data["file"])
        report = apply(parsed, user, dry_run=form.validated_data["dry_run"])
        return Response(ImportReportSerializer(report).data)
