import math
from datetime import datetime, timedelta
import numpy as np
from sklearn.cluster import DBSCAN

def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a['lat'], a['lon'], b['lat'], b['lon']])
    value = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(min(1, math.sqrt(value)))

def bearing(a, b):
    lat1, lat2 = map(math.radians, [a['lat'], b['lat']])
    delta = math.radians(b['lon']-a['lon'])
    return math.degrees(math.atan2(math.sin(delta)*math.cos(lat2), math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(delta))) % 360

def drift(point, toward, km):
    lat, lon, theta = map(math.radians, [point['lat'], point['lon'], toward])
    arc = km / 6371
    next_lat = math.asin(math.sin(lat)*math.cos(arc)+math.cos(lat)*math.sin(arc)*math.cos(theta))
    next_lon = lon + math.atan2(math.sin(theta)*math.sin(arc)*math.cos(lat), math.cos(arc)-math.sin(lat)*math.sin(next_lat))
    return {'lat': math.degrees(next_lat), 'lon': math.degrees(next_lon)}

def cluster_fires(fires, eps_km=20, min_samples=2):
    if not fires:
        return []
    coords = np.radians([[f['lat'], f['lon']] for f in fires])
    labels = DBSCAN(eps=eps_km/6371, min_samples=min_samples, metric='haversine').fit_predict(coords)
    groups = {}
    for index, (fire, label) in enumerate(zip(fires, labels)):
        # Preserve isolated detections as single-point clusters, marked explicitly.
        groups.setdefault(f'noise-{index}' if label == -1 else str(label), []).append(fire)
    result = []
    for label, members in groups.items():
        result.append({'id': f'cluster-{label}', 'lat': float(np.mean([f['lat'] for f in members])),
            'lon': float(np.mean([f['lon'] for f in members])), 'fire_count': len(members),
            'total_frp': round(sum(f['frp'] for f in members), 2),
            'time': max(f['time'] for f in members), 'mean_detection_confidence': round(float(np.mean([f['confidence_score'] for f in members])), 3),
            'isolated': label.startswith('noise-'), 'source': members[0]['source']})
    return result

def wind_at(point, time, winds):
    candidates = [w for w in winds if abs((datetime.fromisoformat(w['time'])-time).total_seconds()) <= 5400]
    return min(candidates, key=lambda w: distance(point, w)) if candidates else None

def transport_links(clusters, cities, winds, at, direction=None, speed=None):
    links = []
    for cluster in clusters:
        position = {'lat': cluster['lat'], 'lon': cluster['lon']}
        path = [dict(position, hours=0)]
        wind_samples = []
        for hour in range(1, 49):
            sample = wind_at(position, at + timedelta(hours=hour-1), winds)
            if sample is None:
                break
            velocity = sample['speed_kmh'] if speed is None else speed
            from_direction = sample['direction_deg'] if direction is None else direction
            position = drift(position, (from_direction + 180) % 360, velocity)
            path.append(dict(position, hours=hour))
            wind_samples.append((velocity, from_direction))
        for city in cities:
            closest = min(path, key=lambda p: distance(p, city))
            miss_distance = distance(closest, city)
            spread = 15 + 3 * closest['hours']
            arrives = len(path) > 1 and closest['hours'] > 0 and miss_distance <= spread
            score = max(0, 1-miss_distance/max(1, spread*2)) * cluster['mean_detection_confidence'] * min(1, len(wind_samples)/12)
            links.append({'id': f"{cluster['id']}:{city['id']}", 'cluster_id': cluster['id'], 'city_id': city['id'],
                'distance_km': round(distance(cluster, city), 1), 'bearing_deg': round(bearing(cluster, city), 1),
                'travel_hours': closest['hours'] if arrives else None, 'arrival_time': (at+timedelta(hours=closest['hours'])).isoformat() if arrives else None,
                'closest_approach_km': round(miss_distance, 1), 'spread_km': spread,
                'transport_score': round(score, 3), 'score_type': 'alignment and data coverage, not a probability',
                'arrives': arrives, 'path': path, 'fire_count': cluster['fire_count'], 'total_frp': cluster['total_frp'],
                'wind_hours_available': len(wind_samples)})
    return links
