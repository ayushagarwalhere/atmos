import math
import random
from datetime import datetime, timedelta, timezone
from .config import CITIES
from .storage import connect, put, records

def seed_demo():
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    existing = records('aqi', 'demo')
    if existing and existing[-1]['time'] == end.isoformat():
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
    for hour in range(-24*60, 49):
        time = (end+timedelta(hours=hour)).isoformat()
        activity = 8 + 6*math.sin(hour/90)
        for point in points:
            winds.append({'id': f"demo:{point['id']}:{time}", 'city_id': point['id'], 'time': time, 'lat': point['lat'], 'lon': point['lon'],
                'speed_kmh': 16+5*math.sin(hour/24), 'direction_deg': 310+12*math.sin(hour/40), 'boundary_layer_height': 500+250*math.sin(hour/12)**2,
                'issued_at': (end+timedelta(hours=min(hour, 0))).isoformat(), 'historical': hour <= 0, 'source': source})
        if hour > 0:
            continue
        for index, city in enumerate(CITIES):
            pm25 = max(8, 55+index*8 + 1.7*activity + 9*math.sin((hour-6)/24) + randomizer.gauss(0, 2))
            readings.append({'id': f"demo:{city['id']}:{time}", 'city_id': city['id'], 'station_id': f"demo-{city['id']}",
                'time': time, 'pm25': round(pm25, 2), 'lat': city['lat'], 'lon': city['lon'], 'source': source})
        if hour % 3 == 0:
            for index in range(max(2, int(activity))):
                lat, lon = (30.3, 75.5) if index % 2 == 0 else (29.7, 76.5)
                fires.append({'id': f'demo:{time}:{index}', 'time': time, 'lat': lat+randomizer.uniform(-.05,.05), 'lon': lon+randomizer.uniform(-.05,.05),
                    'confidence': 'n', 'confidence_score': .65, 'frp': round(randomizer.uniform(3,14), 2), 'source': source})
    with connect() as db:
        for table in ('fires', 'wind', 'aqi', 'stations', 'facilities', 'predictions', 'model_runs', 'alerts'):
            db.execute(f'DELETE FROM {table} WHERE mode=?', ('demo',))
    for table, rows in [('fires',fires),('wind',winds),('aqi',readings),('stations',stations),('facilities',facilities)]:
        put(table, rows, 'demo')
