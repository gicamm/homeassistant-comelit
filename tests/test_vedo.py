from unittest.mock import MagicMock, Mock, patch

from homeassistant.components.alarm_control_panel import AlarmControlPanelState
from homeassistant.const import STATE_OFF, STATE_ON
import pytest

from custom_components.comelit import ComelitVedo
from custom_components.comelit.exception import CookieException
from custom_components.comelit.vedo import SensorUpdater, VedoRequest

VEDO = "custom_components.comelit.vedo"


@pytest.fixture
def vedo():
    vedo_instance = ComelitVedo(
        host="127.0.0.1",
        port=80,
        password="pwd",
        scan_interval=30,
        expose_bin_sensors=True,
    )
    vedo_instance.binary_sensor_add_entities = Mock()
    vedo_instance.alarm_add_entities = Mock()
    return vedo_instance


def make_response(status_code=200, content=b"", headers=None, text=""):
    response = Mock()
    response.status_code = status_code
    response.content = content
    response.headers = headers or {}
    response.text = text
    return response


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


def test_start_starts_the_updater(vedo):
    vedo.vedo_updater = Mock()
    vedo.start()
    vedo.vedo_updater.start.assert_called_once()


def test_build_http_without_query(vedo):
    url, headers = vedo.build_http(None, "cookie", VedoRequest.ZONE_STAT)
    assert url.startswith("http://127.0.0.1:80/user/zone_stat.json?_=")
    assert headers["Cookie"] == "cookie"
    assert headers["X-Requested-With"] == "XMLHttpRequest"


def test_build_http_with_query(vedo):
    url, headers = vedo.build_http({"A": "b"}, None, "action.cgi?vedo=1")
    assert url.startswith("http://127.0.0.1:80/action.cgi?vedo=1&_=")
    assert headers["A"] == "b"
    assert "Cookie" not in headers


def test_get_returns_json(vedo):
    response = make_response(content=b'{"status": "0,1"}')
    with patch(f"{VEDO}.requests.get", return_value=response) as get:
        assert vedo.get("uid", VedoRequest.ZONE_STAT, True) == {"status": "0,1"}
    get.assert_called_once()
    response.raise_for_status.assert_called_once()


def test_get_returns_raw_text(vedo):
    response = make_response(content=b"ok")
    with patch(f"{VEDO}.requests.get", return_value=response):
        assert vedo.get("uid", VedoRequest.ACTION, False) == b"ok"


def test_post(vedo):
    response = make_response()
    with patch(f"{VEDO}.requests.post", return_value=response) as post:
        assert vedo.post("http://url", {"a": 1}, {}) is response
    post.assert_called_once()


def test_login_returns_cookie(vedo):
    response = make_response(headers={"set-cookie": "uid=1"})
    with patch.object(vedo, "post", return_value=response) as post:
        assert vedo.login() == "uid=1"
    assert post.call_args.args[1] == {"code": "pwd"}


def test_login_without_cookie_raises(vedo):
    response = make_response()
    with (
        patch.object(vedo, "post", return_value=response),
        pytest.raises(Exception, match="Unable to obtain the cookie"),
    ):
        vedo.login()


def test_login_bad_status_returns_none(vedo):
    response = make_response(status_code=204)
    with patch.object(vedo, "post", return_value=response):
        assert vedo.login() is None


def test_logout(vedo):
    with patch.object(vedo, "post") as post:
        vedo.logout(None)
        post.assert_not_called()

        vedo.logout("uid")
        assert post.call_args.args[1] == {"logout": 1}

        post.side_effect = OSError("boom")
        vedo.logout("uid")  # errors are ignored


@pytest.mark.parametrize(
    ("method", "key"),
    [("arm", "tot"), ("arm_night", "p1"), ("disarm", "dis")],
)
def test_arm_disarm_actions(vedo, method, key):
    with (
        patch.object(vedo, "login", return_value="uid"),
        patch.object(vedo, "get") as get,
        patch.object(vedo, "logout") as logout,
        patch(f"{VEDO}.time.sleep"),
    ):
        getattr(vedo, method)(3)

    get.assert_called_once_with("uid", f"action.cgi?vedo=1&{key}=3&force=1", False)
    logout.assert_called_once_with("uid")


def test_arm_disarm_retries_then_gives_up(vedo):
    with (
        patch.object(vedo, "login", side_effect=OSError("down")) as login,
        patch(f"{VEDO}.time.sleep") as sleep,
    ):
        vedo.arm(1)

    assert login.call_count == 5
    assert sleep.call_count == 5


