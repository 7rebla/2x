"""Health endpoint: tells a container runtime that the API process answers."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthSerializer(serializers.Serializer[dict[str, str]]):
    """Shape of the health response, used for the OpenAPI schema."""

    status = serializers.ChoiceField(choices=["ok"])


class HealthView(APIView):
    """Open to everyone on purpose: container health checks carry no credentials."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(operation_id="health_retrieve", responses=HealthSerializer)
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})
