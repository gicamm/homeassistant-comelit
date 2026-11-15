"""Regression tests for Hub shutdown and interruptible status polling."""

import asyncio
from threading import Event, get_ident
from unittest.mock import Mock, patch

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
)
import pytest

from custom_components.comelit import setup
from custom_components.comelit.const import CONF_SERIAL, DOMAIN
from custom_components.comelit.hub import (
    ComelitHub,
    StatusUpdater,
    connect_callback,
    disconnect_callback,
    on_message_callback,
)


@pytest.fixture
def shutdown_hub():
    """Use the real Hub and worker with a client that never opens a socket."""
    with patch("custom_components.comelit.hub.mqtt.Client"):
        hub = ComelitHub(
            client_name="test",
            hub_serial="00000000",
            hub_host="127.0.0.1",
            hub_user="user",
            hub_password="pwd",
            mqtt_port=1883,
            mqtt_user="user",
            mqtt_password="pwd",
            scan_interval=3600,
        )
    stop = hub.stop
    try:
        yield hub
    finally:
        stop()


def observe_wait(updater):
    """Synchronize with the worker's wait without arbitrary sleeps."""
    entered = Event()
    original_wait = updater._stop_event.wait

    def wait(timeout):
        entered.set()
        return original_wait(timeout)

    return entered, patch.object(updater._stop_event, "wait", side_effect=wait)


def test_missing_token_waits_and_can_be_stopped():
    """A missing login token must not cause a busy loop or a status request."""
    hub = Mock(sessiontoken="")
    updater = StatusUpdater("test", 3600, hub)
    entered, observed_wait = observe_wait(updater)
    with observed_wait:
        updater.start()
        try:
            assert entered.wait(2)
            hub.publish.assert_not_called()
        finally:
            updater.stop()
            updater.join(timeout=2)
    assert not updater.is_alive()


def test_stop_interrupts_long_polling_interval_and_is_idempotent(shutdown_hub):
    hub = shutdown_hub
    hub.sessiontoken = "token"
    entered, observed_wait = observe_wait(hub.status_thread)
    with observed_wait:
        hub.start()
        try:
            assert entered.wait(2)
            hub.client.publish.assert_called_once()
        finally:
            hub.stop()
    hub.stop()
    assert not hub.status_thread.is_alive()
    assert hub.client.method_calls[-2:] == [
        ("disconnect", (), {}),
        ("loop_stop", (), {}),
    ]
    hub.client.disconnect.assert_called_once()
    hub.client.loop_stop.assert_called_once()


def test_stop_before_worker_starts(shutdown_hub):
    hub = shutdown_hub
    hub.stop()
    hub.status_thread.start()
    hub.status_thread.join(timeout=2)
    assert not hub.status_thread.is_alive()
    hub.client.publish.assert_not_called()


@pytest.mark.parametrize("failing_method", ["disconnect", "loop_stop"])
def test_mqtt_error_still_stops_the_worker(shutdown_hub, failing_method):
    hub = shutdown_hub
    getattr(hub.client, failing_method).side_effect = OSError("MQTT socket closed")
    hub.start()
    with pytest.raises(OSError, match="MQTT socket closed"):
        hub.stop()
    assert not hub.status_thread.is_alive()
    hub.client.disconnect.assert_called_once()
    hub.client.loop_stop.assert_called_once()


def test_callbacks_and_dispatch_ignore_work_after_stop(shutdown_hub):
    hub = shutdown_hub
    hub.stop()
    hub.client.reset_mock()
    # The payload is invalid deliberately: stopping must prevent even decoding it.
    on_message_callback(hub.client, None, Mock(payload=b"not-json"))
    connect_callback(hub.client, None, None, 0)
    hub.dispatch({"req_type": 5, "sessiontoken": "late-token"})
    hub.publish({"req_type": 0})
    assert hub.sessiontoken == ""
    hub.client.subscribe.assert_not_called()
    hub.client.publish.assert_not_called()


def test_queued_climate_selector_is_ignored_after_stop(shutdown_hub):
    hub = shutdown_hub
    hub.select_add_entities = Mock()
    hub.stop()
    hub.update_climate_select("DOM#CL#1", "Living", 1)
    assert hub.climate_selects == {}
    hub.select_add_entities.assert_not_called()


def test_expected_disconnect_does_not_warn(shutdown_hub, caplog):
    hub = shutdown_hub
    disconnect_callback(hub.client, None, 1)
    assert "disconnected from hub" in caplog.text
    caplog.clear()
    hub.stop()
    disconnect_callback(hub.client, None, 0)
    assert not [record for record in caplog.records if record.levelname == "WARNING"]


async def test_shutdown_hook_awaits_cleanup_without_blocking_hass(hass, shutdown_hub):
    """Exercise setup and the real HA event bus, not an extracted listener."""
    hub = shutdown_hub
    loop = asyncio.get_running_loop()
    loop_thread = get_ident()
    responsive = Event()
    stopped = Event()
    calls = []
    original_stop = hub.stop

    def stop():
        calls.append(get_ident())
        assert get_ident() != loop_thread
        loop.call_soon_threadsafe(responsive.set)
        assert responsive.wait(2), "HA loop was blocked while stopping MQTT"
        original_stop()
        stopped.set()

    # The HA pytest fixture executes Mock executor jobs inline. Keep this a real
    # function so this regression test exercises the real thread executor.
    hub.stop = stop
    config = {
        DOMAIN: {
            "hub": {
                CONF_HOST: "127.0.0.1",
                CONF_USERNAME: "user",
                CONF_PASSWORD: "pwd",
                CONF_SERIAL: "00000000",
            }
        }
    }
    with (
        patch("custom_components.comelit.ComelitHub", return_value=hub),
        patch("custom_components.comelit.load_platform"),
    ):
        assert await hass.async_add_executor_job(setup, hass, config)
    assert hub.status_thread.is_alive()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    assert stopped.is_set(), "The stop listener returned before cleanup finished"
    assert not hub.status_thread.is_alive()
    assert len(calls) == 1
