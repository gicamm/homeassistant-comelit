"""Platform for light integration."""
import logging

from homeassistant.const import STATE_CLOSED, STATE_OPENING, STATE_CLOSING

from .const import DOMAIN
from homeassistant.components.cover import (CoverEntity)
from .comelit_device import ComelitDevice


_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['hub'].cover_add_entities = add_entities
    _LOGGER.info("Comelit Cover Integration started")


class ComelitCover(ComelitDevice, CoverEntity):

    def __init__(self, id, description, closed, position, hub):
        ComelitDevice.__init__(self, id, None, description)
        self._state = closed
        self._hub = hub
        if position != -1:
            self._position = position
        else:
            self._position = None

    @property
    def is_closed(self):
        return self._state == STATE_CLOSED

    @property
    def is_opening(self):
        return self._state == STATE_OPENING

    @property
    def is_closing(self):
        return self._state == STATE_CLOSING

    @property
    def current_cover_position(self):  # -> int | None:
        if self._position is None:
            return None
        else:
            return 100 - self._position
            
    def set_cover_position(self, position, **kwargs):
        _LOGGER.debug(f"Trying to SET POSITION {position} cover {self.name}! _state={self._state}")
        self._hub.cover_position(self._id, 100 - position)

    def open_cover(self, stopping=False, **kwargs):
        _LOGGER.debug(f"Trying to OPEN cover {self.name}! _state={self._state}")
        self._hub.cover_up(self._id)
        if not stopping:
            self._state = STATE_OPENING
        self.schedule_update_ha_state()

    def close_cover(self, stopping=False, **kwargs):
        _LOGGER.debug(f"Trying to CLOSE cover {self.name}! _state={self._state}")
        self._hub.cover_down(self._id)
        if not stopping:
            self._state = STATE_CLOSING
        self.schedule_update_ha_state()
    
    def update_state(self, state, position):
        super().update_state(state)

        if position != -1:
            old = self._position
            self._position = position
            if old != position:
                self.schedule_update_ha_state()

    def stop_cover(self, **kwargs):
        _LOGGER.debug(f"Trying to STOP cover {self.name}! is_opening={self.is_opening}, is_closing={self.is_closing}")
        if self.is_opening:
            self.close_cover(stopping=True)
        elif self.is_closing:
            self.open_cover(stopping=True)
