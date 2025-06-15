import logging


from homeassistant.components.climate import ClimateEntity

from homeassistant.components.climate import HVACMode, HVACAction

from homeassistant.components.climate import (
    ClimateEntityFeature
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_OFF,
    STATE_IDLE,
    STATE_ON
)
from homeassistant.components.sensor import (
    UnitOfTemperature,
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
        if self._state['status']:
            if self._state['is_winter_season']:
                return HVACMode.HEAT 
            else:
                return HVACMode.COOL 
        else: 
            return HVACMode.OFF

    @property
    def hvac_modes(self):
        return [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]

    @property
    def hvac_action(self):
        if self._state['status']:
            if self._state['is_winter_season']:
                return HVACAction.HEATING
            else:
                return HVACAction.COOLING
        else:
            return HVACAction.IDLE if self._state['is_enabled'] else HVACAction.OFF

    @property
    def target_temperature(self):
        return self._state['target_temperature']

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        return self._state['measured_temperature']

    @property
    def current_humidity(self):
        return self._state.get('measured_humidity', None)

    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE

    def set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._hub.climate_set_temperature(self._id, temperature)
            self._state['target_temperature'] = temperature
            self.schedule_update_ha_state()

    def set_hvac_mode(self, hvac_mode):
        self._hub.climate_set_state(self._id, hvac_mode)
        self.schedule_update_ha_state()
        
    def update(self):
        pass

    @property
    def state(self):
        state_mapping = {HVACAction.HEATING: STATE_ON, HVACAction.COOLING: STATE_ON, HVACAction.IDLE: STATE_IDLE, HVACAction.OFF: STATE_OFF}
        return state_mapping[self.hvac_action]
