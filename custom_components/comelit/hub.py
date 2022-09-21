"""Platform for sensor integration."""
import time
import json

import paho.mqtt.client as mqtt
from threading import Thread

from homeassistant.const import STATE_CLOSED, STATE_OPEN, STATE_CLOSING, STATE_OPENING, STATE_ON, STATE_OFF, \
    STATE_UNKNOWN

from .scene import ComelitScenario
from .sensor import PowerSensor, TemperatureSensor, HumiditySensor
from .light import ComelitLight
from .cover import ComelitCover
from .switch import ComelitSwitch
import logging

_LOGGER = logging.getLogger(__name__)

COMELIT_HUB_COMPONENTS = [
    'climate',
    'light',
    'sensor',
    'switch',
]


class RequestType:
    STATUS = 0
    LIGHT = 1
    AUTOMATION = 1
    COVER = 1
    SCENARIO = 1
    ANNOUNCE = 13
    LOGIN = 5
    PARAMETERS = 8


class HubFields:
    TOKEN = 'sessiontoken'
    TEMPERATURE = 'temperatura'
    HUMIDITY = 'umidita'
    DESCRIPTION = 'descrizione'
    INSTANT_POWER = 'instant_power'
    ID = 'id'
    PRODUCTION = 'prod'
    ELEMENTS = 'elements'
    COVER_STATUS = 'open_status'
    STATUS = 'status'
    DATA = 'data'
    PARAMETER_NAME = 'param_name'
    PARAMETER_VALUE = 'param_value'


class HubClasses:
    LOGICAL = 'GEN#PL'
    AUTOMATION = 'DOM#AU'
    LIGHT = 'DOM#LT'
    FTV = 'DOM#CN'
    POWER_CONSUMPTION = 'DOM#CN'
    LOAD = 'DOM#LC'
    TEMPERATURE = 'DOM#CL'
    SCENARIO = 'DOM#LD'
    COVER = 'DOM#BL'
    SCENARIO = 'GEN#SC'
    OTHER = 'DOM#LD'


# Publish message to mqtt
def publish(client, topic, agent_id, sequence_id, sessiontoken, data):
    try:
        data["seq_id"] = sequence_id
        data["agent_id"] = agent_id
        data["sessiontoken"] = sessiontoken
        jsonD = json.dumps(data)
        client.publish(topic, jsonD)
        client.hub.sequence_id = client.hub.sequence_id + 1
    except Exception as e:
        _LOGGER.exception("Error publishing message %s", e)


def on_message_callback(client, userdata, message):
    js = str(message.payload.decode("utf-8"))
    payload = json.loads(js)
    client.hub.dispatch(payload)


def connect_callback(client, userdata, flags, rc):
    try:
        _LOGGER.info("connected to comelit hub")
        client.hub.announce()
    except Exception as e:
        _LOGGER.exception(e)


def disconnect_callback(client, userdata, rc):
    _LOGGER.info("disconnected from hub")


# Manage lights, switch and covers
class CommandHub:

    def __init__(self, hub):
        self._hub = hub

    def on(self, req_type, id, brightness=None):
        try:
            if brightness is None:
                act_params = [1]
                act_type = 0
            else:
                if req_type is not RequestType.LIGHT:
                    _LOGGER.error(f'Requested brightness change for a {req_type}!?')
                act_params = [brightness, -1]
                act_type = 11

            req = {"req_type": req_type, "req_sub_type": 3, "obj_id": id, "act_type": act_type, "act_params": act_params}
            self._hub.publish(req)
        except Exception as e:
            _LOGGER.exception("Error opening %s", e)

    def off(self, req_type, id):
        try:
            req = {"req_type": req_type , "req_sub_type": 3, "obj_id": id, "act_type": 0, "act_params": [0]}
            self._hub.publish(req)
        except Exception as e:
            _LOGGER.exception("Error closing %s", e)

    def light_on(self, id, brightness=None):
        self.on(RequestType.LIGHT, id, brightness)

    def light_off(self, id):
        self.off(RequestType.LIGHT, id)

    def switch_on(self, id):
        self.on(RequestType.AUTOMATION, id)

    def switch_off(self, id):
        self.off(RequestType.AUTOMATION, id)

    def cover_up(self, id):
        self.on(RequestType.COVER, id)

    def cover_position(self, id, position):
        try:
            _LOGGER.info(f'Setting cover {id} to position {position}')
            req = {"req_type": RequestType.COVER, "req_sub_type": 3, "obj_id": id, "act_type": 52, "act_params": [int(position*255/100)]}
            self._hub.publish(req)
        except Exception as e:
            _LOGGER.exception("Error setting position %s", e)

    def cover_down(self, id):
        self.off(RequestType.COVER, id)


