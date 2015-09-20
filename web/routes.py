from bottle import route, static_file, request, HTTPResponse
from access_modules import solar, solar_db, weather, weather_db, zwave, alarm
import multiprocessing as mp

fake = False
p_alarm = None
alarm_conn = None
alarm_conn1 = None


@route('/')
def index():
    return static_file('index.html', root='./ha2/web')


@route('/haui/<filepath:path>')
def serve_static(filepath):
    return static_file(filepath, root='./ha2/web/haui')


@route('/ui5lib/<filepath:path>')
def serve_static(filepath):
    return static_file(filepath, root='./ha2/web/ui5lib')


@route('/pages/<filepath:path>')
def serve_static(filepath):
    return static_file(filepath, root='./ha2/web/pages')


# Solar inverter API
# -------------------------------------------------------------------
@route('/solar/current')
def current_solarproduction():
    current_data = solar.read_data(fake) # returns a dictionary, will be transformed to JSON by bottle
    if current_data:
        return current_data
    else:
        return HTTPResponse(dict(error="Could not read solar production values"), status=500)


@route('/solar/historicProduction')
def historic_production():
    year = request.query.year
    month = request.query.month
    historic_data = solar_db.read_data(year, month)
    if historic_data:
        return historic_data
    else:
        return HTTPResponse(dict(error="Could not read solar production values from DB"), status=500)


# Weather data API
# -------------------------------------------------------------------
@route('/weather/current')
def current_weather():
    current_data = weather.read_data(fake)
    if current_data:
        return current_data
    else:
        return HTTPResponse(dict(error="Could not read weather data values"), status=500)


@route('/weather/historicTemperatures')
def historic_temperatures():
    year = request.query.year
    month = request.query.month
    day = request.query.day
    historic_data = weather_db.read_temperature(year, month, day)
    if historic_data:
        return historic_data
    else:
        return HTTPResponse(dict(error="Could not read temperature values form DB"), status=500)


@route('/weather/historicHumidities')
def historic_humidities():
    year = request.query.year
    month = request.query.month
    day = request.query.day
    historic_data = weather_db.read_humidity(year, month, day)
    if historic_data:
        return historic_data
    else:
        return HTTPResponse(dict(error="Could not read humiditiy values form DB"), status=500)


@route('/weather/historicPressures')
def historic_pressures():
    year = request.query.year
    month = request.query.month
    day = request.query.day
    historic_data = weather_db.read_pressure(year, month, day)
    if historic_data:
        return historic_data
    else:
        return HTTPResponse(dict(error="Could not read pressure values form DB"), status=500)


# Zwave API
# --------------------------------------------------------------------
@route('/zwave/status')
def zwave_complete_status():
    zwave_status = zwave.read_devices_status(fake)
    if zwave_status:
        return zwave_status
    else:
        return HTTPResponse(dict(error="Could not read zwave status"), status=500)


@route('/zwave/livingroomLight/<status>')
def zwave_livingroom_light(status):
    light_status = zwave.set_livingroom_light(status, fake)
    if light_status:
        return light_status
    else:
        return HTTPResponse(dict(error="Could not switch livingroom light"), status=500)


# Alarm API
# ----------------------------------------------------------------------
@route('/alarm/<status>')
def alarm_status(status):
    global p_alarm, alarm_conn, alarm_conn1
    if status == "ON" and p_alarm is None:
        ctx = mp.get_context('spawn')
        alarm_conn, alarm_conn1 = ctx.Pipe()
        p_alarm = ctx.Process(target=alarm.start, args=(alarm_conn1,))
        p_alarm.daemon = True
        p_alarm.start()
        return HTTPResponse(dict(msg="Started Alarm"), status=200)
    elif status == "OFF" and p_alarm is not None:
        alarm_conn.send("TERMINATE")
        p_alarm = None
        return HTTPResponse(dict(msg="Stopped Alarm"), status=200)
    else:
        return HTTPResponse(dict(msg="Alarm status not changed"), status=200)
