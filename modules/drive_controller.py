import requests
import logging, configparser
from collections import OrderedDict

from tinkerforge.ip_connection import IPConnection
from tinkerforge.bricklet_temperature import Temperature
from tinkerforge.bricklet_humidity import Humidity
from tinkerforge.bricklet_barometer import Barometer

cfg = configparser.ConfigParser()
cfg.read('./ha2/tools/config.txt')

logger = logging.getLogger("ha_logger")

weather_data = OrderedDict()
weather_data['temperature'] = '16.9'
weather_data['temperature_unit'] = 'Grad'
weather_data['humidity'] = '73.8'
weather_data['humidity_unit'] = '%RH'
weather_data['pressure'] = '1013.6'
weather_data['pressure_unit'] = 'mbar'


def read_data(fake=None):
    """ Reads data from all weather sensors and returns it as Dictionary.
        In case of an error or outlier None is returned"""
    if fake:
        return weather_data

    try:
        ipcon = IPConnection()
        temp_bricklet = Temperature('qnk', ipcon)
        humidity_bricklet = Humidity('nLC', ipcon)
        barometer_bricklet = Barometer('k5g', ipcon)
        ipcon.connect(cfg['weather']['host'], int(cfg['weather']['port']))
        temp_bricklet.set_i2c_mode(Temperature.I2C_MODE_SLOW)

        temp = temp_bricklet.get_temperature() / 100.0
        if 45 < temp < -30:
            weather_data['temperature'] = None
            logger.warn('Got temperature value of %s Grade which is out of range' % temp)
        else:
            weather_data['temperature'] = temp

        humidity = humidity_bricklet.get_humidity() / 10.0
        if humidity < 5:
            weather_data['humidity'] = None
            logger.warn('Got humidity value of %s RH which is out of range' % humidity)
        else:
            weather_data['humidity'] = humidity

        pressure = barometer_bricklet.get_air_pressure() / 1000.0
        if 1080 < pressure < 930:
            weather_data['pressure'] = None
            logger.warn('Got pressure value of %s mbar which is out of range' % pressure)
        else:
            weather_data['pressure'] = pressure

        ipcon.disconnect()
        return weather_data

    except Exception as e:
        logger.error('Cloud not connect to weather sensors: %s' % str(e))
        return
