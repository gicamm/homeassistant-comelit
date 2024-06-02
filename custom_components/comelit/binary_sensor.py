"""Platform for sensor integration."""
import logging
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.const import STATE_ON

from .comelit_device import ComelitDevice
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    if 'vedo' in hass.data[DOMAIN] and hass.data[DOMAIN]['vedo'] is not None:
        hass.data[DOMAIN]['vedo'].binary_sensor_add_entities = add_entities
        _LOGGER.info("Comelit Vedo Binary Sensor Integration started")


class VedoSensor(ComelitDevice, BinarySensorEntity):

    def __init__(self, id, description, state):
        ComelitDevice.__init__(self, id, "vedo", description)
        self._state = state

    @property
    def is_on(self):
        return self._state == STATE_ON

    @property
    def device_class(self):
        return BinarySensorDeviceClass.MOTION
