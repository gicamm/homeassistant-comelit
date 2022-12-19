import logging


from homeassistant.components.climate import ClimateEntity

from homeassistant.components.climate import HVACMode, HVACAction

from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
)

from .const import DOMAIN

from .comelit_device import ComelitDevice

_LOGGER = logging.getLogger(__name__)



def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['hub'].climate_add_entities = add_entities
    _LOGGER.info("Comelit Climate Integration started")

class ComelitClimate(ComelitDevice, ClimateEntity):
    def __init__(self, id, description, state, measured_temperature, target_temperature, measured_humidity, hub):
        ComelitDevice.__init__(self, id, "climate", description)
        self._hub = hub
        self._state = state
        self._temperature = measured_temperature
        self._target_temperature = target_temperature
        self._humidity = measured_humidity

    @property
    def hvac_mode(self):
        return HVACMode.HEAT if self._state else HVACMode.OFF

    @property
    def hvac_modes(self):
        return [HVACMode.HEAT, HVACMode.OFF]

    @property
    def hvac_action(self):
        if self._state:
            return HVACAction.HEATING
        else:
            return HVACAction.IDLE if self._target_temperature else HVACAction.OFF

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        return self._temperature

    @property
    def current_humidity(self):
        return self._humidity

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE

    def set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._hub.climate_set_temperature(self._id, temperature)

    def set_hvac_mode(self, hvac_mode):
        self._hub.climate_set_state(self._id, hvac_mode == HVACMode.HEAT)

    def update_state(self, state, temperature, target_temperature, humidity):
        self._state = state
        self._target_temperature = target_temperature
        self._temperature = temperature
        self._humidity = humidity
        self.async_write_ha_state()

    def update(self):
        pass