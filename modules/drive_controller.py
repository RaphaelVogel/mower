import time
import signal
import sys
from collections import deque
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_dc import BrickDC
from tinkerforge.brick_master import BrickMaster
from tinkerforge.bricklet_analog_in import BrickletAnalogIn
from tinkerforge.bricklet_analog_in_v2 import BrickletAnalogInV2
import logging

logger = logging.getLogger("mower")
ipcon = IPConnection()

# globals
cur_speed = 0
bumper_active = False
fence_active = False

bumper_values = deque(maxlen=20)  # queue for calculating moving average of bumper values


def signal_handler(signal_type, frame):
    if ipcon.get_connection_state() == IPConnection.CONNECTION_STATE_CONNECTED:
        ipcon.disconnect()
    logger.info("Terminate drive_controller")
    sys.exit(0)


def start(parent_conn):
    loop_counter = 0
    internal_cmd = 'stop/'  # start with 'stop/' to initialize motor driver
    signal.signal(signal.SIGTERM, signal_handler)
    global bumper_active, fence_active

    ipcon.connect('localhost', 4223)
    time.sleep(1.0)
    master = BrickMaster('6QHvJ1', ipcon)
    master.disable_status_led()
    right_wheel = BrickDC('6wUYf6', ipcon)
    right_wheel.set_drive_mode(BrickDC.DRIVE_MODE_DRIVE_COAST)
    right_wheel.set_acceleration(50000)
    right_wheel.set_velocity(0)
    right_wheel.disable_status_led()
    right_wheel.enable()
    left_wheel = BrickDC('62gBJZ', ipcon)
    left_wheel.set_drive_mode(BrickDC.DRIVE_MODE_DRIVE_COAST)
    left_wheel.set_acceleration(50000)
    left_wheel.set_velocity(0)
    left_wheel.disable_status_led()
    left_wheel.enable()
    cutter = BrickDC('6e68bZ', ipcon)
    cutter.set_drive_mode(BrickDC.DRIVE_MODE_DRIVE_COAST)
    cutter.set_acceleration(10000)
    cutter.set_velocity(0)
    cutter.disable_status_led()
    cutter.enable()
    analog_bumper = BrickletAnalogIn('bK7', ipcon)
    analog_bumper.set_range(BrickletAnalogIn.RANGE_UP_TO_6V)
    analog_fence = BrickletAnalogInV2('vgY', ipcon)

    while True:
        loop_counter += 1
        if loop_counter > 30000:
            loop_counter = 0

        # commands: forward/<speed>, backward/<speed>, turnL/, turnR/,
        # cutter/<speed>, stop/, reset_bumper/, reset_fence/, reboot_driver/
        if internal_cmd is not None:
            cmd = internal_cmd
            internal_cmd = None
            logger.info("Execute internal command %s" % cmd)
            execute_command(cmd, right_wheel, left_wheel, cutter, master)
        elif parent_conn.poll():
            cmd = parent_conn.recv()
            logger.info("Execute external command %s" % cmd)
            execute_command(cmd, right_wheel, left_wheel, cutter, master)

        # check bumper
        if not bumper_active and (loop_counter % 4) == 0:
            volt = analog_bumper.get_voltage()
            bumper_values.append(volt)
            moving_average = sum(bumper_values) / len(bumper_values)
            if volt > (moving_average * 1.50):
                logger.warn("Bumper triggered, turn mower")
                internal_cmd = 'stop/'
                bumper_active = True
                parent_conn.send("bumper_active:" + str(cur_speed))

        # check fence
        if not fence_active and ((loop_counter + 2) % 4) == 0:
            volt = analog_fence.get_voltage()
            if volt > 600.0:
                logger.warn("Fence triggered, turn mower. Volt: %s", volt)
                internal_cmd = 'stop/'
                fence_active = True
                parent_conn.send("fence_active:" + str(cur_speed))

        time.sleep(0.01)


def execute_command(cmd, right_wheel, left_wheel, cutter, master):
    global cur_speed, bumper_active, bumper_values, fence_active
    split_cmd = cmd.split('/')
    cur_mode = split_cmd[0]
    if cur_mode == 'forward' and not bumper_active and not fence_active:
        cur_speed = int(split_cmd[1])
        right_wheel.set_velocity(cur_speed)
        left_wheel.set_velocity(cur_speed)
    elif cur_mode == 'backward':
        cur_speed = int(split_cmd[1])
        right_wheel.set_velocity(-cur_speed)
        left_wheel.set_velocity(-cur_speed)
    elif cur_mode == 'turnL':
        right_wheel.set_velocity(30000)
        left_wheel.set_velocity(-30000)
    elif cur_mode == 'turnR':
        right_wheel.set_velocity(-30000)
        left_wheel.set_velocity(30000)
    elif cur_mode == 'cutter':
        cutter_speed = int(split_cmd[1])
        cutter.set_velocity(cutter_speed)
    elif cur_mode == 'stop':
        right_wheel.set_velocity(0)
        left_wheel.set_velocity(0)
    elif cur_mode == 'reset_bumper':
        bumper_active = False
        bumper_values.clear()
    elif cur_mode == 'reset_fence':
        fence_active = False
    elif cur_mode == 'reboot_driver':
        master.reset()
