#!/usr/bin/python3
import sys
import logging
from logging.handlers import RotatingFileHandler
from bottle import run, route, static_file
import mmap

# logger configuration
logger = logging.getLogger("mower")
logger.setLevel(logging.ERROR)
filehandler = RotatingFileHandler('./mower/log.txt', maxBytes=100000, backupCount=2)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(filename)s:%(lineno)s  --  %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S')
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)


@route('/')
def index():
    return static_file('index.html', root='./mower/web')


@route('/lib/<filepath:path>')
def serve_static(filepath):
    return static_file(filepath, root='./mower/web/lib')


@route('/drive/<direction>/<speed>')
def evaluate_drive(direction, speed):
    logger.info('Request from UI, direction=%s; speed=%s', direction, speed)
    with open("mower/command.txt", "w") as file:
        cmd = "drive_conn:" + direction + "/" + speed
        file.write(cmd)

    return dict(status="OK")


if __name__ == "__main__":
    f = open("mower/command.txt", 'w').close()

    if len(sys.argv) > 1 and sys.argv[1] == 'devmode':
        run(server='cherrypy', host='localhost', port=8080, debug=True, reloader=True)
    else:
        run(server='cherrypy', host='0.0.0.0', port=8080, debug=False, reloader=False)
