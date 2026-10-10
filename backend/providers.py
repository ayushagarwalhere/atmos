import csv
import hashlib
import io
import os
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import httpx
from .config import CITIES
from .storage import put, provider_status, utcnow
from .transport import distance

def timestamp(value):
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamps must include an explicit UTC offset')
    return dt.astimezone(timezone.utc).isoformat(timespec='seconds')

def identity(*parts):
    return hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:24]

def request_json(url, params=None, headers=None):
    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

def firms_refresh():
    key = os.getenv('FIRMS_MAP_KEY')
    if not key:
        provider_status('NASA FIRMS', 'missing_key', 'Set FIRMS_MAP_KEY or import a FIRMS CSV. No detections available is not evidence of no fires.')
        return
    url = f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/73.5,28,77.5,32.7/3'
    with httpx.Client(timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(response.text)))
    normalized = normalize_fires(rows, 'NASA FIRMS VIIRS SNPP NRT')
    put('fires', normalized, 'live')
    provider_status('NASA FIRMS', 'ok', '3-day regional bounding box; VIIRS detections, not verified stubble fires', len(normalized))

def normalize_fires(rows, source):
    normalized = []
    for row in rows:
        lat, lon = float(row.get('latitude', row.get('lat'))), float(row.get('longitude', row.get('lon')))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('Invalid fire coordinates')
        if not (28 <= lat <= 32.7 and 73.5 <= lon <= 77.5):
            continue
        time = row.get('time') or f"{row['acq_date']}T{str(row['acq_time']).zfill(4)[:2]}:{str(row['acq_time']).zfill(4)[2:]}:00+00:00"
        time = timestamp(time)
        confidence = str(row.get('confidence', 'n')).lower()
        score = {'l': .35, 'n': .65, 'h': .9}.get(confidence)
        if score is None:
            score = min(1, max(0, float(confidence)/100))
        frp = float(row.get('frp', 0))
        if frp < 0:
            raise ValueError('FRP cannot be negative')
        normalized.append({'id': identity(lat, lon, time, row.get('satellite', 'SNPP')), 'lat': lat, 'lon': lon,
            'time': time, 'confidence': confidence, 'confidence_score': score, 'frp': frp, 'source': source})
    return normalized

def weather_refresh(start=None, end=None):
    points = CITIES + [{'id': 'punjab', 'lat': 30.7, 'lon': 75.6}, {'id': 'haryana', 'lat': 29.7, 'lon': 76.5}]
    params = {'latitude': ','.join(str(p['lat']) for p in points), 'longitude': ','.join(str(p['lon']) for p in points),
        'hourly': 'wind_speed_10m,wind_direction_10m,boundary_layer_height', 'timezone': 'UTC', 'wind_speed_unit': 'kmh'}
    if start:
        url = 'https://archive-api.open-meteo.com/v1/archive'
        params.update(start_date=start, end_date=end)
        # ERA5 boundary-layer height is not universally available in this endpoint.
        params['hourly'] = 'wind_speed_10m,wind_direction_10m'
    else:
        url = 'https://api.open-meteo.com/v1/forecast'
        params.update(past_days=2, forecast_days=3)
    responses = request_json(url, params)
    responses = responses if isinstance(responses, list) else [responses]
    rows = []
    issued = utcnow()
    for point, data in zip(points, responses):
        hourly = data['hourly']
        for index, raw_time in enumerate(hourly['time']):
            speed, direction = hourly['wind_speed_10m'][index], hourly['wind_direction_10m'][index]
            if speed is None or direction is None:
                continue
            time = timestamp(raw_time + '+00:00')
            blh = hourly.get('boundary_layer_height', [None]*len(hourly['time']))[index]
            rows.append({'id': identity(point['id'], time), 'city_id': point['id'], 'lat': point['lat'], 'lon': point['lon'],
                'time': time, 'speed_kmh': float(speed), 'direction_deg': float(direction), 'boundary_layer_height': blh,
                'issued_at': issued, 'historical': bool(start), 'source': 'Open-Meteo ERA5' if start else 'Open-Meteo forecast'})
    put('wind', rows, 'live')
    provider_status('Open-Meteo', 'ok', '10 m wind is a simplified transport input; historical archives are retrospective hindcasts', len(rows))

def paginated(url, params, headers, maximum=40):
    rows = []
    for page in range(1, maximum+1):
        data = request_json(url, dict(params, page=page, limit=1000), headers)
        batch = data.get('results', [])
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
    raise ValueError('Pagination limit exceeded; narrow the date range to avoid incomplete history')

