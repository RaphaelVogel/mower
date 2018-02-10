import signal
import sys
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_dc import BrickDC
from modules.command import State
import logging
import time


logger = logging.getLogger("mower")
ipcon = IPConnection()

g_right_wheel_speed = 0
g_left_wheel_speed = 0
g_cutter_speed = 0


def signal_handler(signal_type, frame):
    if ipcon.get_connection_state() == IPConnection.CONNECTION_STATE_CONNECTED:
        ipcon.disconnect()
    logger.info("Terminate drive_controller")
    sys.exit(0)


def start(main_controller_connection):
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Starting drive_controller")

    # Motor drivers
    ipcon.connect('localhost', 4223)
    time.sleep(1.0)
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
    cutter.set_acceleration(10000)
    cutter.set_velocity(0)
    cutter.disable_status_led()
    cutter.enable()

    while True:
        if main_controller_connection.poll():
            cmd = main_controller_connection.recv()
            logger.info("Execute external command {}".format(str(cmd)))
            execute_command(cmd, right_wheel, left_wheel, cutter)

        time.sleep(0.01)


def execute_command(cmd, right_wheel, left_wheel, cutter):
    global g_right_wheel_speed, g_left_wheel_speed, g_cutter_speed

    if cmd.state is State.forward:
        right_wheel.set_velocity(cmd.value)
        left_wheel.set_velocity(cmd.value)
        g_right_wheel_speed, g_left_wheel_speed = cmd.value, cmd.value

    elif cmd.state is State.stop:
        right_wheel.set_velocity(0)
        left_wheel.set_velocity(0)
        time.sleep(0.8)  # prevent fast thrust reversal
        g_right_wheel_speed, g_left_wheel_speed = 0, 0

    elif cmd.state is State.backward:
        right_wheel.set_velocity(-cmd.value)
        left_wheel.set_velocity(-cmd.value)
        g_right_wheel_speed, g_left_wheel_speed = -cmd.value, -cmd.value

    elif cmd.state is State.turn_left:
        right_wheel.set_velocity(30000)
        left_wheel.set_velocity(-30000)
        g_right_wheel_speed, g_left_wheel_speed = 30000, -30000

    elif cmd.state is State.turn_right:
        right_wheel.set_velocity(-30000)
        left_wheel.set_velocity(30000)
        g_right_wheel_speed, g_left_wheel_speed = -30000, 30000

    elif cmd.state is State.correct_heading:
        slowdown_factor_left, slowdown_factor_right = cmd.value
        speed_right = g_right_wheel_speed * slowdown_factor_right
        speed_left = g_left_wheel_speed * slowdown_factor_left
        right_wheel.set_velocity(int(speed_right))
        left_wheel.set_velocity(int(speed_left))
        g_right_wheel_speed, g_left_wheel_speed = int(speed_right), int(speed_left)

    elif cmd.state is State.cutter:
        cutter.set_velocity(cmd.value)
        g_cutter_speed = cmd.value

