from unittest.mock import Mock

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntityFeature,
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import (
    STATE_CLOSING,
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
    STATE_OPENING,
    UnitOfTemperature,
)
import pytest

from custom_components.comelit import (
    alarm_control_panel,
    binary_sensor,
    climate,
    cover,
    light,
    scene,
    select,
    sensor,
    switch,
)
from custom_components.comelit.alarm_control_panel import VedoAlarm
from custom_components.comelit.binary_sensor import VedoSensor
from custom_components.comelit.climate import ComelitClimate
from custom_components.comelit.const import DOMAIN
from custom_components.comelit.cover import ComelitCover
from custom_components.comelit.scene import ComelitScenario
from custom_components.comelit.select import ComelitClimateSelect
from custom_components.comelit.sensor import PowerSensor, TemperatureSensor
from custom_components.comelit.switch import ComelitOther, ComelitSwitch


def fake_hass():
    hass = Mock()
    hass.data = {DOMAIN: {"hub": Mock(climate_selects={}), "vedo": Mock()}}
    hass.loop.call_soon_threadsafe = lambda callback, *args: callback(*args)
    return hass


@pytest.mark.parametrize(
    ("platform", "attribute"),
    [
        (climate, "climate_add_entities"),
        (cover, "cover_add_entities"),
        (light, "light_add_entities"),
        (scene, "scene_add_entities"),
        (sensor, "sensor_add_entities"),
        (switch, "switch_add_entities"),
    ],
)
def test_hub_platform_setup(platform, attribute):
    hass = fake_hass()
    add_entities = Mock()
    platform.setup_platform(hass, {}, add_entities)
    assert getattr(hass.data[DOMAIN]["hub"], attribute) is add_entities


@pytest.mark.parametrize(
    ("platform", "attribute"),
    [
        (alarm_control_panel, "alarm_add_entities"),
        (binary_sensor, "binary_sensor_add_entities"),
    ],
)
def test_vedo_platform_setup(platform, attribute):
    hass = fake_hass()
    add_entities = Mock()
    platform.setup_platform(hass, {}, add_entities)
    assert getattr(hass.data[DOMAIN]["vedo"], attribute) is add_entities


def test_binary_sensor_setup_without_vedo():
    hass = fake_hass()
    hass.data[DOMAIN]["vedo"] = None
    binary_sensor.setup_platform(hass, {}, Mock())


def test_select_setup_restores_known_selectors():
    hass = fake_hass()
    hub = hass.data[DOMAIN]["hub"]
    selector = Mock()
    hub.climate_selects = {"id": selector}
    add_entities = Mock()

    select.setup_platform(hass, {}, add_entities)

    assert hub.select_add_entities is add_entities
    add_entities.assert_called_once_with([selector])


def test_select_setup_without_selectors():
    hass = fake_hass()
    add_entities = Mock()
    select.setup_platform(hass, {}, add_entities)
    add_entities.assert_not_called()


@pytest.fixture
def climate_state():
    return {
        "auto_man": 2,
        "is_enabled": True,
        "is_winter_season": True,
        "status": True,
        "measured_temperature": 20.5,
        "target_temperature": 21.0,
        "measured_humidity": 45.0,
    }


@pytest.fixture
def comelit_climate(climate_state):
    entity = ComelitClimate("DOM#CL#1", "Living", climate_state, Mock())
    entity.schedule_update_ha_state = Mock()
    return entity


