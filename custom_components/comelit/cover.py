"""Platform for light integration."""
import time
import logging

from homeassistant.const import STATE_OPEN, STATE_CLOSED

from .const import DOMAIN
from homeassistant.components.cover import (CoverEntity)
from .comelit_device import ComelitDevice


_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['hub'].cover_add_entities = add_entities
    _LOGGER.info("Comelit Cover Integration started")


class ComelitCover(ComelitDevice, CoverEntity):

    def __init__(self, id, description, closed, closing_time, hub):
        ComelitDevice.__init__(self, id, None, description)
        self._state = closed
        self._hub = hub
        self._opening = False
        self._closing = False
        self._closing_time = closing_time
        self._motion_start_time = None


    @property
    def is_closed(self):
        return self._state == STATE_CLOSED

    def update_cover_state(self, state):
        if self._closing_time > 0:
            _LOGGER.debug(f"update_cover_state {self.name}! old state={self._state} new state={state}")
            old = self._state
            if old == STATE_OPEN and state == STATE_CLOSED: #is closing
                _LOGGER.debug(f"update_cover_state {self.name} setting IS CLOSING")
                self._opening = False
                self._closing = True
            elif old == STATE_CLOSED and state == STATE_OPEN: #is opening
                _LOGGER.debug(f"update_cover_state {self.name} setting IS OPENING")
                self._opening = True
                self._closing = False
            elif self._motion_start_time is not None and (time.time() - self._motion_start_time) > self._closing_time: #Reset the state
                _LOGGER.debug(f"update_cover_state {self.name} RESETTING")
                self._opening = False
                self._closing = False
                self._motion_start_time = None
                self.update_state(state)
            elif self._motion_start_time is None:
                self.update_state(state)

    @property
    def is_opening(self):
        self._opening

    @property
    def is_closing(self):
        self._closing

    def open_cover(self, **kwargs):
        _LOGGER.debug(f"Trying to OPEN cover {self.name}! _state={self._state}")
        self._hub.cover_up(self._id)
        self._motion_start_time = time.time()
        self.update_cover_state(STATE_OPEN)
        _LOGGER.debug(f"Trying to OPEN cover {self.name} - DONE!")

    def close_cover(self, **kwargs):
        _LOGGER.debug(f"Trying to CLOSE cover {self.name}! _state={self._state}")
        self._hub.cover_down(self._id)
        self._motion_start_time = time.time()
        self.update_cover_state(STATE_CLOSED)
        _LOGGER.debug(f"Trying to CLOSE cover {self.name} - DONE!")

    def stop_cover(self, **kwargs):
        _LOGGER.debug(f"Trying to STOP cover {self.name}! is_opening={self.is_opening}, is_closing={self.is_closing}")
        if self.is_opening:
            self.close_cover()
        elif self.is_closing:
            self.open_cover()
