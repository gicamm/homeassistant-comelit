"""Platform for sensor integration."""
import logging
from homeassistant.const import (
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
)

from .const import DOMAIN
from .comelit_device import ComelitDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['hub'].sensor_add_entities = add_entities
    _LOGGER.info("Comelit Sensor Integration started")


class ComelitSensor(ComelitDevice):

    def __init__(self, id, description, state, type, icon, unit_of_measurement, device_class):
        ComelitDevice.__init__(self, id, type, description)
        self._type = type
        self._icon = icon
        self._state = state
        self._unit_of_measurement = unit_of_measurement
        self._device_class = device_class

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self):
        self._icon

    # @property
    # def state(self):
    #     return self._state

    def update(self):
        pass

    @property
    def device_class(self):
        return self._device_class


class PowerSensor(ComelitSensor):
    def __init__(self, id, description, value, prod):
        """Initialize the sensor."""
        self.prod = prod
        if prod:
            type = "power_prod"
            icon = "mdi:solar-power"
        else:
            type = "power_cons"
            icon = "mdi:power-plug"
        ComelitSensor.__init__(self, id, description, value, type, icon, UnitOfPower.WATT, SensorDeviceClass.POWER)


class TemperatureSensor(ComelitSensor):
    """Representation of a Sensor."""

    def __init__(self, id, description, value):
        """Initialize the sensor."""
        ComelitSensor.__init__(self, id, description, value, "temperature", "mdi:home-thermometer",
                               UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE)


class HumiditySensor(ComelitSensor):
    def __init__(self, id, description, value):
        """Initialize the sensor."""
        ComelitSensor.__init__(self, id, description, value, "humidity", "mdi:water-percent", "%",
                               SensorDeviceClass.HUMIDITY)
