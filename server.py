#!/usr/bin/python3
import sys
import time
from bottle import run, route, static_file
import mmap
from tinkerforge.ip_connection import IPConnection
from tinkerforge.brick_master import BrickMaster


@route('/')
def index():
    return static_file('index.html', root='/home/pi/mower/web')


@route('/lib/<filepath:path>')
def serve_static(filepath):
    return static_file(filepath, root='/home/pi/mower/web/lib')


@route('/drive/<direction>/<speed>')
def evaluate_drive(direction, speed):
    with open("/home/pi/mower/command.txt", "r+") as file:
        mm = mmap.mmap(file.fileno(), 0)
        cmd = "drive_conn:" + direction + "/" + speed
        mm.write(cmd.encode('utf-8'))

    return dict(status="Send drive command " + direction + "/" + speed)


@route('/cutter/<speed>')
def evaluate_cutter(speed):
    with open("/home/pi/mower/command.txt", "r+") as file:
        mm = mmap.mmap(file.fileno(), 0)
        cmd = "drive_conn:cutter/" + speed
        mm.write(cmd.encode('utf-8'))

    return dict(status="Send cutter command cutter/" + speed)


@route('/master/getVoltage')
def get_voltage():
    stack_voltage = master.get_stack_voltage() / 1000.0
    return dict(stack_voltage=str(stack_voltage))


if __name__ == "__main__":
    f = open("/home/pi/mower/command.txt", 'wb')
    f.write(b"                                        ")
    f.close()
    ipcon = IPConnection()
    ipcon.connect('localhost', 4223)
    time.sleep(1.0)
    master = BrickMaster('6QHvJ1', ipcon)

    if len(sys.argv) > 1 and sys.argv[1] == 'devmode':
        run(server='cherrypy', host='localhost', port=8080, debug=True, reloader=True)
    else:
        run(server='cherrypy', host='0.0.0.0', port=8080, debug=False, reloader=False)
