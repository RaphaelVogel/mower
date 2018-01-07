#!/usr/bin/python3
import multiprocessing as mp
import modules.gpio_controller as gpio_controller
import modules.drive_controller as drive_controller
import time
import signal
import sys
import logging
from logging.handlers import RotatingFileHandler
import mmap
import pickle
from modules.command import Command
from modules.command import Controller
from modules.command import State
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_master import BrickMaster
from tinkerforge.bricklet_analog_in import BrickletAnalogIn


logger = logging.getLogger("mower")
logger.setLevel(logging.WARN)
filehandler = RotatingFileHandler('/home/pi/mower/main_controller.log', maxBytes=100000, backupCount=2)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(filename)s:%(lineno)s  --  %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)

ipcon = IPConnection()


def signal_handler(signal_type, frame):
    logger.info("Terminate main_controller")
    sys.exit(0)


def undervolt_callback(voltage):
    volt = voltage / 1000.0
    logger.warning("Undervoltage detected. Voltage is {} V".format(str(volt)))
    drive_controller_connection.send(Command(Controller.drive, State.stop))


# Bumper
def bumper_triggered(voltage):
    logger.warning("Bumper triggered")
    drive_controller_connection.send(Command(Controller.drive, State.stop))


# pressure can change over time due to environmental changes -> threshold must be adjusted
def adjust_bumper_threshold(voltage):
    analog_bumper.set_voltage_callback_threshold('>', int(voltage * 1.4), 0)


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
    analog_bumper.set_voltage_callback_threshold('>', int(current_volt * 1.4), 0)
    analog_bumper.set_debounce_period(2000)
    analog_bumper.register_callback(analog_bumper.CALLBACK_VOLTAGE, adjust_bumper_threshold)
    analog_bumper.set_voltage_callback_period(10000)


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

    while True:
        # check for external command e.g. from web server
        with open("/home/pi/mower/command", "r+") as file:
            mm_file = mmap.mmap(file.fileno(), 0)
            cmd = pickle.loads(mm_file.read())
            if cmd:
                logger.info("Command from webserver {}".format(cmd))
                mm_file.seek(0)
                mm_file.write(pickle.dumps(None))
                logger.info("External command received: {}".format(cmd))
                if cmd.controller is Controller.drive:
                    drive_controller_connection.send(cmd)
                elif cmd.controller is Controller.gpio:
                    gpio_controller_connection.send(cmd)
                else:
                    logger.error("Wrong external command. Command {} does not exist".format(cmd))

        time.sleep(0.5)

