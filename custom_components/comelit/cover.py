"""Platform for light integration."""
import time
import logging

from homeassistant.const import STATE_OPEN, STATE_CLOSED, STATE_OPENING, STATE_CLOSING

from .const import DOMAIN
from homeassistant.components.cover import (CoverEntity)
from .comelit_device import ComelitDevice


_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    hass.data[DOMAIN]['hub'].cover_add_entities = add_entities
    _LOGGER.info("Comelit Cover Integration started")


class ComelitCover(ComelitDevice, CoverEntity):

    def __init__(self, id, description, closed, hub):
        ComelitDevice.__init__(self, id, None, description)
        self._state = closed
        self._hub = hub

    @property
    def is_closed(self):
        return self._state == STATE_CLOSED

    @property
    def is_opening(self):
        return self._state == STATE_OPENING

    @property
    def is_closing(self):
        return self._state == STATE_CLOSING

    def open_cover(self, **kwargs):
        _LOGGER.debug(f"Trying to OPEN cover {self.name}! _state={self._state}")
        self._hub.cover_up(self._id)
        # self._state == STATE_OPENING

    def close_cover(self, **kwargs):
        _LOGGER.debug(f"Trying to CLOSE cover {self.name}! _state={self._state}")
        self._hub.cover_down(self._id)
        # self._state = STATE_CLOSING

    def stop_cover(self, **kwargs):
        _LOGGER.debug(f"Trying to STOP cover {self.name}! is_opening={self.is_opening}, is_closing={self.is_closing}")
        if self.is_opening:
            self.close_cover()
        elif self.is_closing:
            self.open_cover()
