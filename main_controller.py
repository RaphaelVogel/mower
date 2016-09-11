#!/usr/bin/python3
import multiprocessing as mp
import modules.button_controller as button
import modules.drive_controller as drive
import time
import signal
import sys
import logging
from logging.handlers import RotatingFileHandler
import mmap
import random
import subprocess


logger = logging.getLogger("mower")
logger.setLevel(logging.WARN)
filehandler = RotatingFileHandler('/home/pi/mower/main_controller.log', maxBytes=100000, backupCount=2)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(filename)s:%(lineno)s  --  %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S')
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)

left_right = ['turnL/', 'turnR/']


def signal_handler(signal_type, frame):
    logger.info("Terminate main_controller")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    # start button controller
    button_conn, button_conn1 = mp.Pipe()
    p_button = mp.Process(target=button.start, args=(button_conn1,), name="Button Process")
    p_button.daemon = True
    p_button.start()

    # start drive controller
    drive_conn, drive_conn1 = mp.Pipe()
    p_drive = mp.Process(target=drive.start, args=(drive_conn1,), name="Drive Process")
    p_drive.daemon = True
    p_drive.start()

    loop_counter = 0

    while True:
        loop_counter += 1
        if loop_counter > 30000:
            loop_counter = 0

        if (loop_counter % 50) == 0:
            # check for command from web server. Syntax: <connection>:<command> e.g. drive_conn:forward/4000
            with open("/home/pi/mower/command.txt", "r+") as file:
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

        # check for command from button process
        if button_conn.poll():
            cmd = button_conn.recv()
            if cmd == "reboot":
                drive_conn.send("reboot_driver/")
                time.sleep(0.5)
                subprocess.call(["sudo", "reboot"])
            elif cmd == "shutdown":
                drive_conn.send("reboot_driver/")
                time.sleep(0.5)
                subprocess.call(["sudo", "shutdown", "-h", "now"])

        # check for command from drive process
        if drive_conn.poll():
            split_cmd = drive_conn.recv().split(':')
            if split_cmd[0] == "bumper_active" or split_cmd[0] == "fence_active":
                time.sleep(0.8)
                drive_conn.send("backward/30000")
                time.sleep(2.2)
                drive_conn.send("stop/")
                time.sleep(0.8)
                drive_conn.send(random.choice(left_right))
                turn_time = round(random.uniform(1.0, 1.6), 2)
                time.sleep(turn_time)
                drive_conn.send("stop/")
                drive_conn.send("clear_obstacle_phase/")
                time.sleep(2.0)
                drive_conn.send("forward/" + split_cmd[1])

        time.sleep(0.01)

    sys.exit(0)
