#!/usr/bin/python
import sys
import logging
from logging.handlers import RotatingFileHandler
from bottle import run, TEMPLATE_PATH
import web.routes 

# logger configuration
logger = logging.getLogger("dash_logger")
logger.setLevel(logging.WARN)
filehandler = RotatingFileHandler('./dashboard/log.txt', maxBytes=100000, backupCount=3)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)

TEMPLATE_PATH.insert(0, './dashboard/web/views')

if len(sys.argv) > 1 and sys.argv[1] == 'devmode':
    run(server='cherrypy', host='localhost', port=8080, debug=True, reloader=True)
else:
    run(server='cherrypy', host='0.0.0.0', port=8080, debug=False, reloader=False)
