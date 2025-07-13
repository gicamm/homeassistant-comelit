"""Platform for light integration."""
import logging

# Import the device class from the component that you want to support
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, LightEntity, ColorMode)
from homeassistant.const import STATE_ON, STATE_OFF

from .const import DOMAIN
from .comelit_device import ComelitDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['hub'].light_add_entities = add_entities
    _LOGGER.info("Comelit Light Integration started")


class ComelitLight(ComelitDevice, LightEntity):

    def __init__(self, id, description, state, brightness, light_hub):
        ComelitDevice.__init__(self, id, None, description)
        self._light = light_hub
        self._state = state
        self._brightness = brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state == STATE_ON

    @property
    def supported_color_modes(self):
        return {ColorMode.BRIGHTNESS} if self._brightness is not None else {ColorMode.ONOFF}

    @property
    def color_mode(self):
        return ColorMode.BRIGHTNESS if self._brightness is not None else ColorMode.ONOFF
    
    @property
    def brightness(self):
        return self._brightness

    def update(self):
        pass

    def turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
        self._light.light_on(self._id, self._brightness)
        self._state = STATE_ON # Immediately update the state, don't wait for the next update
        self.schedule_update_ha_state()
        
    def turn_off(self, **kwargs):
        self._light.light_off(self._id)
        self._state = STATE_OFF # Immediately update the state, don't wait for the next update
        self.schedule_update_ha_state()
