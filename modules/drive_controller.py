import time
import signal
import sys
from collections import deque
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_servo import BrickServo
from tinkerforge.bricklet_io16 import BrickletIO16
from tinkerforge.bricklet_industrial_quad_relay import BrickletIndustrialQuadRelay
from tinkerforge.bricklet_analog_in import BrickletAnalogIn
import logging
from threading import Timer

logger = logging.getLogger("mower")
ipcon = IPConnection()

# globals
cur_mode = 'stop'
cur_speed = 0
bumper_active = False
rpm_activated = False

rpm_values_right = deque(maxlen=20)  # queue for calculating moving average of right wheel
rpm_values_left = deque(maxlen=20)  # queue for calculating moving average of left wheel
bumper_values = deque(maxlen=20)  # queue for calculating moving average of bumper values


def signal_handler(signal_type, frame):
    if ipcon.get_connection_state() == IPConnection.CONNECTION_STATE_CONNECTED:
        ipcon.disconnect()
    logger.warn("Terminate drive_controller")
    sys.exit(0)


def start(parent_conn):
    loop_counter = 0
    internal_cmd = 'stop/'  # start with 'stop/' to initialize motor driver
    signal.signal(signal.SIGTERM, signal_handler)
    global rpm_values_right, rpm_values_left, bumper_active, rpm_activated

    ipcon.connect('localhost', 4223)
    time.sleep(0.8)
    servo = BrickServo('6JqqH8', ipcon)
    servo.set_acceleration(2, 30000)  # cutter
    servo.set_velocity(2, 30000)
    io16 = BrickletIO16('b7Y', ipcon)
    io16.set_port_configuration('a', 0b11111111, BrickletIO16.DIRECTION_IN, True)  # all pins input with pull-up
    io16.set_edge_count_config(0, BrickletIO16.EDGE_TYPE_BOTH, 1)  # set pin 0 for edge count
    io16.set_edge_count_config(1, BrickletIO16.EDGE_TYPE_BOTH, 1)  # set pin 1 for edge count
    iqr = BrickletIndustrialQuadRelay('mT2', ipcon)
    iqr.set_monoflop(0b0111, 0b0111, 1500)
    analog = BrickletAnalogIn('bK7', ipcon)
    analog.set_range(BrickletAnalogIn.RANGE_UP_TO_6V)

    while True:
        loop_counter += 1
        if loop_counter > 30000:
            loop_counter = 0

        # commands: forward/<speed>, backward/<speed>, turnL/, turnR/,
        # curveL/<smooth|medium|strong>, curveR/<smooth|medium|strong>, cutter/<speed>, stop/
        # reset_bumper/
        if internal_cmd is not None:
            cmd = internal_cmd
            internal_cmd = None
            logger.info("Execute internal command %s" % cmd)
            execute_command(cmd, servo)
        elif parent_conn.poll():
            cmd = parent_conn.recv()
            logger.info("Execute external command %s" % cmd)
            execute_command(cmd, servo)

        # check rpm per wheel against moving average to check if wheel is blocked
        if (loop_counter % 4) == 0:
            left_rpm = abs(io16.get_edge_count(1, True))
            right_rpm = abs(io16.get_edge_count(0, True))
            rpm_values_right.append(right_rpm)
            rpm_values_left.append(left_rpm)
            if rpm_activated:
                moving_average = sum(rpm_values_right) / len(rpm_values_right)
                if moving_average > 1.0 and right_rpm < (moving_average * 0.80):
                    logger.warn("Right wheel blocked, stop mower. Moving average: %s - Left RPM: %s", moving_average, right_rpm)
                    internal_cmd = 'stop/'

                moving_average = sum(rpm_values_left) / len(rpm_values_left)
                if moving_average > 1.0 and left_rpm < (moving_average * 0.80):
                    logger.warn("Left wheel blocked, stop mower. Moving average: %s - Left RPM: %s", moving_average, left_rpm)
                    internal_cmd = 'stop/'

        # check bumper
        if not bumper_active and ((loop_counter + 2) % 4) == 0:
            volt = analog.get_voltage()
            bumper_values.append(volt)
            moving_average = sum(bumper_values) / len(bumper_values)
            if volt > (moving_average * 1.30):
                logger.warn("Bumper triggered, stop mower")
                internal_cmd = 'stop/'
                bumper_active = True
                parent_conn.send("bumper_active")

        # update drive monoflop
        if (loop_counter % 100) == 0:
            iqr.set_monoflop(0b0111, 0b0111, 1300)

        time.sleep(0.01)


def execute_command(cmd, servo):
    global cur_mode, cur_speed, bumper_active, bumper_values
    split_cmd = cmd.split('/')
    cur_mode = split_cmd[0]
    if cur_mode == 'forward':
        reset_rpm()
        cur_speed = int(split_cmd[1])
        execute_drive_command(servo, cur_speed, cur_speed)
    elif cur_mode == 'backward':
        reset_rpm()
        cur_speed = int(split_cmd[1])
        execute_drive_command(servo, -cur_speed, -cur_speed)
    elif cur_mode == 'turnL':
        reset_rpm()
        cur_speed = 4500
        execute_drive_command(servo, cur_speed, -cur_speed)
    elif cur_mode == 'turnR':
        reset_rpm()
        cur_speed = 4500
        execute_drive_command(servo, -cur_speed, cur_speed)
    elif cur_mode == 'curveL':
        reset_rpm()
        if split_cmd[1] == 'smooth':
            execute_drive_command(servo, cur_speed, cur_speed - 400)
        elif split_cmd[1] == 'medium':
            execute_drive_command(servo, cur_speed, cur_speed - 800)
        elif split_cmd[1] == 'strong':
            execute_drive_command(servo, cur_speed, cur_speed - 1200)
    elif cur_mode == 'curveR':
        reset_rpm()
        if split_cmd[1] == 'smooth':
            execute_drive_command(servo, cur_speed - 400, cur_speed)
        elif split_cmd[1] == 'medium':
            execute_drive_command(servo, cur_speed - 800, cur_speed)
        elif split_cmd[1] == 'strong':
            execute_drive_command(servo, cur_speed - 1200, cur_speed)
    elif cur_mode == 'cutter':
        execute_cutter_command(servo, int(split_cmd[1]))
    elif cur_mode == 'stop':
        reset_rpm()
        execute_drive_command(servo, 0, 0)
    elif cur_mode == 'reset_bumper':
        bumper_active = False
        bumper_values.clear()


# execute a drive command
def execute_drive_command(servo, right_wheel, left_wheel):
    servo.set_position(0, right_wheel)
    servo.set_position(1, left_wheel)
    servo.enable((1 << 0) | (1 << 1) | (1 << 7))


# execute a cutter command
def execute_cutter_command(servo, cutter_speed):
    servo.set_position(2, cutter_speed)
    servo.enable(2)


# activate the wheel rpm
def activate_rpm():
    global rpm_activated, rpm_values_left, rpm_values_right
    rpm_values_right.clear()
    rpm_values_left.clear()
    rpm_activated = True


# Activate rpm checks only after a delay to prevent blocked wheel error messages if directions change
def reset_rpm():
    global rpm_activated
    rpm_activated = False
    t = Timer(1.0, activate_rpm)
    t.start()
