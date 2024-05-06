"""Platform for sensor integration."""
import logging
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity, AlarmControlPanelEntityFeature
)

from .const import DOMAIN
from .comelit_device import ComelitDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['vedo'].alarm_add_entities = add_entities
    _LOGGER.info("Comelit Vedo Alarm Integration started")


class VedoAlarm(ComelitDevice, AlarmControlPanelEntity):

    def __init__(self, id, description, state, vedo):
        ComelitDevice.__init__(self, id, "vedo", description)
        self._vedo = vedo
        self._state = state

    def alarm_disarm(self, code=None):
        self._vedo.disarm(self._id)

    def alarm_arm_home(self, code=None):
        raise NotImplementedError()
        # self._vedo.arm(self._id)

    def alarm_arm_away(self, code=None):
        self._vedo.arm(self._id)

    def alarm_arm_night(self, code=None):
        self._vedo.disarm(self._id)

    # @property
    # def state(self):
    #     return self._state

    @property
    def code_arm_required(self):
        return False

    @property
    def supported_features(self):
        return AlarmControlPanelEntityFeature.ARM_AWAY | AlarmControlPanelEntityFeature.ARM_NIGHT
