import RPi.GPIO as GPIO
import sys
import signal
import time
import logging
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_master import BrickMaster


GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # GPIO4 is Board pin 7

ipcon = IPConnection()

logger = logging.getLogger("mower")


def signal_handler(signal_type, frame):
    GPIO.cleanup()
    if ipcon.get_connection_state() == IPConnection.CONNECTION_STATE_CONNECTED:
        ipcon.disconnect()
    logger.info("Terminate shutdown_controller")
    sys.exit(0)


def start(parent_conn):
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Starting shutdown_controller")

    ipcon.connect('localhost', 4223)
    time.sleep(1.0)
    master = BrickMaster('5Wr87j', ipcon)
    loop_counter = 0

    while True:
        loop_counter += 1
        if loop_counter > 30000:
            loop_counter = 0

        # Check GPIO
        if not GPIO.input(4):
            presstime = 0
            for i in range(30):
                if not GPIO.input(4):
                    presstime += 1
                else:
                    parent_conn.send("reboot")
                    break
                if presstime > 20:
                    parent_conn.send("shutdown")
                    break
                time.sleep(0.1)

            # wait so that the command really reaches main_controller
            time.sleep(3)

        # Check for stack voltage
        if (loop_counter % 100) == 0:
            stack_voltage = master.get_stack_voltage()/1000.0
            if stack_voltage < 20.0:
                logger.warn("Stack Voltage below 20 V - Stop mower")
                parent_conn.send("undervoltage")

        time.sleep(0.4)
