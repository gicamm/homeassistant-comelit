from typing import ClassVar
from unittest import mock

from homeassistant.components.alarm_control_panel import AlarmControlPanelState
import pytest

from custom_components.comelit import ComelitVedo
from custom_components.comelit.vedo import SensorUpdater, VedoRequest


@pytest.fixture
def vedo_instance():
    return ComelitVedo(
        host="127.0.0.1",
        port=80,
        password="pwd",
        scan_interval=30,
        expose_bin_sensors=True,
    )


@pytest.mark.asyncio
async def test_vedo_sensor(hass):
    vedo_instance = ComelitVedo(
        host="127.0.0.1",
        port=80,
        password="pwd",
        scan_interval=30,
        expose_bin_sensors=True,
    )
    vedo_instance.binary_sensor_add_entities = lambda *args, **kwargs: None

    sensor_dict = {"index": 1, "id": 1, "name": "garage", "status": "0011"}
    vedo_instance.update_sensor(sensor_dict)

    assert len(vedo_instance.sensors) == 1


class TestBuildHttp:
    def test_cgi_path_has_no_cache_buster(self, vedo_instance):
        url, _ = vedo_instance.build_http({}, None, VedoRequest.LOGIN)
        assert url == "http://127.0.0.1:80/login.cgi"

    def test_json_path_gets_cache_buster(self, vedo_instance):
        url, _ = vedo_instance.build_http({}, None, VedoRequest.ZONE_STAT)
        assert url.startswith("http://127.0.0.1:80/user/zone_stat.json?_=")

    def test_json_path_with_query_appends_cache_buster(self, vedo_instance):
        url, _ = vedo_instance.build_http({}, None, "user/foo.json?bar=1")
        assert url.startswith("http://127.0.0.1:80/user/foo.json?bar=1&_=")


class TestArmDisarm:
    def test_arm_disarm_posts_expected_params(self, vedo_instance):
        vedo_instance.login = mock.MagicMock(return_value="cookie")
        vedo_instance.logout = mock.MagicMock()
        vedo_instance.post = mock.MagicMock()

        vedo_instance.arm_disarm("tot", 2)

        url, params, headers = vedo_instance.post.call_args[0]
        assert url == "http://127.0.0.1:80/action.cgi"
        assert params == {
            "forced": 1,
            "vedo_param": 1,
            "type_param": "tot",
            "area_param": 2,
        }
        assert headers["Cookie"] == "cookie"
        vedo_instance.logout.assert_called_once_with("cookie")


class TestUpdateArea:
    BASE_AREA: ClassVar = {
        "id": 1,
        "name": "Ingresso",
        "armed": 0,
        "alarm": 0,
        "sabotage": 0,
        "anomaly": 0,
        "out_time": 0,
    }

    def _update(self, vedo_instance, **overrides):
        area = {**self.BASE_AREA, **overrides}
        vedo_instance.update_area(area)
        return vedo_instance.areas[area["id"]].update_state.call_args[0][0]

    def _vedo_with_area(self, vedo_instance):
        vedo_instance.alarm_add_entities = lambda entities: None
        vedo_instance.update_area({**self.BASE_AREA})
        vedo_instance.areas[1] = mock.MagicMock()
        return vedo_instance

    def test_disarmed(self, vedo_instance):
        vedo = self._vedo_with_area(vedo_instance)
        assert self._update(vedo, armed=0) == AlarmControlPanelState.DISARMED

    def test_armed_away(self, vedo_instance):
        vedo = self._vedo_with_area(vedo_instance)
        assert self._update(vedo, armed=4) == AlarmControlPanelState.ARMED_AWAY

    def test_armed_night(self, vedo_instance):
        vedo = self._vedo_with_area(vedo_instance)
        assert self._update(vedo, armed=1) == AlarmControlPanelState.ARMED_NIGHT

    def test_arming(self, vedo_instance):
        vedo = self._vedo_with_area(vedo_instance)
        assert self._update(vedo, armed=4, out_time=1) == AlarmControlPanelState.ARMING

    def test_triggered(self, vedo_instance):
        vedo = self._vedo_with_area(vedo_instance)
        assert self._update(vedo, armed=4, alarm=1) == AlarmControlPanelState.TRIGGERED

    def test_unknown_armed_value_does_not_raise(self, vedo_instance, caplog):
        # "armed" values other than 1/4 (e.g. a partial P2 arm) used to hit no
        # branch and raise UnboundLocalError on the undefined `state`.
        vedo = self._vedo_with_area(vedo_instance)
        assert self._update(vedo, armed=2) == AlarmControlPanelState.ARMED_CUSTOM_BYPASS
        assert "Error updating the alarm area" not in caplog.text


class TestSensorUpdaterAreaFiltering:
    def test_only_present_areas_are_updated(self, vedo_instance):
        vedo_instance.expose_bin_sensors = False
        vedo_instance.login = mock.MagicMock(return_value="cookie")
        vedo_instance.update_area = mock.MagicMock()

        def fake_get(uid, path, is_response):
            if path == VedoRequest.ZONE_DESC:
                return {"description": ["Zone 1"], "in_area": [0]}
            if path == VedoRequest.ZONE_STAT:
                return {"status": "0000"}
            if path == VedoRequest.AREA_DESC:
                return {
                    "description": ["Area 1", "Area 2"],
                    "present": [1, 0],
                    "p1_pres": [0, 0],
                    "p2_pres": [0, 0],
                }
            if path == VedoRequest.AREA_STAT:
                return {
                    "ready": [1, 1],
                    "armed": [0, 0],
                    "alarm": [0, 0],
                    "alarm_memory": [0, 0],
                    "sabotage": [0, 0],
                    "anomaly": [0, 0],
                    "in_time": [0, 0],
                    "out_time": [0, 0],
                }
            raise AssertionError(f"unexpected path {path}")

        vedo_instance.get = mock.MagicMock(side_effect=fake_get)

        updater = SensorUpdater("Thread#BS", 30, vedo_instance)

        def stop_after_one_iteration(*args, **kwargs):
            updater._active = False

        with mock.patch("custom_components.comelit.vedo.time.sleep") as sleep_mock:
            sleep_mock.side_effect = stop_after_one_iteration
            updater._active = True
            updater.run()

        assert vedo_instance.update_area.call_count == 1
        assert vedo_instance.update_area.call_args[0][0]["name"] == "Area 1"
