import time
from tinkerforge.ip_connection import IPConnection
ipcon = IPConnection()

DRIVE_STATE = 'stop'
WHEEL_LEFT, WHEEL_RIGHT = 0, 0  # -9000 to +9000


# Starts the main drive loop
def start(main_conn):
    global DRIVE_STATE
    while True:
        # check command comming from the main process
        if main_conn.poll():
            evaluate_drive_command(main_conn.recv())

        # check rpm per wheel and adjust individual wheel speed based on DRIVE_STATE


        time.sleep(0.05)


# check the drive commands comming from the main process
# Possible commands:
# stop, forward/<speed_left_wheel>,<speed_right_wheel>, backward/<speed_left>,<speed_right>
def evaluate_drive_command(cmd):
    global DRIVE_STATE, WHEEL_LEFT, WHEEL_RIGHT
    if cmd == 'stop':
        DRIVE_STATE = 'stop'
        WHEEL_LEFT = 0
        WHEEL_RIGHT = 0
    else:
        split_cmd = cmd.split('/')
        DRIVE_STATE = split_cmd[0]
        left_wheel, right_wheel = split_cmd[1].split(',')
        WHEEL_LEFT = int(left_wheel)
        WHEEL_RIGHT = int(right_wheel)
