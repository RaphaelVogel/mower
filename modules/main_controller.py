import multiprocessing as mp
#import modules.shutdown_controller as shutdown
import modules.drive_controller as drive
import time
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_master import BrickMaster
import sys
import logging
import subprocess


logger = logging.getLogger("mower")


def signal_handler(signal_type, frame):
    logger.info("Terminate main_controller")
    sys.exit(0)


def start(parent_conn):
    # start shutdown controller
    #shutdown_conn, shutdown_conn1 = mp.Pipe()
    #p_shutdown = mp.Process(target=shutdown.start, args=(shutdown_conn1,), name="Shutdown Process")
    #p_shutdown.daemon = False
    #p_shutdown.start()

    # start drive controller
    drive_conn, drive_conn1 = mp.Pipe()
    p_drive = mp.Process(target=drive.start, args=(drive_conn1,), name="Drive Process")
    p_drive.daemon = False
    p_drive.start()

    ipcon = IPConnection()
    ipcon.connect('localhost', 4223)
    time.sleep(0.5)
    master = BrickMaster('5Wr87j', ipcon)
    time.sleep(8)

    while True:
        # check for command from web server. Syntax: <connection>:<command> e.g. drive_conn:forward/4000
        if parent_conn.poll():
            connection = parent_conn.recv().split(':')[0]
            command = parent_conn.recv().split(':')[1]
            logger.info("Call from webserver, connection=%s; command=%s", connection, command)
            if connection == "drive_conn":
                drive_conn.send(command)
            else:
                logger.warn("Wrong command from webserver", parent_conn.recv(), "does not exist")


        # check for command from shutdown process
        #if shutdown_conn.poll():
        #    master.reset()
        #    cmd = shutdown_conn.recv()
        #    if cmd == "reboot":
        #        subprocess.call(["sudo", "reboot"])
        #    elif cmd == "shutdown":
        #        subprocess.call(["sudo", "shutdown", "-h", "now"])
        #    break

        # check for command from drive process
        if drive_conn.poll():
            cmd = drive_conn.recv()
            if cmd == "bumper_active":
                time.sleep(0.6)
                drive_conn.send("backward/3500")
                time.sleep(2.5)
                drive_conn.send("stop/")
                time.sleep(0.6)
                drive_conn.send("turnL/")
                drive_conn.send("reset_bumper/")
                time.sleep(2.5)
                drive_conn.send("stop/")
                time.sleep(0.6)
                drive_conn.send("forward/3500")

        time.sleep(0.01)

    sys.exit(0)