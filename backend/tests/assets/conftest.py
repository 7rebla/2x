"""Fixtures of the structure tests: a small structure and signed-in API clients."""

from collections.abc import Callable
from dataclasses import dataclass

import pytest
from rest_framework.test import APIClient

from tests.accounts.users import make_user
from twox.assets.models import Area, Device, Plant, Site

type ClientFactory = Callable[[str], APIClient]


@dataclass(frozen=True)
class Structure:
    """Two sites; both have an area of the same name, each with plants and devices."""

    north: Site
    south: Site
    north_line: Area
    south_line: Area
    press: Plant
    welder: Plant
    paint: Plant
    press_plc: Device
    press_hmi: Device
    welder_plc: Device
    paint_plc: Device


@pytest.fixture
def structure(db: None) -> Structure:
    north = Site.objects.create(name="North")
    south = Site.objects.create(name="South")
    north_line = Area.objects.create(site=north, name="Line 1")
    south_line = Area.objects.create(site=south, name="Line 1")
    press = Plant.objects.create(area=north_line, key="press", name="Press")
    welder = Plant.objects.create(area=north_line, key="welder", name="Welder")
    paint = Plant.objects.create(area=south_line, key="paint", name="Paint shop")
    return Structure(
        north=north,
        south=south,
        north_line=north_line,
        south_line=south_line,
        press=press,
        welder=welder,
        paint=paint,
        press_plc=Device.objects.create(
            plant=press, key="press-plc", name="Press PLC", ip_address="192.0.2.10"
        ),
        press_hmi=Device.objects.create(plant=press, key="press-hmi", name="Press HMI"),
        welder_plc=Device.objects.create(
            plant=welder, key="welder-plc", name="Welder PLC", ip_address="192.0.2.20"
        ),
        paint_plc=Device.objects.create(
            plant=paint, key="paint-plc", name="Paint PLC", ip_address="2001:db8::30"
        ),
    )


@pytest.fixture
def client_for(db: None) -> ClientFactory:
    """Return an API client signed in as a user of a kind (see tests.accounts.users).

    Each kind can be used once per test.
    """

    def make(kind: str) -> APIClient:
        client = APIClient()
        user = make_user(kind)
        if user is not None:
            client.force_login(user)
        return client

    return make
