import RPi.GPIO as GPIO
import sys
import signal
import time
import logging
import subprocess
from modules.command import State
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_master import BrickMaster


GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # GPIO4 is Board pin 7
logger = logging.getLogger("mower")

ipcon = IPConnection()


def signal_handler(signal_type, frame):
    GPIO.cleanup()
    logger.info("Terminate gpio_controller")
    sys.exit(0)


def start(main_controller_connection):
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Starting gpio_controller")

    while True:
        # Check GPIO
        if not GPIO.input(4):
            command = None
            presstime = 0
            for i in range(50):
                if not GPIO.input(4):
                    presstime += 1
                else:
                    command = State.reboot_system
                    break
                if presstime > 20:
                    command = State.shutdown_system
                    break
                time.sleep(0.1)

            ipcon.connect('localhost', 4223)
            time.sleep(1.0)
            master_brick = BrickMaster('6QHvJ1', ipcon)
            master_brick.reset()
            if command is State.reboot_system:
                subprocess.call(["sudo", "reboot"])
            elif command is State.shutdown_system:
                subprocess.call(["sudo", "shutdown", "-h", "now"])

        time.sleep(0.3)
