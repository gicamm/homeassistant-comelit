import pytest
from unittest.mock import Mock

from homeassistant.components.light import ColorMode, ATTR_BRIGHTNESS
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.comelit.light import ComelitLight


@pytest.fixture
def comelit_light():
    light_hub = Mock()
    light = ComelitLight("id", "description", STATE_ON, 255, light_hub)
    light.schedule_update_ha_state = lambda *args, **kwargs: None
    return light


def test_light_is_on(comelit_light):
    assert comelit_light.is_on


def test_light_supported_color_modes(comelit_light):
    assert comelit_light.supported_color_modes == {ColorMode.BRIGHTNESS}


def test_light_color_mode(comelit_light):
    assert comelit_light.color_mode == ColorMode.BRIGHTNESS


def test_light_brightness(comelit_light):
    assert comelit_light.brightness == 255


def test_light_turn_on(comelit_light):
    comelit_light.turn_on(**{ATTR_BRIGHTNESS: 128})
    assert comelit_light._state == STATE_ON
    assert comelit_light._brightness == 128


def test_light_turn_off(comelit_light):
    comelit_light.turn_off()
    assert comelit_light._state == STATE_OFF
