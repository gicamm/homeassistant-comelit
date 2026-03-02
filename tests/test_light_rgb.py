"""RGB light tests.

The fixtures (hub_status_rgb_on/off.json) are real captures from a
production SimpleHome hub (serial 002529174B6A). Note the protocol
quirk they document: an ON RGB light reports ``status: "7"`` (not
``"1"`` like on/off lights), and the hub retains ``bright``/
``rgb_value`` even while the light is off.

Historical bug: ``ComelitLight.color_mode`` returned the *set*
``{ColorMode.RGB}`` for RGB lights instead of the single
``ColorMode.RGB`` enum. HA core evaluates ``color_mode.value`` while
computing state attributes, so every state write for an RGB light
raised ``AttributeError`` and the entity was stuck at its initial
(off) state while the physical light happily turned on.
"""

import json
import os
from unittest.mock import MagicMock, patch

from homeassistant.components.light import ColorMode
from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.comelit.hub import ComelitHub
from custom_components.comelit.light import ComelitLight

RGB_ID = "DOM#LT#48.1"  # "Bagno RGB", a real light on the captured hub


def load_fixture(name):
    filename = os.path.join(os.path.dirname(__file__), name)
    with open(filename, "r") as json_file:
        return json.load(json_file)


def make_hub():
    with patch("paho.mqtt.client.Client"):
        hub = ComelitHub(
            client_name="test",
            hub_serial="00000000",
            hub_host="127.0.0.1",
            hub_user="user",
            hub_password="pwd",
            mqtt_port=1883,
            mqtt_user="user",
            mqtt_password="pwd",
            scan_interval=30,
        )
    for name in ("sensor", "light", "cover", "climate", "scene", "switch"):
        setattr(hub, f"{name}_add_entities", lambda *args, **kwargs: None)
    return hub


# --- light entity: color_mode must be a single ColorMode -----------------


def test_rgb_light_color_mode():
    light = ComelitLight(RGB_ID, "Bagno RGB", STATE_OFF, 123, (16, 66, 248), MagicMock())

    # must be a single enum value, not a set: HA core does `color_mode.value`
    assert isinstance(light.color_mode, ColorMode)
    assert light.color_mode == ColorMode.RGB
    assert light.color_mode.value == "rgb"
    assert light.color_mode in light.supported_color_modes
    assert light.supported_color_modes == {ColorMode.RGB}
    assert light.rgb_color == (16, 66, 248)
    assert light.brightness == 123


def test_onoff_light_color_mode():
    light = ComelitLight("DOM#LT#10.1", "Lavanderia", STATE_OFF, None, None, MagicMock())
    assert light.color_mode == ColorMode.ONOFF
    assert light.color_mode.value == "onoff"
    assert light.supported_color_modes == {ColorMode.ONOFF}


def test_dimmable_light_color_mode():
    light = ComelitLight("DOM#LT#34.1", "Cucina", STATE_OFF, 255, None, MagicMock())
    assert light.color_mode == ColorMode.BRIGHTNESS
    assert light.color_mode.value == "brightness"
    assert light.supported_color_modes == {ColorMode.BRIGHTNESS}


# --- hub status parsing for RGB lights ------------------------------------


def test_hub_status_rgb_on():
    hub = make_hub()
    hub.status(load_fixture("hub_status_rgb_on.json"))

    light = hub.lights.get(RGB_ID)
    assert light is not None, "RGB light DOM#LT#48.1 should exist"
    # an ON RGB light reports status "7" (not "1" as on/off lights do)
    assert light._state == STATE_ON
    assert light._rgb == (16, 66, 248)
    assert light._brightness == 123


def test_hub_status_rgb_off():
    hub = make_hub()
    hub.status(load_fixture("hub_status_rgb_off.json"))

    light = hub.lights.get(RGB_ID)
    assert light is not None, "RGB light DOM#LT#48.1 should exist"
    assert light._state == STATE_OFF
    # the hub retains the last color/brightness while the light is off
    assert light._rgb == (16, 66, 248)
    assert light._brightness == 123


def test_hub_poll_keeps_rgb_light_in_sync():
    """The entity state must follow the hub, poll after poll."""
    hub = make_hub()

    hub.status(load_fixture("hub_status_rgb_off.json"))
    light = hub.lights.get(RGB_ID)
    assert light is not None
    assert light._state == STATE_OFF

    # the light gets turned on (from HA or a wall switch)
    hub.status(load_fixture("hub_status_rgb_on.json"))
    assert light._state == STATE_ON
    assert light._rgb == (16, 66, 248)
    assert light._brightness == 123

    # and back off again
    hub.status(load_fixture("hub_status_rgb_off.json"))
    assert light._state == STATE_OFF