def test_climate_properties(comelit_climate):
    assert comelit_climate.extra_state_attributes == {"comelit_auto_man": 2}
    assert comelit_climate.hvac_modes == [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
    assert comelit_climate.native_target_temperature == 21.0
    assert comelit_climate.native_current_temperature == 20.5
    assert comelit_climate.current_humidity == 45.0
    assert comelit_climate.native_temperature_unit == UnitOfTemperature.CELSIUS
    assert comelit_climate.supported_features == ClimateEntityFeature.TARGET_TEMPERATURE


@pytest.mark.parametrize(
    ("status", "winter", "enabled", "mode", "action", "state"),
    [
        (True, True, True, HVACMode.HEAT, HVACAction.HEATING, STATE_ON),
        (True, False, True, HVACMode.COOL, HVACAction.COOLING, STATE_ON),
        (False, True, True, HVACMode.OFF, HVACAction.IDLE, STATE_IDLE),
        (False, True, False, HVACMode.OFF, HVACAction.OFF, STATE_OFF),
    ],
)
def test_climate_modes(
    comelit_climate, climate_state, status, winter, enabled, mode, action, state
):
    climate_state.update(
        {"status": status, "is_winter_season": winter, "is_enabled": enabled}
    )
    assert comelit_climate.hvac_mode == mode
    assert comelit_climate.hvac_action == action
    assert comelit_climate.state == state


def test_climate_set_temperature(comelit_climate):
    comelit_climate.set_temperature(**{ATTR_TEMPERATURE: 22.5})
    comelit_climate._hub.climate_set_temperature.assert_called_once_with(
        "DOM#CL#1", 22.5
    )
    assert comelit_climate.native_target_temperature == 22.5

    comelit_climate.set_temperature()
    comelit_climate._hub.climate_set_temperature.assert_called_once()


def test_climate_set_hvac_mode(comelit_climate):
    comelit_climate.set_hvac_mode(HVACMode.COOL)
    comelit_climate._hub.climate_set_state.assert_called_once_with(
        "DOM#CL#1", HVACMode.COOL
    )
    comelit_climate.schedule_update_ha_state.assert_called_once()


@pytest.fixture
def climate_select():
    entity = ComelitClimateSelect("DOM#CL#1", "Living", 1, Mock())
    entity.schedule_update_ha_state = Mock()
    return entity


def test_select_options(climate_select):
    assert climate_select.options == ["AUTO", "MANUALE", "OFF"]
    assert climate_select.current_option == "AUTO"


def test_select_option(climate_select):
    hub = climate_select._hub
    climate_select.select_option("AUTO")
    hub.climate_set_auto_man.assert_called_with("DOM#CL#1", 1)
    climate_select.select_option("MANUALE")
    hub.climate_set_auto_man.assert_called_with("DOM#CL#1", 2)
    climate_select.select_option("OFF")
    hub.climate_set_state.assert_called_once_with("DOM#CL#1", HVACMode.OFF)
    with pytest.raises(ValueError, match="Unsupported"):
        climate_select.select_option("ECO")


def test_select_update_auto_man(climate_select):
    climate_select.update_auto_man(1)
    climate_select.schedule_update_ha_state.assert_not_called()
    climate_select.update_auto_man(2)
    assert climate_select.current_option == "MANUALE"
    climate_select.schedule_update_ha_state.assert_called_once()


@pytest.fixture
def comelit_cover():
    entity = ComelitCover("DOM#BL#1", "Kitchen", STATE_OPENING, 30, Mock())
    entity.schedule_update_ha_state = Mock()
    return entity


def test_cover_position(comelit_cover):
    assert comelit_cover.current_cover_position == 70
    comelit_cover.set_cover_position(30)
    comelit_cover._hub.cover_position.assert_called_once_with("DOM#BL#1", 70)


def test_cover_without_position():
    entity = ComelitCover("DOM#BL#1", "Kitchen", STATE_OPENING, -1, Mock())
    assert entity.current_cover_position is None


def test_cover_update_state(comelit_cover):
    comelit_cover.update_state(STATE_OPENING, 40)
    assert comelit_cover._position == 40
    comelit_cover.schedule_update_ha_state.assert_called_once()

    comelit_cover.update_state(STATE_OPENING, -1)
    assert comelit_cover._position == 40


def test_cover_stop_while_opening(comelit_cover):
    comelit_cover.stop_cover()
    comelit_cover._hub.cover_down.assert_called_once_with("DOM#BL#1")
    assert comelit_cover.is_opening


def test_cover_stop_while_closing(comelit_cover):
    comelit_cover._state = STATE_CLOSING
    comelit_cover.stop_cover()
    comelit_cover._hub.cover_up.assert_called_once_with("DOM#BL#1")
    assert comelit_cover.is_closing


def test_switch():
    hub = Mock()
    entity = ComelitSwitch("DOM#LD#1", "Pump", "mdi:pump", hub)
    assert entity.icon == "mdi:pump"
    assert not entity.is_on
    entity.turn_on()
    hub.switch_on.assert_called_once_with("DOM#LD#1")
    entity.turn_off()
    hub.switch_off.assert_called_once_with("DOM#LD#1")
    assert ComelitOther("DOM#LD#2", "Other", hub).icon is None


def test_scene_activate():
    hub = Mock()
    ComelitScenario("GEN#SC#1", "Night", hub).activate()
    hub.activate.assert_called_once_with("GEN#SC#1")


def test_sensors():
    temperature = TemperatureSensor("DOM#CL#1", "Living", 20.5)
    assert temperature.icon is not None
    assert temperature.device_class is not None
    assert temperature.state_class is not None

    power = PowerSensor("DOM#CN#1", "Meter", "100.00", True)
    assert power.unit_of_measurement is not None


def test_vedo_entities():
    vedo = Mock()
    alarm = VedoAlarm(0, "Home", STATE_OFF, vedo)
    alarm.alarm_disarm()
    vedo.disarm.assert_called_once_with(0)
    alarm.alarm_arm_away()
    vedo.arm.assert_called_once_with(0)
    alarm.alarm_arm_night()
    vedo.arm_night.assert_called_once_with(0)
    assert alarm.code_arm_required is False
    assert alarm.supported_features == (
        AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )

    motion = VedoSensor(1, "Door", STATE_ON)
    assert motion.is_on
    assert motion.device_class == BinarySensorDeviceClass.MOTION
