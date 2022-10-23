"""Comelit Hub/Vedo integration."""

import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL)
from .hub import ComelitHub
from .vedo import ComelitVedo
from .const import DOMAIN, HUB_DOMAIN, VEDO_DOMAIN, CONF_MQTT_USER, CONF_MQTT_PASSWORD, CONF_SERIAL, CONF_CLIENT
_LOGGER = logging.getLogger(__name__)


HUB_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=1883): cv.port,
        vol.Optional(CONF_MQTT_USER, default="hsrv-user"): cv.string,
        vol.Optional(CONF_MQTT_PASSWORD, default="sf1nE9bjPc"): cv.string,
        vol.Required(CONF_SERIAL): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_CLIENT, default="homeassistant"): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=1): cv.positive_int
    }
)

VEDO_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=80): cv.port,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=1): cv.positive_int
    }
)


def setup(hass, config):
    conf = config[DOMAIN]
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]['conf'] = conf

    # Comelit Hub
    if 'hub' in conf:
        hub_conf = conf["hub"]
        if hub_conf is not None:
            schema = HUB_SCHEMA(hub_conf)
            hub_host = schema[CONF_HOST]
            mqtt_port = schema[CONF_PORT]
            mqtt_user = schema[CONF_MQTT_USER]
            mqtt_password = schema[CONF_MQTT_PASSWORD]
            hub_user = schema[CONF_USERNAME]
            scan_interval = schema[CONF_SCAN_INTERVAL]
            hub_password = schema[CONF_PASSWORD]
            hub_serial = schema[CONF_SERIAL]
            hub_client = schema[CONF_CLIENT]
            hub = ComelitHub(hub_client, hub_serial, hub_host, mqtt_port, mqtt_user, mqtt_password, hub_user,
                             hub_password, scan_interval)
            hass.data[DOMAIN]['hub'] = hub
            hass.helpers.discovery.load_platform('sensor', DOMAIN, {}, config)
            hass.helpers.discovery.load_platform('light', DOMAIN, {}, config)
            hass.helpers.discovery.load_platform('cover', DOMAIN, {}, config)
            hass.helpers.discovery.load_platform('scene', DOMAIN, {}, config)
            hass.helpers.discovery.load_platform('switch', DOMAIN, {}, config)
            _LOGGER.info("Comelit Hub integration started")

    # Comelit Vedo
    if 'vedo' in conf:
        vedo_conf = conf["vedo"]
        if vedo_conf is not None:
            schema = VEDO_SCHEMA(vedo_conf)
            vedo_host = schema[CONF_HOST]
            vedo_port = schema[CONF_PORT]
            vedo_pwd = schema[CONF_PASSWORD]
            scan_interval = schema[CONF_SCAN_INTERVAL]
            vedo = ComelitVedo(vedo_host, vedo_port, vedo_pwd, scan_interval)
            hass.data[DOMAIN]['vedo'] = vedo
            # hass.helpers.discovery.load_platform('binary_sensor', DOMAIN, {}, config)
            hass.helpers.discovery.load_platform('alarm_control_panel', DOMAIN, {}, config)
            _LOGGER.info("Comelit Vedo integration started")

    return True
