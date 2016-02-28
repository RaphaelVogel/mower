#!/usr/bin/python3
import sys
import logging
from logging.handlers import RotatingFileHandler
from bottle import run, route, static_file
import modules.main_controller as main_controller
import multiprocessing as mp

# logger configuration
logger = logging.getLogger("mower")
logger.setLevel(logging.WARN)
filehandler = RotatingFileHandler('./mower/log.txt', maxBytes=100000, backupCount=2)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
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
    print(direction, speed)
    main_controller_conn.send("drive_conn:" + direction + "/" + speed)
    return dict(status="OK")


if __name__ == "__main__":
    mp.set_start_method('spawn')
    main_controller_conn, main_controller_conn1 = mp.Pipe()
    p_main_controller = mp.Process(target=main_controller.start, args=(main_controller_conn1,), name="Maincontroller Process")
    p_main_controller.daemon = False
    p_main_controller.start()

    if len(sys.argv) > 1 and sys.argv[1] == 'devmode':
        run(server='cherrypy', host='localhost', port=8080, debug=True, reloader=True)
    else:
        run(server='cherrypy', host='0.0.0.0', port=8080, debug=False, reloader=False)
