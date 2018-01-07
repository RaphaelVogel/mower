from enum import Enum


class State(Enum):
    start = "start"
    stop = "stop"
    forward = "forward"
    backward = "backward"
    turn_left = "turn_left"
    turn_right = "turn_right"
    deviate_left = "deviate_left"
    deviate_right = "deviate_right"
    cutter = "cutter"
    reboot_system = "reboot_system"
    shutdown_system = "shutdown_system"


class Controller(Enum):
    drive = "drive_controller"
    main = "main_controller"
    gpio = "gpio_controller"


class Command:
    def __init__(self, controller, state, value=None):
        if controller in Controller:
            self.controller = controller
        else:
            raise Exception('Controller {} not supported'.format(controller))

        if state in State:
            self.state = state
        else:
            raise Exception('State {} not supported'.format(state))

        self.value = value if value is not None else None

    def __str__(self):
        return "Controller: {}, State: {}, Value: {}".format(self.controller, self.state, self.value)
