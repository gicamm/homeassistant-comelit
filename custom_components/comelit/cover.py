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
        self._last_update = None

    @property
    def is_closed(self):
        return self._state == STATE_CLOSED

    def update_cover_state(self, state):
        if self._closing_time > 0:# Disable ste opening/closing status
            old = self._state
            if old == STATE_OPEN and state == STATE_CLOSED: #is closing
                self._opening = False
                self._closing = True
                self._last_update = time.time()
            elif old == STATE_CLOSED and state == STATE_OPEN: #is opening
                self._opening = True
                self._closing = False
                self._last_update = time.time()
            elif self._last_update is not None and (time.time() - self._last_update) > self._closing_time:#Reset the state
                self._last_update = None
                self._opening = False
                self._closing = False

        self.update_state(state)

    @property
    def is_opening(self):
        self._opening

    @property
    def is_closing(self):
        self._closing

    def open_cover(self, **kwargs):
        self._hub.cover_up(self._id)

    def close_cover(self, **kwargs):
        self._hub.cover_down(self._id)
