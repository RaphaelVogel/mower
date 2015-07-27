import time
from collections import deque
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_servo import Servo
from tinkerforge.bricklet_io16 import IO16


def start(main_conn):
    ipcon = IPConnection()
    ipcon.connect('localhost', 4223)

    servo = Servo('6QFwhz', ipcon)
    servo.set_acceleration(0, 50000)  # right wheel
    servo.set_acceleration(1, 50000)  # left wheel
    servo.set_acceleration(2, 30000)  # cutter

    io16 = IO16('b7Y', ipcon)
    io16.set_port_configuration('a', 0b11111111, IO16.DIRECTION_IN, True)  # all pins input with pull-up
    io16.set_edge_count_config(0, IO16.EDGE_TYPE_BOTH, 1)  # set pin 0 for edge count
    io16.set_edge_count_config(1, IO16.EDGE_TYPE_BOTH, 1)  # set pin 1 for edge count

    curr_mode = 'stop'
    curr_value = 0
    rpm_values_right = deque(maxlen=10)
    rpm_values_left = deque(maxlen=10)

    count_rpm = 0
    internal_cmd = None
    while True:
        count_rpm += 1
        if count_rpm > 10000:
            count_rpm = 0

        # Commands: forward/<speed>, backward/<speed>, turnL/, turnR/,
        # curveL/<smooth|medium|strong>, curveR/<smooth|medium|strong>, cutter/<speed>, stop/, terminate/
        if main_conn.poll() or internal_cmd is not None:
            if internal_cmd is not None:
                cmd = internal_cmd
                internal_cmd = None
            else:
                cmd = main_conn.recv()

            split_cmd = cmd.split('/')
            cur_mode = split_cmd[0]
            if cur_mode == 'forward':
                curr_value = int(split_cmd[1])
                rpm_values_right.clear()
                rpm_values_left.clear()
                execute_drive_command(servo, curr_value, curr_value)
            elif cur_mode == 'backward':
                curr_value = int(split_cmd[1])
                rpm_values_right.clear()
                rpm_values_left.clear()
                execute_drive_command(servo, -curr_value, -curr_value)
            elif cur_mode == 'turnL':
                rpm_values_right.clear()
                rpm_values_left.clear()
                curr_value = 3000
                execute_drive_command(servo, curr_value, -curr_value)
            elif cur_mode == 'turnR':
                rpm_values_right.clear()
                rpm_values_left.clear()
                curr_value = 3000
                execute_drive_command(servo, -curr_value, curr_value)
            elif cur_mode == 'curveL':
                rpm_values_left.clear()
                if split_cmd[1] == 'smooth':
                    execute_drive_command(servo, curr_value, curr_value - 400)
                elif split_cmd[1] == 'medium':
                    execute_drive_command(servo, curr_value, curr_value - 700)
                elif split_cmd[1] == 'strong':
                    execute_drive_command(servo, curr_value, curr_value - 1000)
            elif cur_mode == 'curveR':
                rpm_values_right.clear()
                if split_cmd[1] == 'smooth':
                    execute_drive_command(servo, curr_value - 400, curr_value)
                elif split_cmd[1] == 'medium':
                    execute_drive_command(servo, curr_value - 700, curr_value)
                elif split_cmd[1] == 'strong':
                    execute_drive_command(servo, curr_value - 1000, curr_value)
            elif cur_mode == 'cutter':
                execute_cutter_command(servo, int(split_cmd[1]))
            elif cur_mode == 'stop':
                rpm_values_right.clear()
                rpm_values_left.clear()
                execute_drive_command(servo, 0, 0)
            elif cur_mode == 'terminate':
                ipcon.disconnect()
                break

        # check rpm per wheel against moving average to check if wheel is blocked
        if (count_rpm % 4) == 0:
            right_rpm = io16.get_edge_count(0, True)
            left_rpm = io16.get_edge_count(1, True)
            if len(rpm_values_right) > 3:
                moving_average = sum(rpm_values_right) / len(rpm_values_right)
                if moving_average * 0.8 > right_rpm:
                    internal_cmd = 'stop/'
                rpm_values_right.append(right_rpm)
            else:
                rpm_values_right.append(right_rpm)

            if len(rpm_values_left) > 3:
                moving_average = sum(rpm_values_left) / len(rpm_values_left)
                if moving_average * 0.8 > left_rpm:
                    internal_cmd = 'stop/'
                rpm_values_left.append(left_rpm)
            else:
                rpm_values_left.append(left_rpm)

        time.sleep(0.02)


# execute a drive command
def execute_drive_command(servo, right_wheel, left_wheel):
    servo.set_position(0, right_wheel)
    servo.set_position(1, left_wheel)
    servo.enable((1 << 0) | (1 << 1) | (1 << 7))


# execute a cutter command
def execute_cutter_command(servo, cutter_speed):
    servo.set_position(2, cutter_speed)
    servo.enable(2)
