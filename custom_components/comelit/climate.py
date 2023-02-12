import logging


from homeassistant.components.climate import ClimateEntity

from homeassistant.components.climate import HVACMode, HVACAction

from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
    STATE_OFF,
    STATE_IDLE,
    STATE_ON
)

from .const import DOMAIN

from .comelit_device import ComelitDevice

_LOGGER = logging.getLogger(__name__)



def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['hub'].climate_add_entities = add_entities
    _LOGGER.info("Comelit Climate Integration started")

class ComelitClimate(ComelitDevice, ClimateEntity):
    def __init__(self, id, description, state_dict, hub):
        ComelitDevice.__init__(self, id, "climate", description)
        self._hub = hub
        self._state = state_dict

    @property
    def hvac_mode(self):
        return HVACMode.HEAT if self._state['is_heating'] else HVACMode.OFF

    @property
    def hvac_modes(self):
        return [HVACMode.HEAT, HVACMode.OFF]

    @property
    def hvac_action(self):
        if self._state['is_heating']:
            return HVACAction.HEATING
        else:
            return HVACAction.IDLE if self._state['is_enabled'] else HVACAction.OFF

    @property
    def target_temperature(self):
        return self._state['target_temperature']

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        return self._state['measured_temperature']

    @property
    def current_humidity(self):
        return self._state['measured_humidity']

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE

    def set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._hub.climate_set_temperature(self._id, temperature)
            self._state['target_temperature'] = temperature
            self.async_schedule_update_ha_state()

    def set_hvac_mode(self, hvac_mode):
        self._hub.climate_set_state(self._id, hvac_mode == HVACMode.HEAT)
        self.async_schedule_update_ha_state()
        
    def update(self):
        pass

    @property
    def state(self):
        state_mapping = {HVACAction.HEATING: STATE_ON, HVACAction.IDLE: STATE_IDLE, HVACAction.OFF: STATE_OFF}
        return state_mapping[self.hvac_action]
