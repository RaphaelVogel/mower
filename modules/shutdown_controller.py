import RPi.GPIO as GPIO
import sys
import signal
import time
import logging

GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # GPIO4 is Board pin 7

logger = logging.getLogger("mower")


def signal_handler(signal_type, frame):
    GPIO.cleanup()
    logger.info("Terminate shutdown_controller")
    sys.exit(0)


def start(parent_conn):
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Starting shutdown_controller")
    while True:
        if not GPIO.input(4):
            presstime = 0
            for i in range(30):
                if not GPIO.input(4):
                    presstime += 1
                else:
                    parent_conn.send("reboot")
                    break
                if presstime > 15:
                    parent_conn.send("shutdown")
                    break
                time.sleep(0.1)

            # wait so that the command really reaches main_controller
            time.sleep(3)

        time.sleep(0.5)
