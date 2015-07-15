import time
from tinkerforge.ip_connection import IPConnection
ipcon = IPConnection()


def start(main_conn):
    while True:
        time.sleep(0.05)