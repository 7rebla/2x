"""Helpers of the files API tests: devices, signed-in clients, raw multipart bodies."""

from pathlib import Path
from typing import TYPE_CHECKING

from rest_framework.test import APIClient

from tests.accounts.users import make_user
from twox.assets.models import Area, Device, Plant, Site

if TYPE_CHECKING:
    # Exists in the type stubs only; annotations are not evaluated at runtime.
    from rest_framework.response import _MonkeyPatchedResponse


def make_device(key: str = "dps-plc") -> Device:
    """A device in a small structure; several keys share site, area and plant."""
    site, _ = Site.objects.get_or_create(name="Test site")
    area, _ = Area.objects.get_or_create(site=site, name="Production line")
    plant, _ = Plant.objects.get_or_create(area=area, key="aps-dps", name="Goods in and out")
    return Device.objects.create(plant=plant, key=key, name=f"Device {key}")


def client_for(kind: str) -> APIClient:
    """An API client signed in as a user of ``kind`` (see tests.accounts.users)."""
    client = APIClient()
    user = make_user(kind)
    if user is not None:
        client.force_login(user)
    return client


BOUNDARY = "twox-test-boundary"


def multipart_body(
    filename: str, content: bytes, content_type: str, fields: dict[str, str] | None = None
) -> bytes:
    """A ``multipart/form-data`` body with one file part named ``file``.

    Unlike the test client, the file name goes out unchanged, path parts
    included.
    """
    parts = [
        (
            f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        ).encode()
        for name, value in (fields or {}).items()
    ]
    parts.append(
        (
            f"--{BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
        + content
        + b"\r\n"
    )
    parts.append(f"--{BOUNDARY}--\r\n".encode())
    return b"".join(parts)


MULTIPART_CONTENT_TYPE = f"multipart/form-data; boundary={BOUNDARY}"


def post_multipart(
    client: APIClient, url: str, body: bytes, headers: dict[str, str] | None = None
) -> _MonkeyPatchedResponse:
    """POST a body from :func:`multipart_body` as it is."""
    # The stubs declare str; Django's test client sends bytes unchanged.
    return client.generic(
        "POST",
        url,
        body,  # type: ignore[arg-type]
        MULTIPART_CONTENT_TYPE,
        headers=headers,
    )


def files_below(directory: Path) -> list[Path]:
    """Every file below ``directory`` (empty if it does not exist)."""
    return sorted(p for p in directory.rglob("*") if p.is_file()) if directory.exists() else []
