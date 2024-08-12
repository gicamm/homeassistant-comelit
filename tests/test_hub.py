from custom_components.comelit import ComelitHub
from custom_components.comelit.sensor import HumiditySensor
import json
import os
import pytest
from unittest.mock import patch


# Extracted class outside the function
class MockResponse:
    def recv(self, *args, **kwargs):
        return 'mocked data'.encode()  # Mocked data you want to return

    def settimeout(self, *args, **kwargs):
        pass  # Since it's a mock, no operation is needed.

    def bind(self, *args, **kwargs):
        pass  # Since it's a mock, no operation is needed.

    def connect(self, *args, **kwargs):
        pass

    def setblocking(self, *args, **kwargs):
        pass

    def setsockopt(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass


def mock_hub_return(*args, **kwargs):
    # Now the function will return an instance of the extracted class
    return MockResponse()


@pytest.mark.asyncio
@patch("socket.socket", side_effect=mock_hub_return)
async def test_hub_sensors(hass):
    global hub_instance
    hub_instance = ComelitHub(client_name='test', hub_serial='00000000', hub_host='127.0.0.1', hub_user='user',
                              hub_password='pwd',
                              mqtt_port=1883, mqtt_user='user', mqtt_password='pwd', scan_interval=30)
    hub_instance.sensor_add_entities = lambda *args, **kwargs: None

    # test the humidity sensor
    humidity_sensor_name = 'hs1'
    humidity_sensor_id = f'comelit_humidity_{humidity_sensor_name}'
    humidity_sensor_description = humidity_sensor_name
    humidity_sensor_humidity = 50
    humidity_sensor = HumiditySensor(humidity_sensor_name, humidity_sensor_description, humidity_sensor_humidity)
    hub_instance.add_or_update_sensor(humidity_sensor, humidity_sensor_humidity)
    assert humidity_sensor_id in hub_instance.sensors
    assert hub_instance.sensors[humidity_sensor_id].unit_of_measurement == '%'


def load_status():
    filename = 'hub_status.json'
    if not os.path.exists(filename):
        filename = 'tests/hub_status.json'
    with open(filename, 'r') as json_file:
        return json.load(json_file)


@pytest.mark.asyncio
@patch("socket.socket", side_effect=mock_hub_return)
async def test_hub_status(hass):
    global hub_instance
    hub_instance = ComelitHub(client_name='test', hub_serial='00000000', hub_host='127.0.0.1', hub_user='user',
                              hub_password='pwd',
                              mqtt_port=1883, mqtt_user='user', mqtt_password='pwd', scan_interval=30)
    hub_instance.sensor_add_entities = lambda *args, **kwargs: None
    hub_instance.light_add_entities = lambda *args, **kwargs: None
    hub_instance.cover_add_entities = lambda *args, **kwargs: None
    hub_instance.climate_add_entities = lambda *args, **kwargs: None
    hub_instance.scene_add_entities = lambda *args, **kwargs: None

    status = load_status()
    hub_instance.status(status)

    assert len(hub_instance.sensors) == 6
    assert len(hub_instance.lights) == 11
    assert len(hub_instance.covers) == 2
    assert len(hub_instance.climates) == 2
    assert len(hub_instance.switches) == 0
