from custom_components.comelit import ComelitVedo
import pytest


@pytest.mark.asyncio
async def test_vedo_sensor(hass):
    vedo_instance = ComelitVedo(host='127.0.0.1', port=80, password='pwd', scan_interval=30, expose_bin_sensors=True)
    vedo_instance.binary_sensor_add_entities = lambda *args, **kwargs: None

    sensor_dict = {"index": 1, "id": 1, "name": "garage", "status": "0011"}
    vedo_instance.update_sensor(sensor_dict)

    assert len(vedo_instance.sensors) == 1
