#!/usr/bin/python3
import multiprocessing as mp
import modules.gpio_controller as gpio_controller
import modules.drive_controller as drive_controller
import modules.webserver as webserver
import time
import signal
import sys
import math
import logging
from logging.handlers import RotatingFileHandler
import pickle
from modules.command import Command
from modules.command import Controller
from modules.command import State
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_master import BrickMaster
from tinkerforge.bricklet_analog_in import BrickletAnalogIn
from tinkerforge.bricklet_gps import BrickletGPS
from collections import namedtuple


logger = logging.getLogger("mower")
logger.setLevel(logging.WARN)
filehandler = RotatingFileHandler('/home/pi/mower/main_controller.log', maxBytes=100000, backupCount=2)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(filename)s:%(lineno)s  --  %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)

ipcon = IPConnection()
TargetCoord = namedtuple('TargetCoord', 'lat, lon')
g_target = TargetCoord(lat=49.31899296, lon=8.80862925)


def signal_handler(signal_type, frame):
    logger.info("Terminate main_controller")
    sys.exit(0)


def undervolt_callback(voltage):
    volt = voltage / 1000.0
    logger.warning("Undervoltage detected. Voltage is {} V".format(str(volt)))
    drive_controller_connection.send(Command(Controller.drive, State.stop))


# Bumper
def bumper_triggered(voltage):
    logger.info("Bumper triggered")
    drive_controller_connection.send(Command(Controller.drive, State.stop))


# pressure can change over time due to environmental changes -> threshold must be adjusted
def adjust_bumper_threshold(voltage):
    analog_bumper.set_voltage_callback_threshold('>', int(voltage * 1.3), 0)


def gps_coordinates(lat, ns, lon, ew, pdop, hdop, vdop, epe):
    # lat, lon are in DD.dddddd° format. 57123468 means 57,123468° 
    lat = lat / 1000000.0
    lon = lon / 1000000.0
    fix_status, _, _ = gps.get_status()
    if fix_status == BrickletGPS.FIX_NO_FIX:
        return
    current_course, current_speed = gps.get_motion()
    current_course = current_course / 100.0
    current_speed = current_speed / 100.0
    logger.info("GPS coordinates: Latitude: {}, Longitude: {}, Position Error: {} cm, Course: {}, Speed: {}"\
        .format(lat, lon, epe, current_course, current_speed))
    target_course = calculate_target_course(lat, lon)
    course_diff = abs(target_course - current_course)
    slowdown_factor_left = 1.0
    slowdown_factor_right = 1.0
    if course_diff <=180.0: # right turn
        slowdown_factor_right = 1 - (course_diff / 180)
    else: # left turn
        slowdown_factor_left = (course_diff - 180) / (359.99 - 180)

    drive_controller_connection.send(
        Command(Controller.drive, State.correct_heading, (slowdown_factor_left, slowdown_factor_right))
    )


def calculate_target_course(current_lat, current_lon):
    lat1 = math.radians(current_lat)
    lat2 = math.radians(g_target.lat)
    diff_long = math.radians(g_target.lon - current_lon)
    x = math.sin(diff_long) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diff_long))
    initial_bearing = math.atan2(x, y)
    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Starting main_controller")

    # initialize master connection
    ipcon.connect('localhost', 4223)
    time.sleep(1.0)
    master_brick = BrickMaster('6QHvJ1', ipcon)
    master_brick.disable_status_led()
    master_brick.register_callback(master_brick.CALLBACK_STACK_VOLTAGE_REACHED, undervolt_callback)
    master_brick.set_stack_voltage_callback_threshold('<', 21000, 0)  # 21 Volt
    master_brick.set_debounce_period(100000)

    # initialize bumper
    analog_bumper = BrickletAnalogIn('bK7', ipcon)
    analog_bumper.set_range(BrickletAnalogIn.RANGE_UP_TO_6V)
    current_volt = analog_bumper.get_voltage()
    analog_bumper.register_callback(analog_bumper.CALLBACK_VOLTAGE_REACHED, bumper_triggered)
    analog_bumper.set_voltage_callback_threshold('>', int(current_volt * 1.3), 0)
    analog_bumper.set_debounce_period(2000)
    analog_bumper.register_callback(analog_bumper.CALLBACK_VOLTAGE, adjust_bumper_threshold)
    analog_bumper.set_voltage_callback_period(10000)

    # initialize gps
    gps = BrickletGPS('sqe', ipcon)
    gps.register_callback(gps.CALLBACK_COORDINATES, gps_coordinates)
    gps.set_coordinates_callback_period(1000)

    # start gpio controller
    gpio_controller_connection, gpio_child_connection = mp.Pipe()
    gpio_process = mp.Process(target=gpio_controller.start, args=(gpio_child_connection,), name="GPIO Controller Process")
    gpio_process.daemon = True
    gpio_process.start()

    # start drive controller
    drive_controller_connection, drive_child_connection = mp.Pipe()
    drive_process = mp.Process(target=drive_controller.start, args=(drive_child_connection,), name="Drive Controller Process")
    drive_process.daemon = True
    drive_process.start()

    # start webserver process
    webserver_connection, webserver_child_connection = mp.Pipe()
    webserver_process = mp.Process(target=webserver.start, args=(webserver_child_connection,), name="Webserver Process")
    webserver_process.daemon = True
    webserver_process.start()


    while True:
        # check for commands from started processes
        if webserver_connection.poll():
            cmd = webserver_connection.recv()
            logger.info("Command from webserver {}".format(str(cmd)))
            if cmd.controller is Controller.drive:

                drive_controller_connection.send(cmd)
            elif cmd.controller is Controller.gpio:
                gpio_controller_connection.send(cmd)
            else:
                logger.error("Wrong external command. Command {} does not exist".format(str(cmd)))

        time.sleep(0.05)