# Manage scenario
class SceneHub:

    def __init__(self, hub):
        self._hub = hub

    def activate(self, id):
        _LOGGER.info("SCENE %s", id)
        try:
            req = {"req_type": RequestType.SCENARIO, "req_sub_type": 3, "obj_id": id, "act_type": 1000, "act_params": []}
            self._hub.publish(req)
        except Exception as e:
            _LOGGER.exception("Error activating the scenario %s", e)


class ComelitHub:

    def __init__(self, client_name, hub_serial, hub_host, mqtt_port, mqtt_user, mqtt_password, hub_user, hub_password, scan_interval):
        """Initialize the sensor."""
        self.sensors = {}
        self.lights = {}
        self.covers = {}
        self.scenes = {}
        self.switches = {}
        self.client_name = client_name
        self.sequence_id = 1
        self.agent_id = 10
        self.sessiontoken = ""
        self.hub_serial = hub_serial
        self.hub_host = hub_host
        self.mqtt_user = mqtt_user
        self.mqtt_port = mqtt_port
        self.hub_user = hub_user
        self.hub_password = hub_password
        self.mqtt_password = mqtt_password
        self._scan_interval = scan_interval
        self._vedo = None
        self._vip = None
        self._music = None
        self.client = mqtt.Client(client_name)
        _LOGGER.info("{0} {1}:{2} {3}".format("Starting Comelit Hub integration", hub_host, mqtt_port, hub_serial))
        self.topic_rx = "{0}/{1}/{2}/{3}".format("HSrv", hub_serial, "rx", client_name)
        self.topic_tx = "{0}/{1}/{2}/{3}".format("HSrv", hub_serial, "tx", client_name)
        self.client.hub = self

        self.client.on_message = on_message_callback
        self.client.on_connect = connect_callback
        self.client.on_disconnect = disconnect_callback
        self.client.username_pw_set(mqtt_user, mqtt_password)
        self.client.connect(hub_host, mqtt_port, 45)
        self.client.subscribe(self.topic_tx)
        thread1 = StatusUpdater("Thread#1", self._scan_interval, self)
        thread1.start()
        self.client.loop_start()

    def dispatch(self, payload):
        try:
            req_type = payload["req_type"]

            options = {
                RequestType.ANNOUNCE: self.manage_announce,
                RequestType.LOGIN: self.token,
                RequestType.STATUS: self.status,
                RequestType.PARAMETERS: self.parse_parameters,
            }
            options[req_type](payload)
        except Exception as e:
            _LOGGER.error(e)

    def manage_announce(self, payload):
        self.agent_id = payload['out_data'][0]["agent_id"]
        _LOGGER.debug("agent id is %s", self.agent_id)
        req = {"req_type": RequestType.LOGIN, "req_sub_type": -1, "agent_type": 0, "user_name": self.hub_user,
               "password": self.hub_password}
        self.publish(req)

    def token(self, payload):
        self.sessiontoken = payload[HubFields.TOKEN]

    def announce(self):
        req = {"req_type": RequestType.ANNOUNCE, "req_sub_type": -1, "agent_type": 0}
        self.publish(req)

    def parse_parameters(self, payload):
        parameters = payload["params_data"]
        for parameter in parameters:
            name = parameter[HubFields.PARAMETER_NAME]
            value = parameter[HubFields.PARAMETER_VALUE]

            if name == "alarmDevicePass":
                self._vedo["password"] = value
            elif name == "alarmLocalAddress":
                self._vedo["host"] = value
            elif name == "alarmLocalPort":
                self._vedo["port"] = value
            elif name == "alarmLocalPort":
                self._vedo["port"] = value
            elif name == "vipEnable":
                self._vip["enable"] = value == "1"
            elif name == "musicEnable":
                self._music["enable"] = value == "1"

        req = {"req_type": RequestType.ANNOUNCE, "req_sub_type": -1, "agent_type": 0}
        self.publish(req)

    def publish(self, data):
        publish(self.client, self.topic_rx, self.agent_id, self.sequence_id, self.sessiontoken, data)
        self.sequence_id = self.sequence_id + 1

    def update_sensor(self, id, description, data):
        try:
            if HubClasses.POWER_CONSUMPTION in id or HubClasses.FTV in id:
                value = format(float(data[HubFields.INSTANT_POWER]), '.2f')
                prod = data[HubFields.PRODUCTION] == "1"
                sensor = PowerSensor(id, description, value, prod)
            else:
                value = format(float(data[HubFields.TEMPERATURE]), '.1f')
                value = float(value) / 10
                sensor = TemperatureSensor(id, description, value)

                if data["type"] == 9 and data["sub_type"] == 16:# Add the humidity sensor
                    humidity = data[HubFields.HUMIDITY]
                    humidity_sensor = HumiditySensor(id, description, humidity)
                    self.add_or_update_sensor(humidity_sensor, humidity)

            self.add_or_update_sensor(sensor, value)
        except Exception as e:
            _LOGGER.exception("Error updating sensor %s", e)

    def add_or_update_sensor(self, sensor, value):
        name = sensor.entity_name
        if sensor.name not in self.sensors:  # Add the new sensor
            if hasattr(self, 'sensor_add_entities'):
                self.sensor_add_entities([sensor])
                self.sensors[name] = sensor
                _LOGGER.info("added the sensor %s", name)
        else:
            self.sensors[name].update_state(value)
            _LOGGER.debug("updated the sensor %s", name)

    def update_light(self, id, description, data):
        try:
            _LOGGER.debug("update_light: %s has data %s", description, data)
            
            # Dimmable light (3=light, 4=dimmable)
            if data["type"] == 3 and data["sub_type"] == 4:
                brightness = int(data["bright"])
            else:
                brightness = None

            if data["status"] == "1":
                state = STATE_ON
            else:
                state = STATE_OFF

            light = ComelitLight(id, description, state, brightness, CommandHub(self))
            if id not in self.lights:  # Add the new sensor
                if hasattr(self, 'light_add_entities'):
                    self.light_add_entities([light])
                    self.lights[id] = light
                    _LOGGER.info("added the light %s %s", description, light.entity_name)
            else:
                _LOGGER.debug("updating the light %s %s", description, light.entity_name)
                self.lights[id].update_state(state)
        except Exception as e:
            _LOGGER.exception("Error updating light %s", e)

    def update_cover(self, id, description, data, status_key):
        try:
            if 'position' in data:
                if data['status'] == '0':
                    # Not moving
                    if data['open_status'] == '1':
                        state = STATE_OPEN
                    else:
                        state = STATE_CLOSED
                elif data['status'] == '1':
                    state = STATE_OPENING
                elif data['status'] == '2':
                    state = STATE_CLOSING

                position = int(100 * float(data['position']) / 255)
            else:  # unable to define the position. works for legacy cover
                state = STATE_UNKNOWN
                position = -1

            if id not in self.covers:  # Add the new cover
                if hasattr(self, 'cover_add_entities'):
                    cover = ComelitCover(id, description, state, position, CommandHub(self))
                    self.cover_add_entities([cover])
                    self.covers[id] = cover
                    _LOGGER.info("added the cover %s %s", description, id)
            else:
                _LOGGER.debug("updating the cover %s %s", description, id)
                self.covers[id].update_state(state, position)
        except Exception as e:
            _LOGGER.exception("Error updating the cover %s", e)

    def update_scenario(self, id, description, data):
        try:
            scene = ComelitScenario(id, description, SceneHub(self))
            if id not in self.scenes:  # Add the new cover
                if hasattr(self, 'scene_add_entities'):
                    self.scene_add_entities([scene])
                    self.scenes[id] = scene
                    _LOGGER.info("added the scene %s %s", description, id)
        except Exception as e:
            _LOGGER.exception("Error updating the scene %s", e)

    def update_switch(self, id, description, data):
        try:
            switch = ComelitSwitch(id, description, None, CommandHub(self))
            if data[HubFields.STATUS] == '1':
                state = STATE_ON
            else:
                state = STATE_OFF

            if id not in self.switches:  # Add the new cover
                if hasattr(self, 'switch_add_entities'):
                    self.switch_add_entities([switch])
                    self.switches[id] = switch
                    _LOGGER.info("added the switch %s %s", description, id)
            else:
                _LOGGER.debug("updating the switch %s %s", description, id)
                self.switches[id].update_state(state)
        except Exception as e:
            _LOGGER.exception("Error updating the switch %s", e)

    def update_entities(self, elements):
        try:
            for item in elements:

                id = item[HubFields.ID]

                if HubClasses.LOGICAL in id:
                    logical_elements = item[HubFields.DATA][HubFields.ELEMENTS]
                    for logical_element in logical_elements:
                        logical_data = logical_element[HubFields.DATA]
                        if HubClasses.LOGICAL in logical_data[HubFields.ID]:
                            self.update_entities(logical_data[HubFields.ELEMENTS])
                        else:
                            self.update_entities([logical_data])

                try:
                    item = item[HubFields.DATA]
                except Exception:
                    item = item

                if HubClasses.POWER_CONSUMPTION in id or HubClasses.FTV in id or HubClasses.TEMPERATURE in id:  # Sensor
                    description = item[HubFields.DESCRIPTION]
                    self.update_sensor(id, description, item)
                elif HubClasses.LIGHT in id:
                    description = item[HubFields.DESCRIPTION]
                    self.update_light(id, description, item)
                elif HubClasses.COVER in id:
                    description = item[HubFields.DESCRIPTION]
                    self.update_cover(id, description, item, HubFields.COVER_STATUS)
                elif HubClasses.AUTOMATION in id:
                    description = item[HubFields.DESCRIPTION]
                    self.update_cover(id, description, item, HubFields.STATUS)
                elif HubClasses.SCENARIO in id:
                    description = item[HubFields.DESCRIPTION]
                    self.update_scenario(id, description, item)
                elif HubClasses.OTHER in id:
                    description = item[HubFields.DESCRIPTION]
                    self.update_switch(id, description, item)
                else:
                    continue
        except Exception as e:
            _LOGGER.error(e)

    def status(self, payload):
        try:
            elements = payload["out_data"][0][HubFields.ELEMENTS]
            self.update_entities(elements)
        except Exception as e:
            _LOGGER.error(e)


# Make a request for status
class StatusUpdater (Thread):
    def __init__(self, name, scan_interval, hub):
        Thread.__init__(self)
        self.name = name
        self._scan_interval = scan_interval
        self.hub = hub

    def run(self):
        parameters_timer = 0
        _LOGGER.debug("Comelit Hub status snapshot started")
        while True:
            if self.hub.sessiontoken == "":
                continue

            if parameters_timer == 0:
                {"req_type": 8, "seq_id": 5, "req_sub_type": 23, "param_type": 2, "agent_type": 0,
                 "sessiontoken": "1367343208"}
                parameters_timer = 30

            req = {"req_type": RequestType.STATUS, "req_sub_type": -1, "obj_id": "GEN#17#13#1", "detail_level": 1}
            self.hub.publish(req)
            time.sleep(self._scan_interval)
            parameters_timer = parameters_timer - 1

