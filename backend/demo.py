import math
import random
from datetime import datetime, timedelta, timezone
from .config import CITIES
from .storage import connect, put, records, setting, set_setting

def seed_demo():
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    existing = records('aqi', 'demo')
    if existing and existing[-1]['time'] == end.isoformat() and setting('demo_weather_version') == 2:
        return
    randomizer = random.Random(41)
    fires, winds, readings, stations, facilities = [], [], [], [], []
    source = 'Synthetic reproducible demo; not observations'
    for city in CITIES:
        stations.append(dict(city, id=f"demo-{city['id']}", city_id=city['id'], time=end.isoformat(), source=source))
        for index, kind in enumerate(['school', 'school', 'hospital']):
            facilities.append({'id': f"demo:{city['id']}:{index}", 'city_id': city['id'], 'time': end.isoformat(),
                'lat': city['lat']+.03*index, 'lon': city['lon']-.025*index, 'kind': kind, 'name': f'Demo {kind} {index+1}', 'population': None, 'source': source})
    points = CITIES + [{'id': 'punjab', 'lat': 30.7, 'lon': 75.6}, {'id': 'haryana', 'lat': 29.7, 'lon': 76.5}]
    def weather(hour):
        # Deliberately synthetic relationships for exploring the software, not atmospheric calibration.
        return {'rain_mm': round(max(0, 7*math.sin(hour/19)-3),2),
            'cloud_cover_pct': round(50+40*math.sin(hour/31),1),
            'humidity_pct': round(60+25*math.sin(hour/27),1),
            'temperature_c': round(25+7*math.sin(hour/12),1)}
    for hour in range(-24*60, 49):
        time = (end+timedelta(hours=hour)).isoformat()
        activity = 8 + 6*math.sin(hour/90)
        for point in points:
            winds.append({'id': f"demo:{point['id']}:{time}", 'city_id': point['id'], 'time': time, 'lat': point['lat'], 'lon': point['lon'],
                'speed_kmh': 16+5*math.sin(hour/24), 'direction_deg': 310+12*math.sin(hour/40), 'boundary_layer_height': 500+250*math.sin(hour/12)**2,
                **weather(hour),
                'issued_at': (end+timedelta(hours=min(hour, 0))).isoformat(), 'historical': hour <= 0, 'source': source})
        if hour > 0:
            continue
        for index, city in enumerate(CITIES):
            meteo = weather(hour)
            pm25 = max(8, 65+index*8 + 2.5*activity - 1.4*(16+5*math.sin(hour/24))
                - 5*meteo['rain_mm'] + .18*meteo['cloud_cover_pct'] + .08*(meteo['humidity_pct']-60)
                + 9*math.sin((hour-6)/24) + randomizer.gauss(0, 2))
            readings.append({'id': f"demo:{city['id']}:{time}", 'city_id': city['id'], 'station_id': f"demo-{city['id']}",
                'time': time, 'pm25': round(pm25, 2), 'lat': city['lat'], 'lon': city['lon'], 'source': source})
        if hour % 3 == 0:
            for index in range(max(2, int(activity))):
                lat, lon = (30.3, 75.5) if index % 2 == 0 else (29.7, 76.5)
                fires.append({'id': f'demo:{time}:{index}', 'time': time, 'lat': lat+randomizer.uniform(-.05,.05), 'lon': lon+randomizer.uniform(-.05,.05),
                    'confidence': 'n', 'confidence_score': .65, 'frp': round(randomizer.uniform(3,14), 2), 'source': source})
    with connect() as db:
        for table in ('fires', 'wind', 'aqi', 'stations', 'facilities', 'predictions', 'alerts'):
            db.execute(f'DELETE FROM {table} WHERE mode=?', ('demo',))
    for table, rows in [('fires',fires),('wind',winds),('aqi',readings),('stations',stations),('facilities',facilities)]:
        put(table, rows, 'demo')
    set_setting('demo_weather_version',2)
