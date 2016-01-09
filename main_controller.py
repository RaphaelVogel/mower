import multiprocessing as mp
#import modules.shutdown_controller as shutdown
import modules.drive_controller as drive
import time
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_master import BrickMaster
import sys
import logging
from logging.handlers import RotatingFileHandler
import subprocess


logger = logging.getLogger("mower_logger")
logger.setLevel(logging.INFO)
filehandler = RotatingFileHandler('./log.txt', maxBytes=100000, backupCount=2)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)


if __name__ == "__main__":
    # start shutdown controller
    #shutdown_conn, shutdown_conn1 = mp.Pipe()
    #p_shutdown = mp.Process(target=shutdown.start, args=(shutdown_conn1,), name="Shutdown Process")
    #p_shutdown.daemon = True
    #p_shutdown.start()

    # start drive controller
    drive_conn, drive_conn1 = mp.Pipe()
    p_drive = mp.Process(target=drive.start, args=(drive_conn1,), name="Drive Process")
    p_drive.daemon = True
    p_drive.start()

    ipcon = IPConnection()
    ipcon.connect('localhost', 4223)
    time.sleep(0.5)
    master = BrickMaster('5Wr87j', ipcon)

    time.sleep(8)
    drive_conn.send("forward/3500")

    while True:
        #if shutdown_conn.poll():
        #    master.reset()
        #    cmd = shutdown_conn.recv()
        #    if cmd == "reboot":
        #        subprocess.call("sudo reboot", shell=True)
        #    elif cmd == "shutdown":
        #        subprocess.call("sudo shutdown -h now", shell=True)
        #    break

        if drive_conn.poll():
            cmd = drive_conn.recv()
            if cmd == "bumper_active":
                time.sleep(0.5)
                drive_conn.send("backward/3500")
                time.sleep(3)
                drive_conn.send("stop/")
                time.sleep(0.5)
                drive_conn.send("turnL/")
                time.sleep(0.1)
                drive_conn.send("reset_bumper/")
                time.sleep(3)
                drive_conn.send("stop/")
                time.sleep(0.5)
                drive_conn.send("forward/3500")

        time.sleep(0.01)

    sys.exit(0)