def openaq_refresh(start=None, end=None):
    key = os.getenv('OPENAQ_API_KEY')
    if not key:
        provider_status('OpenAQ', 'missing_key', 'Set OPENAQ_API_KEY or import station-level PM2.5 CSV. Historical coverage is unverified without a key.')
        return
    headers = {'X-API-Key': key}
    stations, readings = [], []
    start = start or (datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
    end = end or utcnow()
    for city in CITIES:
        locations = paginated('https://api.openaq.org/v3/locations', {'coordinates': f"{city['lat']},{city['lon']}", 'radius': 25000}, headers)
        for location in locations:
            coords = location.get('coordinates') or {}
            if coords.get('latitude') is None:
                continue
            point = {'lat': coords['latitude'], 'lon': coords['longitude']}
            for sensor in location.get('sensors', []):
                parameter = sensor.get('parameter', {})
                if parameter.get('name') != 'pm25' or parameter.get('units') not in ('µg/m³', 'ug/m3', 'μg/m³'):
                    continue
                sensor_id = sensor['id']
                station = {'id': str(sensor_id), 'city_id': city['id'], 'time': utcnow(), 'name': location['name'], **point,
                    'distance_km': round(distance(point, city), 2), 'source': 'OpenAQ station PM2.5', 'provider': location.get('provider', {}).get('name')}
                stations.append(station)
                for reading in paginated(f'https://api.openaq.org/v3/sensors/{sensor_id}/hours', {'date_from': start, 'date_to': end}, headers):
                    value = reading.get('value')
                    if value is None or value < 0:
                        continue
                    period = reading.get('period', {})
                    raw_time = (period.get('datetimeFrom') or reading.get('datetime') or {}).get('utc')
                    if not raw_time:
                        continue
                    time = timestamp(raw_time)
                    readings.append({'id': identity(sensor_id, time), 'city_id': city['id'], 'station_id': str(sensor_id),
                        'time': time, 'pm25': float(value), 'lat': point['lat'], 'lon': point['lon'], 'source': 'OpenAQ station PM2.5'})
    put('stations', stations, 'live')
    put('aqi', readings, 'live')
    provider_status('OpenAQ', 'ok' if readings else 'no_coverage', 'Hourly PM2.5 from nearest stations within 25 km; coverage differs by city/date', len(readings))

def facilities_refresh(city_id):
    city = next(c for c in CITIES if c['id'] == city_id)
    query = f"[out:json][timeout:25];nwr(around:20000,{city['lat']},{city['lon']})[amenity~\"^(school|hospital)$\"];out center tags;"
    with httpx.Client(timeout=40) as client:
        response = client.post('https://overpass-api.de/api/interpreter', data={'data': query})
        response.raise_for_status()
        data = response.json()
    rows = []
    for item in data.get('elements', []):
        point = item.get('center', item)
        if 'lat' not in point or 'lon' not in point:
            continue
        tags = item.get('tags', {})
        rows.append({'id': f"osm:{item['type']}:{item['id']}", 'city_id': city_id, 'time': utcnow(), 'lat': point['lat'], 'lon': point['lon'],
            'kind': tags['amenity'], 'name': tags.get('name', 'Unnamed facility'), 'population': None, 'source': 'OpenStreetMap / Overpass'})
    put('facilities', rows, 'live')
    provider_status(f'Facilities {city_id}', 'ok', 'OSM amenities within 20 km; incomplete inventory, population unknown', len(rows))
    return len(rows)

def news_refresh():
    # Official PIB RSS; headlines are evidence, never agent instructions.
    with httpx.Client(timeout=30,follow_redirects=True) as client:
        response = client.get('https://www.pib.gov.in/RssMain.aspx',params={'ModId':6,'Lang':1,'Regid':1})
        response.raise_for_status()
        document = ET.fromstring(response.content)
    rows = []
    for item in document.findall('.//item')[:200]:
        title = item.findtext('title','')
        if not any(word in title.lower() for word in ('stubble','air quality','crop residue','pollution','farm fire')):
            continue
        link = item.findtext('link','')
        if not link.startswith('https://'):
            continue
        published = item.findtext('pubDate','')
        try:
            time = parsedate_to_datetime(published).astimezone(timezone.utc).isoformat(timespec='seconds')
        except ValueError:
            time = utcnow()
        for city in CITIES:
            rows.append({'id':identity(link,city['id']),'city_id':city['id'],'time':time,'source':'Press Information Bureau RSS','title':title[:500],'url':link})
    put('news',rows,'live')
    provider_status('PIB news','ok','Official RSS headlines filtered for air quality/crop fires; an empty feed does not imply no relevant news',len(rows))

def guarded(name, fn):
    try:
        fn()
    except httpx.HTTPStatusError as exc:
        provider_status(name, 'error', f'Provider returned HTTP {exc.response.status_code}; existing records retained')
    except Exception as exc:
        # Do not echo request URLs: the FIRMS key is a path segment.
        provider_status(name, 'error', f'{type(exc).__name__}; existing records retained. Check provider coverage/configuration.')

def refresh():
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(guarded, name, fn) for name, fn in [('NASA FIRMS', firms_refresh), ('Open-Meteo', weather_refresh), ('OpenAQ', openaq_refresh), ('PIB news',news_refresh)]]
        for job in jobs:
            job.result()
