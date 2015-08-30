import time
import sys
from collections import deque
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_servo import Servo
from tinkerforge.bricklet_io16 import IO16
from tinkerforge.bricklet_industrial_quad_relay import BrickletIndustrialQuadRelay

ipcon = IPConnection()

cur_mode = 'stop'
cur_speed = 0

rpm_values_right = deque(maxlen=10)  # queue for calculating moving average
rpm_values_left = deque(maxlen=10)  # queue for calculating moving average

loop_counter = 0
internal_cmd = None


def start(main_conn):
    global loop_counter, internal_cmd, rpm_values_right, rpm_values_left
    ipcon.connect('localhost', 4223)
    time.sleep(2)
    servo = Servo('6QFwhz', ipcon)
    servo.set_acceleration(0, 50000)  # right wheel
    servo.set_acceleration(1, 50000)  # left wheel
    servo.set_acceleration(2, 30000)  # cutter
    io16 = IO16('b7Y', ipcon)
    io16.set_port_configuration('a', 0b11111111, IO16.DIRECTION_IN, True)  # all pins input with pull-up
    io16.set_edge_count_config(0, IO16.EDGE_TYPE_BOTH, 1)  # set pin 0 for edge count
    io16.set_edge_count_config(1, IO16.EDGE_TYPE_BOTH, 1)  # set pin 1 for edge count
    iqr = BrickletIndustrialQuadRelay('mT2', ipcon)
    iqr.set_monoflop(0b0111, 0b0111, 1500)

    while True:
        loop_counter += 1
        if loop_counter > 10000:
            loop_counter = 0

        # Commands: forward/<speed>, backward/<speed>, turnL/, turnR/,
        # curveL/<smooth|medium|strong>, curveR/<smooth|medium|strong>, cutter/<speed>, stop/, terminate/
        if main_conn.poll():
            cmd = main_conn.recv()
            execute_command(cmd, servo)
        elif internal_cmd is not None:
            cmd = internal_cmd
            internal_cmd = None
            execute_command(cmd, servo)

        # check rpm per wheel against moving average to check if wheel is blocked every 100ms
        if (loop_counter % 5) == 0:
            right_rpm = io16.get_edge_count(0, True)
            left_rpm = io16.get_edge_count(1, True)
            rpm_values_right.append(right_rpm)
            rpm_values_left.append(left_rpm)

            if len(rpm_values_right) > 3:
                moving_average = sum(rpm_values_right) / len(rpm_values_right)
                if right_rpm < (moving_average * 0.40):
                    internal_cmd = 'stop/'

            if len(rpm_values_left) > 3:
                moving_average = sum(rpm_values_left) / len(rpm_values_left)
                if left_rpm < (moving_average * 0.40):
                    internal_cmd = 'stop/'

        # update drive monoflop every second
        if (loop_counter % 50) == 0:
            iqr.set_monoflop(0b0111, 0b0111, 1500)

        time.sleep(0.02)


def execute_command(cmd, servo):
    global cur_mode, cur_speed
    split_cmd = cmd.split('/')
    cur_mode = split_cmd[0]
    if cur_mode == 'forward':
        cur_speed = int(split_cmd[1])
        reset_queues('both')
        execute_drive_command(servo, cur_speed, cur_speed)
    elif cur_mode == 'backward':
        cur_speed = int(split_cmd[1])
        reset_queues('both')
        execute_drive_command(servo, -cur_speed, -cur_speed)
    elif cur_mode == 'turnL':
        reset_queues('both')
        cur_speed = 3000
        execute_drive_command(servo, cur_speed, -cur_speed)
    elif cur_mode == 'turnR':
        reset_queues('both')
        cur_speed = 3000
        execute_drive_command(servo, -cur_speed, cur_speed)
    elif cur_mode == 'curveL':
        reset_queues('left')
        if split_cmd[1] == 'smooth':
            execute_drive_command(servo, cur_speed, cur_speed - 400)
        elif split_cmd[1] == 'medium':
            execute_drive_command(servo, cur_speed, cur_speed - 700)
        elif split_cmd[1] == 'strong':
            execute_drive_command(servo, cur_speed, cur_speed - 1100)
    elif cur_mode == 'curveR':
        reset_queues('right')
        if split_cmd[1] == 'smooth':
            execute_drive_command(servo, cur_speed - 400, cur_speed)
        elif split_cmd[1] == 'medium':
            execute_drive_command(servo, cur_speed - 700, cur_speed)
        elif split_cmd[1] == 'strong':
            execute_drive_command(servo, cur_speed - 1100, cur_speed)
    elif cur_mode == 'cutter':
        execute_cutter_command(servo, int(split_cmd[1]))
    elif cur_mode == 'stop':
        reset_queues('both')
        execute_drive_command(servo, 0, 0)
    elif cur_mode == 'terminate':
        ipcon.disconnect()
        sys.exit(0)


# execute a drive command
def execute_drive_command(servo, right_wheel, left_wheel):
    servo.set_position(0, right_wheel)
    servo.set_position(1, left_wheel)
    servo.enable((1 << 0) | (1 << 1) | (1 << 7))


# execute a cutter command
def execute_cutter_command(servo, cutter_speed):
    servo.set_position(2, cutter_speed)
    servo.enable(2)


def reset_queues(name):
    global rpm_values_right, rpm_values_left
    if name == 'right':
        rpm_values_right.clear()
    elif name == 'left':
        rpm_values_left.clear()
    elif name == 'both':
        rpm_values_right.clear()
        rpm_values_left.clear()
