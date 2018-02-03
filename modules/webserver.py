import sys
from bottle import run, route, static_file
from modules.command import State
from modules.command import Command
from modules.command import Controller


g_main_controller_connection = None


@route('/')
def index():
    return static_file('index.html', root='/home/pi/mower/web')


@route('/lib/<filepath:path>')
def serve_static(filepath):
    return static_file(filepath, root='/home/pi/mower/web/lib')


# e.g. /drive_controller/forward/3000
@route('/' + Controller.drive.value + '/<state>/<value>')
def drive_controller_command(state, value):
    cmd = Command(Controller.drive, State(state), int(value))
    g_main_controller_connection.send(cmd)
    return dict(status="Send command: {}".format(str(cmd)))


def start(main_controller_connection):
    global g_main_controller_connection
    g_main_controller_connection = main_controller_connection
    run(host='0.0.0.0', port=8080, debug=False, reloader=False)
