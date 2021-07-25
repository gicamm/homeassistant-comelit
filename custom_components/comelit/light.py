"""Platform for light integration."""
import logging

# Import the device class from the component that you want to support
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, PLATFORM_SCHEMA, LightEntity)
from homeassistant.const import STATE_ON

from .const import DOMAIN
from .comelit_device import ComelitDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['hub'].light_add_entities = add_entities
    _LOGGER.info("Comelit Light Integration started")


class ComelitLight(ComelitDevice, LightEntity):

    def __init__(self, id, description, state, light_hub):
        ComelitDevice.__init__(self, id, None, description)
        self._light = light_hub
        self._state = state

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state == STATE_ON

    def update(self):
        pass
        # self._state = self._light.state(self._id)

    def turn_on(self, **kwargs):
        self._light.light_on(self._id)

    def turn_off(self, **kwargs):
        self._light.light_off(self._id)
