from custom_components.comelit import light
from homeassistant import const

if __name__ == '__main__':
    print('TEST')
    light_hub = None
    t = light.ComelitLight('myid', 'yodesc', const.STATE_ON, 255, light_hub)