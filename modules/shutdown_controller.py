#import RPi.GPIO as GPIO
import sys
import signal
import time
import logging

#GPIO.setmode(GPIO.BCM)
#GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # GPIO4 is Board pin 7

logger = logging.getLogger("mower_logger")


def signal_handler(signal_type, frame):
    #GPIO.cleanup()
    logger.info("Terminate shutdown_controller")
    sys.exit(0)


def start(parent_conn):
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Starting shutdown_controller")
    while True:
        time.sleep(80)
        parent_conn.send("shutdown")


