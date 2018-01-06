#!/usr/bin/python3
import sys
from bottle import run, route, static_file
import mmap
from modules.command import State
from modules.command import Command
from modules.command import Controller
import pickle


@route('/')
def index():
    return static_file('index.html', root='/home/pi/mower/web')


@route('/lib/<filepath:path>')
def serve_static(filepath):
    return static_file(filepath, root='/home/pi/mower/web/lib')


# e.g. /drive_controller/forward/3000
@route('/' + Controller.drive.value + '/<state>/<value>')
def drive_controller_command(state, value):
    cmd = Command(Controller.drive, State(state), value)
    with open("/home/pi/mower/command", "r+") as f:
        mm_file = mmap.mmap(f.fileno(), 0)
        mm_file.write(pickle.dumps(cmd))

    return dict(status="Send following command: {}".format(cmd))


if __name__ == "__main__":
    with open("/home/pi/mower/command", "r+") as file:
        mm = mmap.mmap(file.fileno(), 0)
        mm.write(pickle.dumps(None))

    if len(sys.argv) > 1 and sys.argv[1] == 'devmode':
        run(server='cherrypy', host='localhost', port=8080, debug=True, reloader=True)
    else:
        run(server='cherrypy', host='0.0.0.0', port=8080, debug=False, reloader=False)
