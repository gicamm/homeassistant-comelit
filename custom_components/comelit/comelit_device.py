from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class ComelitDevice(Entity):
    def __init__(self, id, device_type, name):
        """Initialize the Comelit device."""
        self._is_available = True
        self._device_type = device_type
        self._id = id
        self._state = None
        if device_type is None:
            self._name = self.entity_name = "{0}_{1}".format(DOMAIN, name.lower().replace(' ', '-'))
            self._unique_id = "{0}_{1}".format(DOMAIN, id)
        else:
            self._name = self.entity_name = "{0}_{1}_{2}".format(DOMAIN, device_type, name.lower().replace(' ', '-'))
            self._unique_id = "{0}_{1}_{2}".format(DOMAIN, device_type, id)


    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def available(self):
        """Return True if entity is available."""
        return self._is_available

    def update_state(self, state):
        old = self._state
        self._state = state
        if old != state:
            self.async_schedule_update_ha_state()

    @property
    def state(self):
        return self._state

    @property
    def should_poll(self):
        return False
