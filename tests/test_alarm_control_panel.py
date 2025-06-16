import pytest
from unittest import mock

from homeassistant.components.alarm_control_panel import AlarmControlPanelEntityFeature

from custom_components.comelit import DOMAIN
from custom_components.comelit.alarm_control_panel import setup_platform, VedoAlarm


@pytest.fixture
def test_setup_platform(hass, config, caplog):
    add_entities = mock.MagicMock()
    setup_platform(hass, config, add_entities, None)
    assert hass.data[DOMAIN]['vedo'].alarm_add_entities is add_entities
    assert "Comelit Vedo Alarm Integration started" in caplog.text


class TestVedoAlarm:
    @pytest.fixture
    def vedo_alarm(self):
        vedo_mock = mock.MagicMock()
        vedo_mock.disarm = mock.MagicMock()
        vedo_mock.arm = mock.MagicMock()
        return VedoAlarm('1', 'Vedo Alarm', 'armed', vedo_mock)

    def test_alarm_disarm(self, vedo_alarm):
        vedo_alarm.alarm_disarm()
        vedo_alarm._vedo.disarm.assert_called_once_with('1')

    def test_alarm_arm_away(self, vedo_alarm):
        vedo_alarm.alarm_arm_away()
        vedo_alarm._vedo.arm.assert_called_once_with('1')

    def test_alarm_arm_night(self, vedo_alarm):
        vedo_alarm.alarm_arm_night()
        vedo_alarm._vedo.arm_night.assert_called_once_with('1')

    def test_alarm_arm_home_errors(self, vedo_alarm):
        with pytest.raises(NotImplementedError):
            vedo_alarm.alarm_arm_home()

    def test_supported_features(self, vedo_alarm):
        assert vedo_alarm.supported_features == AlarmControlPanelEntityFeature.ARM_AWAY | AlarmControlPanelEntityFeature.ARM_NIGHT

    def test_code_arm_required(self, vedo_alarm):
        assert vedo_alarm.code_arm_required is False
