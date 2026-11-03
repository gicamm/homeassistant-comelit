import json
from unittest.mock import Mock, patch

from homeassistant.components.climate import HVACMode
from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_OPENING,
    STATE_UNKNOWN,
)
import pytest

from custom_components.comelit import hub as hub_module
from custom_components.comelit.hub import (
    ComelitHub,
    CommandHub,
    RequestType,
    SceneHub,
    StatusUpdater,
    connect_callback,
    disconnect_callback,
    on_message_callback,
    publish,
    update_status,
)


@pytest.fixture
def comelit_hub():
    with patch.object(hub_module.mqtt, "Client"):
        hub = ComelitHub(
            client_name="test",
            hub_serial="00000000",
            hub_host="127.0.0.1",
            hub_user="user",
            hub_password="pwd",
            mqtt_port=1883,
            mqtt_user="user",
            mqtt_password="pwd",
            scan_interval=30,
        )
    for platform in ("cover", "scene", "switch", "climate", "sensor", "light"):
        setattr(hub, f"{platform}_add_entities", Mock())
    return hub


def last_request(hub):
    return json.loads(hub.client.publish.call_args.args[1])


def test_start(comelit_hub):
    comelit_hub.status_thread = Mock()
    comelit_hub.start()
    comelit_hub.client.loop_start.assert_called_once()
    comelit_hub.status_thread.start.assert_called_once()


def test_publish_adds_session_fields(comelit_hub):
    comelit_hub.sessiontoken = "token"
    comelit_hub.publish({"req_type": RequestType.STATUS})

    request = last_request(comelit_hub)
    assert request["sessiontoken"] == "token"
    assert request["agent_id"] == comelit_hub.agent_id
    assert comelit_hub.client.publish.call_args.args[0] == comelit_hub.topic_rx


def test_publish_errors_are_logged():
    client = Mock()
    client.publish.side_effect = OSError("down")
    publish(client, "topic", 1, 1, "", {})


def test_mqtt_callbacks(comelit_hub):
    client = Mock(hub=Mock())
    message = Mock(payload=b'{"req_type": 5}')
    on_message_callback(client, None, message)
    client.hub.dispatch.assert_called_once_with({"req_type": 5})

    connect_callback(client, None, None, 0)
    client.subscribe.assert_called_once_with(client.hub.topic_tx)
    client.hub.announce.assert_called_once()

    client.subscribe.side_effect = OSError("down")
    connect_callback(client, None, None, 0)  # errors are logged

    disconnect_callback(client, None, 0)


def test_dispatch_login_announce_parameters(comelit_hub):
    comelit_hub.dispatch({"req_type": RequestType.LOGIN, "sessiontoken": "abc"})
    assert comelit_hub.sessiontoken == "abc"

    comelit_hub.dispatch(
        {"req_type": RequestType.ANNOUNCE, "out_data": [{"agent_id": 42}]}
    )
    assert comelit_hub.agent_id == 42
    assert last_request(comelit_hub)["user_name"] == "user"

    comelit_hub._vedo = {}
    comelit_hub._vip = {}
    comelit_hub._music = {}
    params = [
        ("alarmDevicePass", "1234"),
        ("alarmLocalAddress", "10.0.0.2"),
        ("alarmLocalPort", "80"),
        ("vipEnable", "1"),
        ("musicEnable", "0"),
        ("other", "x"),
    ]
    comelit_hub.dispatch(
        {
            "req_type": RequestType.PARAMETERS,
            "params_data": [
                {"param_name": name, "param_value": value} for name, value in params
            ],
        }
    )
    assert comelit_hub._vedo == {"password": "1234", "host": "10.0.0.2", "port": "80"}
    assert comelit_hub._vip == {"enable": True}
    assert comelit_hub._music == {"enable": False}
    assert last_request(comelit_hub)["req_type"] == RequestType.ANNOUNCE


