"""Platform for sensor integration."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON

from .const import DOMAIN
from .comelit_device import ComelitDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['hub'].switch_add_entities = add_entities
    _LOGGER.info("Comelit Switch Integration started")


class ComelitSwitch(ComelitDevice, SwitchEntity):

    def __init__(self, id, description, icon, switch_hub):
        self._switch = switch_hub
        self._icon = icon
        ComelitDevice.__init__(self, id, None, description)

    @property
    def is_on(self):
        return self._state == STATE_ON

    @property
    def icon(self):
        return self._icon

    def turn_on(self, **kwargs):
        self._switch.switch_on(self._id)

    def turn_off(self, **kwargs):
        self._switch.switch_off(self._id)


class ComelitOther(ComelitSwitch):

    def __init__(self, id, description, switch_hub):
        ComelitSwitch.__init__(self, id, description, None, switch_hub)
