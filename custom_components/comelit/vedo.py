"""Platform for sensor integration."""

import json
import time
import requests
import logging
from threading import Thread
from wrapt_timeout_decorator import *
from homeassistant.const import STATE_ALARM_DISARMED, STATE_ALARM_ARMED_AWAY, STATE_ON, STATE_OFF
from .binary_sensor import VedoSensor
from custom_components.comelit.alarm_control_panel import VedoAlarm

_LOGGER = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Accept-Language': 'it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3'
}

DEFAULT_TIMEOUT = 10
ARM_DISARM_ATTEMPT = 5


class VedoRequest:
    ZONE_STAT = "user/zone_stat.json"
    AREA_STAT = "user/area_stat.json"
    ZONE_DESC = "user/zone_desc.json"
    AREA_DESC = "user/area_desc.json"
    LOGIN = "login.cgi"
    ACTION = "action.cgi"


# Manage the Comelit Vedo Central. Fetches the alarm status and the motion status.
class ComelitVedo:

    def __init__(self, host, port, password, scan_interval):
        """Initialize the sensor."""
        _LOGGER.info(f"Initialising ComelitVedo with host {host}, port {port}")
        self.sensors = {}
        self.areas = {}
        self.host = host
        self.port = port
        self.password = password
        self._scan_interval = scan_interval
        thread1 = SensorUpdater("Thread#BS", scan_interval, self)
        thread1.start()

    # Build the HTTP request
    def build_http(self, headers, uid, path):
        if headers is None:
            headers = {}

        headers['User-Agent'] = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0'
        headers['X-Requested-With'] = 'XMLHttpRequest'
        headers['Accept'] = '*/*'
        headers['Connection'] = 'keep-alive'

        if uid is not None:
            headers['Cookie'] = uid

        millis = int(round(time.time() * 1000))
        if "?" in path:
            url = "http://{0}:{1}/{2}&_={3}".format(self.host, self.port, path, millis)
        else:
            url = "http://{0}:{1}/{2}?_={3}".format(self.host, self.port, path, millis)
        _LOGGER.info(f"Build URL: {url}")
        return url, headers

    # Do the GET from the vedo IP
    @timeout(DEFAULT_TIMEOUT, use_signals=True)
    def get(self, uid,  path, is_response):
        _LOGGER.info(f"Running GET with uid {uid}, path {path}")
        url, headers = self.build_http(None, uid, path)
        _LOGGER.info(f"GET: url {url}, headers {headers}")
        response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        text = response.text
        if is_response:
            payload = json.loads(text)
            return payload
        else:
            return text

    # Do the POST to the vedo IP
    @timeout(DEFAULT_TIMEOUT, use_signals=True)
    def post(self, url, params, headers):
        response = requests.post(url, data=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        return response

    # Do the login. Raise an exception if not able to get the cookie
    def login(self):
        headers = DEFAULT_HEADERS.copy()
        url, headers = self.build_http(headers, None, VedoRequest.LOGIN)
        params = {"code": self.password}
        response = self.post(url, params, headers)
        response.raise_for_status()
        if response.status_code == 200:
            uid = response.headers.get('set-cookie')
            if uid is not None:
                _LOGGER.info("Logged in, %s", response.text)
                return uid
            else:
                _LOGGER.warning("Error doing the login %s", response.text)
                raise Exception("Unable to obtain the cookie")
        else:
            _LOGGER.error("Bad login response! - %s", response.text)

    # Do the logout. Ignore errors
    def logout(self, uid):
        if uid is None:
            return

        try:
            headers = DEFAULT_HEADERS.copy()
            url, headers = self.build_http(headers, uid, VedoRequest.LOGIN)
            params = {"logout": 1}
            self.post(url, params, headers)  # Ignore the error
        except Exception:
            pass

    # Arm/Disarm the alarm. Try 5 times
    def arm_disarm(self, key, id):
        for i in range(1, ARM_DISARM_ATTEMPT+1):
            try:
                uid = self.login()
                path = "{0}?vedo=1&{1}={2}&force=1".format(VedoRequest.ACTION, key, id)
                self.get(uid, path, False)
                _LOGGER.info("Armed/Disarmed the area %s", id)
                self.logout(uid)
                break
            except Exception as e:
                if i == ARM_DISARM_ATTEMPT:
                    _LOGGER.exception("Error arming/disarming %s %s", id, e)
                else:
                    _LOGGER.exception("Error arming/disarming. Trying again.")

            time.sleep(DEFAULT_TIMEOUT)

    # arm the alarm
    def arm(self, id):
        _LOGGER.info("Arming the area %s", id)
        self.arm_disarm("tot", id)

    # disarm the alarm
    def disarm(self, id):
        _LOGGER.info("Disarming the area %s", id)
        self.arm_disarm("dis", id)

    # update the binary motion detection sensor
    def update_sensor(self, s):
        try:
            id = s["id"]
            name = s["name"]
            if s["status"] == "0011":
                state = STATE_ON
            else:
                state = STATE_OFF
            sensor = VedoSensor(id, name, state)
            if id not in self.sensors:
                if hasattr(self, 'binary_sensor_add_entities'):
                    self.binary_sensor_add_entities([sensor])
                    self.sensors[id] = sensor
                    _LOGGER.info("added the binary sensor %s %s", name, sensor.entity_name)
            else:
                _LOGGER.debug("updating the binary sensor %s %s", name, sensor.entity_name)
                self.sensors[id].update_state(state)
        except Exception as e:
            _LOGGER.exception("Error updating sensor %s", e)

    # update the alarm area
    def update_area(self, area):
        _LOGGER.debug(f"Updating the alarm area {area}")
        try:
            id = area["id"]
            name = area["name"]
            if area["armed"] == 4:
                state = STATE_ALARM_ARMED_AWAY
            else:
                state = STATE_ALARM_DISARMED

            alarm_area = VedoAlarm(id, name, state, self)
            if id not in self.areas:
                if hasattr(self, 'alarm_add_entities'):
                    self.alarm_add_entities([alarm_area])
                    self.areas[id] = alarm_area
                    _LOGGER.info("added the alarm area %s %s", name, alarm_area.entity_name)
            else:
                self.areas[id].update_state(state)
                _LOGGER.debug("updated the alarm area %s %s", name, alarm_area.entity_name)

        except Exception as e:
            _LOGGER.exception("Error updating alarm area %s", e)


# Update the binary sensors
class SensorUpdater (Thread):
    def __init__(self, name, scan_interval, vedo: ComelitVedo):
        Thread.__init__(self)
        self.name = name
        self._scan_interval = scan_interval
        self._vedo = vedo
        self._active = True
        self._uid = None

    # Invalidate the uid
    def logout(self):
        self._vedo.logout(self._uid)
        self._uid = None

    # Polls the sensors
    def run(self):
        _LOGGER.debug("Comelit Vedo status snapshot started")
        self._uid = None

        while self._active:
            try:
                if self._uid is None:
                    self._uid = self._vedo.login()
                    if self._uid is None:
                        continue

                zone_desc = self._vedo.get(self._uid, VedoRequest.ZONE_DESC, True)
                zone_status = self._vedo.get(self._uid, VedoRequest.ZONE_STAT, True)
                areas_desc = self._vedo.get(self._uid, VedoRequest.AREA_DESC, True)
                areas_stat = self._vedo.get(self._uid, VedoRequest.AREA_STAT, True)

                description = zone_desc["description"]
                zone_statuses = zone_status["status"].split(",")
                in_area = zone_desc["in_area"]
                descs = areas_desc["description"]
                ready = areas_stat["ready"]

                sensors = []

                if len(in_area) != len(zone_statuses) or len(descs) != len(ready):
                    raise Exception("error getting area")

                for i in range(len(in_area)):
                    value = in_area[i]
                    if value == 'Not logged':
                        raise Exception("cookie expired")

                    if value > 1:
                        sensor_dict = {"index": i, "id": i, "name": description[i], "status": zone_statuses[i]}
                        _LOGGER.debug(f"Updating the zone {sensor_dict}")
                        sensors.append(sensor_dict)

                if self._uid is not None:
                    # for sensor in sensors:
                    #     self._vedo.update_sensor(sensor)

                    p1_pres = areas_desc["p1_pres"]
                    p2_pres = areas_desc["p2_pres"]

                    armed = areas_stat["armed"]
                    alarm = areas_stat["alarm"]
                    alarm_memory = areas_stat["alarm_memory"]
                    sabotage = areas_stat["sabotage"]
                    anomaly = areas_stat["anomaly"]
                    in_time = areas_stat["in_time"]
                    out_time = areas_stat["out_time"]

                    for i in range(len(descs)):
                        area = {"name": descs[i],
                                "id": i,
                                "p1_pres": p1_pres[i],
                                "p2_pres": p2_pres[i],
                                "ready": ready[i],
                                "armed": armed[i],
                                "alarm": alarm[i],
                                "alarm_memory": alarm_memory[i],
                                "sabotage": sabotage[i],
                                "anomaly": anomaly[i],
                                "in_time": in_time[i],
                                "out_time": out_time[i]}
                        self._vedo.update_area(area)

            except Exception as e:
                _LOGGER.error("Error getting data! %s", e)
                self.logout()
            finally:
                time.sleep(self._scan_interval)
