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
internal_cmd = None
g_parent_conn = None
analog_bumper = None


def signal_handler(signal_type, frame):
    if ipcon.get_connection_state() == IPConnection.CONNECTION_STATE_CONNECTED:
        ipcon.disconnect()
    logger.info("Terminate drive_controller")
    sys.exit(0)


# Bumper
def bumper_triggered(voltage):
    global internal_cmd, cur_speed, g_parent_conn
    logger.warn("Bumper triggered, turn mower")
    internal_cmd = 'stop/'
    g_parent_conn.send("bumper_active:" + str(cur_speed))


# pressure can change over time due to environmental changes -> threshold must be adjusted
def adjust_bumper_threshold(voltage):
    global analog_bumper
    analog_bumper.set_voltage_callback_threshold('>', int(voltage * 1.5), 0)


# Fence
def fence_activated():
    global internal_cmd, cur_speed, g_parent_conn
    logger.warn("Fence activated, turn mower")
    internal_cmd = 'stop/'
    g_parent_conn.send("fence_active:" + str(cur_speed))


def start(parent_conn):
    global internal_cmd, g_parent_conn, analog_bumper
    g_parent_conn = parent_conn
    loop_counter = 0
    signal.signal(signal.SIGTERM, signal_handler)

    ipcon.connect('localhost', 4223)
    time.sleep(1.0)
    master = BrickMaster('6QHvJ1', ipcon)
    master.disable_status_led()
    # Motor drivers
    right_wheel = BrickDC('6wUYf6', ipcon)
    right_wheel.set_drive_mode(BrickDC.DRIVE_MODE_DRIVE_COAST)
    right_wheel.set_acceleration(60000)
    right_wheel.set_velocity(0)
    right_wheel.disable_status_led()
    right_wheel.enable()
    left_wheel = BrickDC('62gBJZ', ipcon)
    left_wheel.set_drive_mode(BrickDC.DRIVE_MODE_DRIVE_COAST)
    left_wheel.set_acceleration(60000)
    left_wheel.set_velocity(0)
    left_wheel.disable_status_led()
    left_wheel.enable()
    cutter = BrickDC('6e68bZ', ipcon)
    cutter.set_drive_mode(BrickDC.DRIVE_MODE_DRIVE_COAST)
    cutter.set_acceleration(30000)
    cutter.set_velocity(0)
    cutter.disable_status_led()
    cutter.enable()
    # Bumper
    analog_bumper = BrickletAnalogIn('bK7', ipcon)
    analog_bumper.set_range(BrickletAnalogIn.RANGE_UP_TO_6V)
    current_volt = analog_bumper.get_voltage()
    analog_bumper.register_callback(analog_bumper.CALLBACK_VOLTAGE_REACHED, bumper_triggered)
    analog_bumper.set_voltage_callback_threshold('>', int(current_volt * 1.5), 0)
    analog_bumper.set_debounce_period(5000)
    analog_bumper.register_callback(analog_bumper.CALLBACK_VOLTAGE, adjust_bumper_threshold)
    analog_bumper.set_voltage_callback_period(60000)
    # Fence
    analog_fence = BrickletAnalogInV2('vgY', ipcon)
    analog_fence.register_callback(analog_fence.CALLBACK_VOLTAGE_REACHED, fence_activated)
    analog_fence.set_voltage_callback_threshold("<", 600, 0)
    analog_fence.set_debounce_period(5000)

    while True:
        loop_counter += 1
        if loop_counter > 30000:
            loop_counter = 0

        # commands: forward/<speed>, backward/<speed>, turnL/, turnR/,
        # cutter/<speed>, stop/, reboot_driver/
        if internal_cmd is not None:
            cmd = internal_cmd
            internal_cmd = None
            logger.info("Execute internal command %s" % cmd)
            execute_command(cmd, right_wheel, left_wheel, cutter, master)
        elif g_parent_conn.poll():
            cmd = g_parent_conn.recv()
            logger.info("Execute external command %s" % cmd)
            execute_command(cmd, right_wheel, left_wheel, cutter, master)

        time.sleep(0.01)


def execute_command(cmd, right_wheel, left_wheel, cutter, master):
    global cur_speed
    split_cmd = cmd.split('/')
    cur_mode = split_cmd[0]
    if cur_mode == 'forward':
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
    elif cur_mode == 'reboot_driver':
        master.reset()
