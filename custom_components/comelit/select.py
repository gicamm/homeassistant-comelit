"""Select platform for Comelit thermostat AUTO/MANUAL/OFF control."""

from homeassistant.components.climate import HVACMode
from homeassistant.components.select import SelectEntity

from .comelit_device import ComelitDevice
from .const import DOMAIN

OPTIONS = ["AUTO", "MANUALE", "OFF"]
STATE_TO_OPTION = {0: "OFF", 1: "AUTO", 2: "MANUALE", 5: "OFF", 6: "OFF"}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Register selectors and restore previously received states."""
    hub = hass.data[DOMAIN]["hub"]

    def register_platform():
        hub.select_add_entities = add_entities
        if hub.climate_selects:
            add_entities(list(hub.climate_selects.values()))

    hass.loop.call_soon_threadsafe(register_platform)


class ComelitClimateSelect(ComelitDevice, SelectEntity):
    """Choose operating mode independently from heating/cooling season."""

    def __init__(self, id, description, auto_man, hub):
        ComelitDevice.__init__(self, id, "climate_mode", description)
        self._hub = hub
        self._auto_man = auto_man

    @property
    def options(self):
        return OPTIONS

    @property
    def current_option(self):
        return STATE_TO_OPTION.get(self._auto_man)

    def select_option(self, option):
        if option == "AUTO":
            self._hub.climate_set_auto_man(self._id, 1)
        elif option == "MANUALE":
            self._hub.climate_set_auto_man(self._id, 2)
        elif option == "OFF":
            self._hub.climate_set_state(self._id, HVACMode.OFF)
        else:
            raise ValueError(f"Unsupported Comelit climate option: {option}")

    def update_auto_man(self, auto_man):
        if self._auto_man != auto_man:
            self._auto_man = auto_man
            self.schedule_update_ha_state()
