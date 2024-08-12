from unittest import mock
from unittest.mock import MagicMock

from homeassistant.const import STATE_CLOSED

from custom_components.comelit.cover import ComelitCover


class TestComelitCover:
    def setup_method(self, method):
        self.mock_hub = mock.Mock()
        self.device = ComelitCover('id', 'description', 'closed', 'position', self.mock_hub)
        self.device.schedule_update_ha_state = MagicMock()

    def teardown_method(self, method):
        self.device = None

    def test_is_closed(self):
        assert self.device.is_closed == (self.device._state == STATE_CLOSED)

    def test_close_cover(self):
        self.device.close_cover()
        assert self.device.is_closing

    def test_open_cover(self):
        self.device.open_cover()
        assert self.device.is_opening
