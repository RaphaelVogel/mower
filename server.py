#!/usr/bin/python3
import sys
from bottle import run, route, static_file
import mmap


@route('/')
def index():
    return static_file('index.html', root='./web')


@route('/lib/<filepath:path>')
def serve_static(filepath):
    return static_file(filepath, root='./web/lib')


@route('/drive/<direction>/<speed>')
def evaluate_drive(direction, speed):
    with open("command.txt", "r+") as file:
        mm = mmap.mmap(file.fileno(), 0)
        cmd = "drive_conn:" + direction + "/" + speed
        mm.write(cmd.encode('utf-8'))

    return dict(status="Send drive command")


@route('/cutter/<speed>')
def evaluate_cutter(speed):
    with open("command.txt", "r+") as file:
        mm = mmap.mmap(file.fileno(), 0)
        cmd = "drive_conn:cutter/" + speed
        mm.write(cmd.encode('utf-8'))

    return dict(status="Send cutter command")


if __name__ == "__main__":
    f = open("command.txt", 'wb')
    f.write(b"                                        ")
    f.close()
    if len(sys.argv) > 1 and sys.argv[1] == 'devmode':
        run(server='cherrypy', host='localhost', port=8080, debug=True, reloader=True)
    else:
        run(server='cherrypy', host='0.0.0.0', port=8080, debug=False, reloader=False)
