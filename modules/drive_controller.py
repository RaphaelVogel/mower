import time
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_servo import Servo
from tinkerforge.bricklet_io16 import IO16


def start(main_conn):
    ipcon = IPConnection()
    ipcon.connect('localhost', 4223)

    servo = Servo('6QFwhz', ipcon)
    servo.set_acceleration(0, 50000)    # right wheel
    servo.set_acceleration(1, 50000)    # left wheel
    servo.set_acceleration(2, 30000)    # cutter

    io16 = IO16('b7Y', ipcon)
    io16.set_port_configuration('a', 0b11111111, IO16.DIRECTION_IN, True)     # all pins input with pull-up
    io16.set_edge_count_config(0, IO16.EDGE_TYPE_BOTH, 1)          # set pin 0 for edge count
    io16.set_edge_count_config(1, IO16.EDGE_TYPE_BOTH, 1)          # set pin 1 for edge count
    count = 0
    command = None
    while True:
        count += 1
        if count > 100000:
            count = 0
        # check drive command comming from main process.
        # Commands: drive/<right_wheel>,<left_wheel>   cutter/<speed>  terminate
        if main_conn.poll() or command is not None:
            if command is not None:
                cmd = command.split('/')
                command = None
            else:
                cmd = main_conn.recv().split('/')
            if cmd[0] == 'drive':
                speeds = cmd[1].split(',')
                right_wheel = int(speeds[0])
                left_wheel = int(speeds[1])
                execute_drive_command(servo, right_wheel, left_wheel)
            elif cmd[0] == 'cutter':
                execute_cutter_command(servo, int(cmd[1]))
            elif cmd[0] == 'terminate':
                ipcon.disconnect()
                break

        # check rpm per wheel and adjust individual wheel speed based on DRIVE_STATE
        if (count % 3) == 0:
            right_rpm = io16.get_edge_count(0, True)
            left_rpm = io16.get_edge_count(1, True)
            if abs(left_rpm - right_rpm) > 12:
                command = "drive/0,0"

        time.sleep(0.04)


# execute a drive command
def execute_drive_command(servo, right_wheel, left_wheel):
    servo.set_position(0, right_wheel)
    servo.set_position(1, left_wheel)
    servo.enable((1 << 0) | (1 << 1) | (1 << 7))


# execute a cutter command
def execute_cutter_command(servo, cutter_speed):
    servo.set_position(2, cutter_speed)
    servo.enable(2)