def test_update_sensor(vedo):
    vedo.update_sensor(None)
    assert vedo.sensors == {}

    vedo.update_sensor({"id": 1, "name": "garage", "status": "0001"})
    sensor = vedo.sensors[1]
    assert sensor.is_on
    vedo.binary_sensor_add_entities.assert_called_once()

    sensor.schedule_update_ha_state = Mock()
    vedo.update_sensor({"id": 1, "name": "garage", "status": "0000"})
    assert sensor.state == STATE_OFF
    sensor.schedule_update_ha_state.assert_called_once()

    vedo.update_sensor({"id": 2})  # malformed data is logged, not raised
    assert 2 not in vedo.sensors


@pytest.mark.parametrize(
    ("armed", "expected"),
    [
        (4, AlarmControlPanelState.ARMED_AWAY),
        (1, AlarmControlPanelState.ARMED_NIGHT),
        (0, AlarmControlPanelState.DISARMED),
    ],
)
def test_update_area(vedo, armed, expected):
    vedo.update_area({"id": 0, "name": "home", "armed": armed})
    assert vedo.areas[0].state == expected


def test_update_area_updates_existing(vedo):
    vedo.update_area({"id": 0, "name": "home", "armed": 0})
    area = vedo.areas[0]
    area.schedule_update_ha_state = Mock()

    vedo.update_area({"id": 0, "name": "home", "armed": 4})
    assert area.state == AlarmControlPanelState.ARMED_AWAY
    vedo.alarm_add_entities.assert_called_once()

    vedo.update_area({"id": 1})  # malformed data is logged, not raised
    assert 1 not in vedo.areas


ZONE_DESC = {"description": ["door", "window"], "in_area": [1, 0]}
ZONE_STAT = {"status": "0001,0000"}
AREA_DESC = {"description": ["home"], "p1_pres": [1], "p2_pres": [0]}
AREA_STAT = {
    "ready": [1],
    "armed": [4],
    "alarm": [0],
    "alarm_memory": [0],
    "sabotage": [0],
    "anomaly": [0],
    "in_time": [0],
    "out_time": [0],
}


def run_once(updater, responses, iterations=1):
    """Run the given number of polling iterations of the updater."""
    vedo = updater._vedo
    sleeps = []

    def stop(*args):
        sleeps.append(args)
        if len(sleeps) == iterations:
            updater._active = False

    vedo.get = Mock(side_effect=responses)
    with patch(f"{VEDO}.time.sleep", side_effect=stop):
        updater.run()


def test_updater_polls_sensors_and_areas(vedo):
    updater = SensorUpdater("test", 1, vedo)
    vedo.login = Mock(return_value="uid")

    run_once(updater, [ZONE_DESC, ZONE_STAT, AREA_DESC, AREA_STAT])

    assert list(vedo.sensors) == [0]
    assert vedo.sensors[0].state == STATE_ON
    assert vedo.areas[0].state == AlarmControlPanelState.ARMED_AWAY
    assert updater._uid == "uid"


def test_updater_logs_out_on_expired_cookie(vedo):
    updater = SensorUpdater("test", 1, vedo)
    vedo.login = Mock(return_value="uid")
    vedo.logout = Mock()

    expired = {"description": ["door"], "in_area": ["Not logged"]}
    run_once(updater, [expired, {"status": "0"}, AREA_DESC, AREA_STAT])

    vedo.logout.assert_called_once_with("uid")
    assert updater._uid is None


def test_updater_logs_out_on_inconsistent_data(vedo):
    updater = SensorUpdater("test", 1, vedo)
    vedo.login = Mock(return_value="uid")
    vedo.logout = Mock()

    run_once(updater, [ZONE_DESC, {"status": "0"}, AREA_DESC, AREA_STAT])

    vedo.logout.assert_called_once_with("uid")
    assert vedo.sensors == {}


def test_updater_retries_failed_login(vedo):
    updater = SensorUpdater("test", 1, vedo)
    vedo.login = MagicMock(side_effect=[None, "uid"])

    run_once(updater, [ZONE_DESC, ZONE_STAT, AREA_DESC, AREA_STAT], iterations=2)

    assert vedo.login.call_count == 2
    assert vedo.get.call_count == 4


def test_updater_logout_without_vedo():
    updater = SensorUpdater("test", 1, None)
    updater._uid = "uid"
    updater.logout()
    assert updater._uid is None


def test_cookie_exception_is_an_exception():
    assert issubclass(CookieException, Exception)
