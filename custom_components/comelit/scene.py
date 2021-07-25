"""Platform for sensor integration."""
import logging

from homeassistant.components.scene import Scene

from .const import DOMAIN
from .comelit_device import ComelitDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['hub'].scene_add_entities = add_entities
    _LOGGER.info("Comelit Scenario Integration started")


class ComelitScenario(ComelitDevice, Scene):

    def __init__(self, id, description, scenario_hub):
        self._scenario = scenario_hub
        ComelitDevice.__init__(self, id, None, description)

    def activate(self):
        self._scenario.activate(self._id)


