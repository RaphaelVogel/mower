#!/usr/bin/python3
import multiprocessing as mp
import modules.shutdown_controller as shutdown
import modules.drive_controller as drive
import time
import signal
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_master import BrickMaster
import sys
import logging
from logging.handlers import RotatingFileHandler
import mmap
import random
import subprocess


logger = logging.getLogger("mower")
logger.setLevel(logging.WARN)
filehandler = RotatingFileHandler('./mower/log.txt', maxBytes=100000, backupCount=2)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(filename)s:%(lineno)s  --  %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S')
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)

left_right = ['turnL/', 'turnR/']


def signal_handler(signal_type, frame):
    if ipcon.get_connection_state() == IPConnection.CONNECTION_STATE_CONNECTED:
        ipcon.disconnect()
    logger.warn("Terminate main_controller")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    # start shutdown controller
    shutdown_conn, shutdown_conn1 = mp.Pipe()
    p_shutdown = mp.Process(target=shutdown.start, args=(shutdown_conn1,), name="Shutdown Process")
    p_shutdown.daemon = True
    p_shutdown.start()

    # start drive controller
    drive_conn, drive_conn1 = mp.Pipe()
    p_drive = mp.Process(target=drive.start, args=(drive_conn1,), name="Drive Process")
    p_drive.daemon = True
    p_drive.start()

    ipcon = IPConnection()
    ipcon.connect('localhost', 4223)
    time.sleep(0.5)
    master = BrickMaster('5Wr87j', ipcon)
    time.sleep(5)
    loop_counter = 0

    while True:
        loop_counter += 1
        if loop_counter > 30000:
            loop_counter = 0

        if (loop_counter % 50) == 0:
            # check for command from web server. Syntax: <connection>:<command> e.g. drive_conn:forward/4000
            with open("mower/command.txt", "r+") as file:
                mm = mmap.mmap(file.fileno(), 0)
                web_command = mm.readline().decode('utf-8').strip()
                if web_command:
                    mm.seek(0)
                    mm.write(b"                                        ")
                    command_split = web_command.split(':')
                    connection = command_split[0]
                    command = command_split[1]
                    logger.info("Call from webserver, connection=%s; command=%s", connection, command)
                    if connection == "drive_conn":
                        drive_conn.send(command)
                    else:
                        logger.error("Wrong command from webserver", web_command, "does not exist")

        # check for command from shutdown process
        if shutdown_conn.poll():
            master.reset()
            cmd = shutdown_conn.recv()
            if cmd == "reboot":
                subprocess.call(["sudo", "reboot"])
            elif cmd == "shutdown":
                subprocess.call(["sudo", "shutdown", "-h", "now"])
            break

        # check for command from drive process
        if drive_conn.poll():
            split_cmd = drive_conn.recv().split(':')
            if split_cmd[0] == "bumper_active":
                time.sleep(0.6)
                drive_conn.send("backward/4500")
                time.sleep(2.5)
                drive_conn.send("stop/")
                time.sleep(0.6)
                drive_conn.send(random.choice(left_right))
                drive_conn.send("reset_bumper/")
                turn_time = round(random.uniform(1.8, 3.5), 2)
                time.sleep(turn_time)
                drive_conn.send("stop/")
                time.sleep(0.6)
                drive_conn.send("forward/" + split_cmd[1])

        time.sleep(0.01)

    sys.exit(0)
