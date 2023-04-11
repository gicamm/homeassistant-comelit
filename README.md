# Comelit SimpleHome/Vedo integration for Home Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gicamm&repository=homeassistant-comelit&category=integration)

Comelit SimpleHome/Vedo integration lets you connect your Home Assistant instance to Comelit Simple Home and Vedo
systems.

For more information, see the [Wiki](https://github.com/gicamm/homeassistant-comelit/wiki).

### Installation

- Install
  using [HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=gicamm&repository=homeassistant-comelit&category=integration) (
  Or copy the contents of `custom_components/comelit/` to `<your config dir>/custom_components/comelit/`.)
- Add the following to your `<your config dir>/configuration.yaml` file:

```yaml
# Comelit Hub/Vedo
comelit:
  hub:
    host: HUB IP ADDRES
    port: 1883
    mqtt-user: hsrv-user
    mqtt-password: sf1nE9bjPc
    username: HUB USER
    password: HUB PASSWORD
    serial: HUB SERIAL
    client: homeassistant
    scan_interval: 2
  vedo:
    host: VEDO IP ADDRESS
    port: 80
    password: VEDO PASSWORD
    scan_interval: 30

```

- Restart Home Assistant

### How to find the hub serial?

#### Comelit app

- Open the Comelit app
- Scan for a new hub device
- Copy the serial (remove all non-numeric characters, i.e. 'hsrv-0123456789' -> '0123456789' )

For more information, see the [Wiki](https://github.com/gicamm/homeassistant-comelit/wiki).

### Supported features
- Lights
- Shutters
- Energy Production
- Energy Consumption
- Clima
- Temperature/Humidity
- Automation
- Scenario
- Alarm

The integration also exports the alarm sensor as a presence detector. It allows presence-based lights, scenes, and so
on.

#### Comelit scenario

The integration supports the comelit scenario. It exports the scenario as a scene. A scene can be useful for exporting
some VIP features (such as opening the door) which, otherwise, cannot be fully reachable through the Hub.

### Lovelace example

Below is an example with lovelace:

```yaml
- type: entities
  title: Test
  entities:

# lights
  - entity: light.comelit_light_garage
    name: Garage
  - entity: light.comelit_light_bathroom
    name: Bathroom

# power
  - entity: sensor.comelit_power_prod_ftv
    name: Production
  - entity: sensor.comelit_power_cons
    name: Consume

    # door lock
  - entity: scene.comelit_doorlock
    name: Door lock
    icon: mdi:key

    # switch
  - entity: switch.comelit_switch1
    name: Switch1

    # clima
  - entity: climate.comelit_bathroom
    name: Bathroom
  - entity: climate.comelit_living
    name: Living

    # humidity
  - entity: sensor.comelit_humidity_bathroom
    name: Bathroom
  - entity: sensor.comelit_humidity_living
    name: Living

    # temperature
  - entity: sensor.comelit_temperature_bathroom
    name: Bathroom
  - entity: sensor.comelit_temperature_living
    name: Living

    # shutters
  - entity: cover.comelit_living
    name: Living
  - entity: cover.comelit_kitchen_sx
    name: Kitchen

    # vedo Alarm
  - entity: binary_sensor.comelit_vedo_garage
    name: Garage
  - entity: alarm_control_panel.comelit_vedo_garage
    name: Garage

```
