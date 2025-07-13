import unittest
from unittest.mock import patch, Mock
from homeassistant.const import (CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL,
                                 CONF_BINARY_SENSORS)
from custom_components.comelit import setup, CONF_SERIAL


class TestInit(unittest.TestCase):

    @patch("custom_components.comelit.ComelitHub")
    @patch("homeassistant.helpers.discovery.load_platform")
    def test_hub(self, mock_discovery, mock_ComelitHub):
        hub_port = 1883
        hub_address = 'localhost'
        hub_user = 'user'
        hub_pwd = 'pwd'
        hub_serial = '00000'
        hub_client = 'homeassistant'
        mqtt_user = 'hsrv-user'
        mqtt_pwd = 'sf1nE9bjPc'
        scan_interval = 30

        hass = Mock()
        hass.data = {}
        conf = {
            "hub": {
                CONF_HOST: hub_address, CONF_USERNAME: hub_user, CONF_PASSWORD: hub_pwd,
                CONF_PORT: hub_port, CONF_SCAN_INTERVAL: scan_interval, CONF_SERIAL: hub_serial
            }
        }
        config = {"comelit": conf}

        setup(hass, config)

        self.assertTrue(hass.data["comelit"]['hub'])

        # assert Comelit Hub got the correct arguments
        mock_ComelitHub.assert_called_with(hub_client, hub_serial, hub_address, hub_port, mqtt_user, mqtt_pwd,
                                           hub_user, hub_pwd, scan_interval)

    @patch("custom_components.comelit.ComelitVedo")
    @patch("homeassistant.helpers.discovery.load_platform")
    def test_vedo(self, mock_discovery, mock_ComelitVedo):
        vedo_host = "localhost"
        vedo_pwd = "123456"
        vedo_port = 80
        scan_interval = 30
        expose_bin_sensors = True
        hass = Mock()
        hass.data = {}
        conf = {
            "vedo": {
                CONF_HOST: vedo_host, CONF_PASSWORD: vedo_pwd,
                CONF_PORT: vedo_port, CONF_SCAN_INTERVAL: scan_interval,
                CONF_BINARY_SENSORS: expose_bin_sensors
            }
        }
        config = {"comelit": conf}

        setup(hass, config)

        self.assertTrue(hass.data["comelit"]['vedo'])

        # assert Comelit Vedo got the correct arguments
        mock_ComelitVedo.assert_called_with(vedo_host, vedo_port, vedo_pwd, scan_interval, expose_bin_sensors)