def test_dispatch_ignores_unknown_and_malformed(comelit_hub):
    comelit_hub.dispatch({"req_type": 99})
    comelit_hub.dispatch({})
    comelit_hub.dispatch({"req_type": RequestType.LOGIN})
    comelit_hub.client.publish.assert_not_called()


@pytest.mark.parametrize(
    ("call", "act_type", "act_params"),
    [
        (lambda c: c.light_on("L"), 0, [1]),
        (lambda c: c.light_on("L", brightness=100), 11, [100, -1]),
        (lambda c: c.light_on("L", 100, (1, 2, 3)), 15, [1, 2, 3, 100]),
        (lambda c: c.light_off("L"), 0, [0]),
        (lambda c: c.switch_on("L"), 0, [1]),
        (lambda c: c.switch_off("L"), 0, [0]),
        (lambda c: c.cover_up("L"), 0, [1]),
        (lambda c: c.cover_down("L"), 0, [0]),
        (lambda c: c.cover_position("L", 50), 52, [127]),
        (lambda c: c.climate_set_temperature("L", 21.5), 2, [215]),
        (lambda c: c.climate_set_state("L", HVACMode.HEAT), 4, [1]),
        (lambda c: c.climate_set_state("L", HVACMode.COOL), 4, [0]),
        (lambda c: c.climate_set_state("L", HVACMode.OFF), 0, [0]),
        (lambda c: c.climate_set_auto_man("L", 2), 13, [2]),
        (lambda c: c.on(RequestType.ANNOUNCE, "L", brightness=1), 11, [1, -1]),
    ],
)
def test_command_hub(call, act_type, act_params):
    hub = Mock()
    call(CommandHub(hub))
    request = hub.publish.call_args.args[0]
    assert request["obj_id"] == "L"
    assert request["act_type"] == act_type
    assert request["act_params"] == act_params


def test_command_hub_errors_are_logged():
    hub = Mock()
    hub.publish.side_effect = OSError("down")
    commands = CommandHub(hub)
    commands.light_on("L")
    commands.light_off("L")
    commands.cover_position("L", 10)
    commands.climate_set_temperature("L", 20)
    commands.climate_set_state("L", HVACMode.HEAT)
    SceneHub(hub).activate("S")
    assert hub.publish.call_count == 6


def test_climate_set_auto_man_rejects_unknown_mode():
    commands = CommandHub(Mock())
    with pytest.raises(ValueError, match="Unsupported"):
        commands.climate_set_auto_man("L", 3)


def test_scene_hub():
    hub = Mock()
    SceneHub(hub).activate("S")
    assert hub.publish.call_args.args[0]["act_type"] == 1000


@pytest.mark.parametrize(
    ("status", "open_status", "expected"),
    [
        ("0", "1", STATE_OPEN),
        ("0", "0", STATE_CLOSED),
        ("1", "0", STATE_OPENING),
        ("2", "0", STATE_CLOSING),
    ],
)
def test_update_cover(comelit_hub, status, open_status, expected):
    data = {"status": status, "open_status": open_status, "position": "255"}
    comelit_hub.update_cover("DOM#BL#1", "Kitchen", data, "open_status")

    cover = comelit_hub.covers["DOM#BL#1"]
    assert cover._state == expected
    assert cover._position == 100


def test_update_cover_existing_and_legacy(comelit_hub):
    comelit_hub.update_cover("DOM#AU#1", "Gate", {"status": "0"}, "status")
    cover = comelit_hub.covers["DOM#AU#1"]
    assert cover._state == STATE_UNKNOWN
    assert cover.current_cover_position is None

    cover.schedule_update_ha_state = Mock()
    data = {"status": "1", "position": "0"}
    comelit_hub.update_cover("DOM#AU#1", "Gate", data, "status")
    assert cover._state == STATE_OPENING
    comelit_hub.cover_add_entities.assert_called_once()

    comelit_hub.update_cover("DOM#AU#2", "Gate", None, "status")  # logged
    assert "DOM#AU#2" not in comelit_hub.covers


def test_update_switch(comelit_hub):
    comelit_hub.update_switch("DOM#LD#1", "Pump", {"status": "1"})
    switch = comelit_hub.switches["DOM#LD#1"]
    switch.schedule_update_ha_state = Mock()

    comelit_hub.update_switch("DOM#LD#1", "Pump", {"status": "1"})
    assert switch.state == STATE_ON
    comelit_hub.update_switch("DOM#LD#1", "Pump", {"status": "0"})
    assert switch.state == STATE_OFF
    comelit_hub.switch_add_entities.assert_called_once()

    comelit_hub.update_switch("DOM#LD#2", "Pump", {})  # logged
    assert "DOM#LD#2" not in comelit_hub.switches


def test_update_scenario(comelit_hub):
    comelit_hub.update_scenario("GEN#SC#1", "Night", {})
    comelit_hub.update_scenario("GEN#SC#1", "Night", {})
    assert "GEN#SC#1" in comelit_hub.scenes
    comelit_hub.scene_add_entities.assert_called_once()


def test_update_entities_routes_switches_and_automations(comelit_hub):
    elements = [
        {"id": "DOM#LD#1", "data": {"descrizione": "Pump", "status": "0"}},
        {"id": "DOM#AU#1", "data": {"descrizione": "Gate", "status": "0"}},
        {"id": "GEN#SC#1", "data": {"descrizione": "Night"}},
        {"id": "UNKNOWN#1", "data": {}},
    ]
    comelit_hub.update_entities(elements)

    assert "DOM#LD#1" in comelit_hub.switches
    assert "DOM#AU#1" in comelit_hub.covers
    assert "GEN#SC#1" in comelit_hub.scenes


def test_update_entities_and_status_errors_are_logged(comelit_hub):
    comelit_hub.update_entities([{}])
    comelit_hub.status({})


def test_update_climate_schedules_selector_on_event_loop(comelit_hub):
    comelit_hub.hass = Mock()
    comelit_hub.hass.loop.call_soon_threadsafe = lambda cb, *args: cb(*args)
    comelit_hub.select_add_entities = Mock()
    data = {
        "temperatura": "205",
        "soglia_attiva": "210",
        "auto_man": "1",
        "est_inv": "1",
        "status": "0",
    }

    comelit_hub.update_climate("DOM#CL#1", "Living", data)
    selector = comelit_hub.climate_selects["DOM#CL#1"]
    comelit_hub.select_add_entities.assert_called_once_with([selector])

    selector.schedule_update_ha_state = Mock()
    comelit_hub.climates["comelit_climate_living"].schedule_update_ha_state = Mock()
    comelit_hub.update_climate("DOM#CL#1", "Living", {**data, "auto_man": "2"})
    assert selector.current_option == "MANUALE"


def test_update_climate_rejects_non_climate_ids(comelit_hub):
    comelit_hub.update_climate("DOM#LT#1", "Lamp", {})
    assert comelit_hub.climates == {}


def test_update_light_errors_are_logged(comelit_hub):
    comelit_hub.update_light("DOM#LT#1", "Lamp", {})
    assert comelit_hub.lights == {}


def test_update_sensor_errors_are_logged(comelit_hub):
    comelit_hub.update_sensor("DOM#CL#1", "Living", {})
    assert comelit_hub.sensors == {}


def test_update_status():
    hub = Mock()
    update_status(hub)
    assert hub.publish.call_args.args[0]["req_type"] == RequestType.STATUS

    hub.publish.side_effect = OSError("down")
    update_status(hub)  # errors are logged


def test_status_updater_polls_once_logged_in():
    hub = Mock(sessiontoken="token")
    updater = StatusUpdater("test", 30, hub)

    class Stop(Exception):
        pass

    with (
        patch.object(hub_module.time, "sleep", side_effect=Stop),
        pytest.raises(Stop),
    ):
        updater.run()

    hub.publish.assert_called_once()
