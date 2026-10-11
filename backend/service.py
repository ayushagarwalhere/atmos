import csv
import io
import math
from datetime import datetime, timedelta, timezone
import numpy as np
from .config import CITIES, LIMITS
from .forecast import hourly_air, predict_city
from .providers import identity, normalize_fires, timestamp
from .storage import records, put, providers, setting, utcnow
from .transport import cluster_fires, transport_links, distance
from .weather import WEATHER_FIELDS, current_weather, interpret_weather

def at_time(raw=None):
    return datetime.fromisoformat(timestamp(raw)) if raw else datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)

def pm25_subindex(mean):
    # CPCB PM2.5 24-hour breakpoints; concentrations rounded to whole µg/m³.
    rounded = int(round(mean))
    for lo,hi,index_lo,index_hi in [(0,30,0,50),(31,60,51,100),(61,90,101,200),(91,120,201,300),(121,250,301,400),(251,500,401,500)]:
        if lo<=rounded<=hi:
            return round(index_lo+(index_hi-index_lo)*(rounded-lo)/(hi-lo))
    return 500 if rounded>500 else None

def snapshot(mode='live', at=None, horizon=6, direction=None, speed=None, multiplier=1, persist=False, smoke_factor=1, burning='unspecified', **weather):
    moment = at_time(at)
    air = hourly_air(mode)
    fires = records('fires',mode,start=(moment-timedelta(hours=24)).isoformat(),end=moment.isoformat())
    winds = records('wind',mode,start=(moment-timedelta(hours=1)).isoformat(),end=(moment+timedelta(hours=48)).isoformat())
    clusters = sorted(cluster_fires(fires),key=lambda c:c['total_frp'],reverse=True)
    total_clusters = len(clusters)
    clusters = clusters[:80]
    if multiplier == 0:
        clusters = []
    for cluster in clusters:
        cluster['fire_count'] = round(cluster['fire_count']*multiplier)
        cluster['total_frp'] = round(cluster['total_frp']*multiplier,2)
    links = transport_links(clusters,CITIES,winds,moment,direction,speed) if smoke_factor > 0 else []
    cities, predictions = [], []
    for city in CITIES:
        prediction = predict_city(city,moment,mode,horizon,direction,speed,multiplier,(air,fires,winds),smoke_factor,**weather)
        if burning != 'unspecified':
            prediction.update(scenario=True,interval_valid_for_scenario=False)
        changed = direction is not None or speed is not None or multiplier != 1 or smoke_factor != 1 or any(value is not None for value in weather.values())
        baseline = predict_city(city,moment,mode,horizon,context=(air,fires,winds)) if changed else prediction
        meteo = current_weather(city['id'],moment,winds,dict(weather,direction=direction,speed=speed))
        incoming = [edge for edge in links if edge['city_id']==city['id'] and edge['arrives']]
        samples = [value for (name,time),value in air.items() if name==city['id'] and moment-timedelta(hours=24)<time<=moment]
        recent = [(time,value) for (name,time),value in air.items() if name==city['id'] and time<=moment]
        latest = max(recent) if recent else None
        city_stations = records('stations',mode,city_id=city['id'])
        outlook = dict(city, observed_pm25=round(latest[1],2) if latest else None,
            observed_at=latest[0].isoformat() if latest else None,
            air_stale=bool(latest and (moment-latest[0]).total_seconds()>10800),
            pm25_subindex=pm25_subindex(float(np.mean(samples))) if len(samples)>=16 else None,
            subindex_label='24h PM2.5-only Indian sub-index, not overall AQI', valid_hours_24h=len(samples),
            history=[{'time':time.isoformat(),'pm25':value} for (name,time),value in sorted(air.items(),key=lambda item:item[0][1]) if name==city['id'] and moment-timedelta(hours=48)<time<=moment],
            stations=sorted(city_stations,key=lambda station:station.get('distance_km',0)), forecast=prediction,
            baseline_forecast=baseline, weather=meteo, environment=interpret_weather(meteo,multiplier,smoke_factor,burning),
            scenario_difference=round(prediction['pm25']-baseline['pm25'],2) if prediction['pm25'] is not None and baseline['pm25'] is not None else None,
            arrival_hours=min((edge['travel_hours'] for edge in incoming),default=None),
            transport_score=max((edge['transport_score'] for edge in incoming),default=None), source_clusters=[edge['cluster_id'] for edge in incoming])
        cities.append(outlook)
        if persist and prediction['pm25'] is not None:
            predictions.append(dict(prediction,id=identity(city['id'],moment.isoformat(),horizon),time=moment.isoformat(),source='model forecast'))
    if predictions:
        put('predictions',predictions,mode)
    return {'mode':mode,'time':moment.isoformat(),'horizon':horizon,'cities':cities,'clusters':clusters,'edges':links,
        'fires_count':len(fires),'total_frp':round(sum(f['frp'] for f in fires)*multiplier,2),'providers':providers(),'limits':LIMITS,
        'clusters_truncated':total_clusters>80, 'transport_method':'hourly nearest-grid 10 m wind drift; 15 km initial spread + 3 km/hour',
        'scenario':{'wind_direction':direction,'wind_speed':speed,'fire_multiplier':multiplier,'smoke_factor':smoke_factor,'burning':burning,**weather},
        'data_note':'All records and metrics in this mode are synthetic.' if mode=='demo' else 'Real imported/provider records only; missing feeds stay missing.'}

def impact(snapshot_data, city_id):
    city = next(city for city in snapshot_data['cities'] if city['id']==city_id)
    facilities = records('facilities',snapshot_data['mode'],city_id=city_id)
    edges = [edge for edge in snapshot_data['edges'] if edge['city_id']==city_id and edge['arrives']]
    affected = []
    for facility in facilities:
        matched = any(any(point['hours']<=24 and distance(point,facility)<=15+3*point['hours'] for point in edge['path']) for edge in edges)
        if matched:
            affected.append(facility)
    supplied_population = [f['population'] for f in affected if f.get('population') is not None]
    return {'city_id':city_id,'schools':sum(f['kind']=='school' for f in affected),'hospitals':sum(f['kind']=='hospital' for f in affected),
        'districts':sum(f['kind']=='district' for f in affected), 'population':sum(supplied_population) if supplied_population else None,
        'inventory_count':len(facilities),'potentially_affected_count':len(affected),'facilities':affected[:100],
        'forecast':city['forecast'],'coverage':'Synthetic example inventory' if snapshot_data['mode']=='demo' else ('OSM/imported inventory; incomplete' if facilities else 'No inventory loaded. Fetch OSM or import facilities.'),
        'method':'Facility/district centre intersects a rough 24h drift corridor. Counts indicate potential exposure, not measured population exposure.'}

def advisory(city, audience, mode):
    prefix = 'Synthetic demonstration. ' if mode=='demo' else ''
    forecast = city['forecast']
    if forecast['pm25'] is None:
        return prefix+'A usable forecast is unavailable. Check the latest official station readings before making decisions.'
    interval = forecast.get('interval')
    uncertainty = f"Empirical interval: {interval[0]}–{interval[1]} µg/m³." if interval else 'Prediction uncertainty cannot be quantified with the available history.'
    tasks = {'principal':'Review outdoor schedules against current official local advisories; verify the station readings before changing activities.',
        'parent':'Check current official station readings and school communications when planning outdoor activities.',
        'official':'Compare station trends and source-data freshness; review local official response procedures before issuing notices.'}
    return prefix+f"{city['name']}: {forecast['model']} estimates PM2.5 {forecast['pm25']} µg/m³ in {forecast['horizon']} hours. {uncertainty} "+tasks[audience]+' This screening estimate does not establish how much pollution comes from crop fires.'

def import_csv(kind, text, mode='live', source='User CSV import'):
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or len(rows)>100000:
        raise ValueError('CSV must contain 1–100,000 rows')
    if kind=='fires':
        normalized = normalize_fires(rows,source)
    else:
        normalized = []
        for row in rows:
            if row.get('city_id') not in {c['id'] for c in CITIES}:
                raise ValueError('city_id must be delhi, chandigarh, ludhiana or lucknow')
            time = timestamp(row['time'])
            city = next(c for c in CITIES if c['id']==row['city_id'])
            base = {'id':row.get('id') or identity(kind,row['city_id'],row.get('station_id',''),time,row.get('name','')),
                'city_id':row['city_id'],'time':time,'source':source}
            if kind=='aqi':
                value = float(row['pm25'])
                if not 0<=value<=2000:
                    raise ValueError('PM2.5 must be 0–2000 µg/m³')
                if not row.get('station_id'):
                    raise ValueError('Station readings require station_id')
                base.update(station_id=row['station_id'],pm25=value,lat=float(row.get('lat') or city['lat']),lon=float(row.get('lon') or city['lon']))
            elif kind=='wind':
                speed,direction = float(row['speed_kmh']),float(row['direction_deg'])
                if not 0<=speed<=300 or not 0<=direction<=360:
                    raise ValueError('Invalid wind speed/direction')
                base.update(lat=float(row.get('lat') or city['lat']),lon=float(row.get('lon') or city['lon']),speed_kmh=speed,direction_deg=direction,
                    boundary_layer_height=float(row['boundary_layer_height']) if row.get('boundary_layer_height') else None, historical=True,issued_at=time)
                for name, (_, lo, hi) in WEATHER_FIELDS.items():
                    value = float(row[name]) if row.get(name) else None
                    if value is not None and (not math.isfinite(value) or not lo <= value <= hi):
                        raise ValueError(f'{name} must be {lo}–{hi}')
                    base[name] = value
            elif kind=='facilities':
                if row['kind'] not in ('school','hospital','district'):
                    raise ValueError('Facility kind must be school, hospital or district')
                population = int(row['population']) if row.get('population') else None
                if population is not None and population<0:
                    raise ValueError('Population cannot be negative')
                base.update(name=row['name'],kind=row['kind'],lat=float(row['lat']),lon=float(row['lon']),population=population)
            elif kind=='news':
                url = row.get('url','')
                if not url.startswith('https://'):
                    raise ValueError('News links must use HTTPS')
                base.update(title=row['title'][:500],url=url)
            normalized.append(base)
    put(kind,normalized,mode)
    if kind=='aqi':
        stations = {r['station_id']: {'id':r['station_id'],'city_id':r['city_id'],'name':r['station_id'],'lat':r['lat'],'lon':r['lon'], 'time':utcnow(),'source':source} for r in normalized}
        put('stations',list(stations.values()),mode)
    return {'kind':kind,'mode':mode,'imported_rows':len(normalized),'source':source}

def arrival_backtest(mode='live', days=7):
    air = hourly_air(mode)
    if not air:
        raise ValueError('No station history available for arrival validation')
    end = max(time for _,time in air)
    start = end-timedelta(days=days)
    fires = records('fires',mode,start=(start-timedelta(hours=24)).isoformat(),end=end.isoformat())
    winds = records('wind',mode,start=start.isoformat(),end=end.isoformat())
    cases = []
    for offset in range(days*2):
        at = start+timedelta(hours=12*offset)
        clusters = cluster_fires([f for f in fires if at-timedelta(hours=24)<datetime.fromisoformat(f['time'])<=at])[:30]
        window = [w for w in winds if at<=datetime.fromisoformat(w['time'])<=at+timedelta(hours=24)]
        edges = transport_links(clusters,CITIES,window,at)
        for city in CITIES:
            incoming = [edge for edge in edges if edge['city_id']==city['id'] and edge['arrives'] and edge['travel_hours']<=18]
            arrival_hours = min((edge['travel_hours'] for edge in incoming),default=6)
            baseline = air.get((city['id'],at))
            samples = [(hour,air.get((city['id'],at+timedelta(hours=hour)))) for hour in range(max(1,arrival_hours-3),min(24,arrival_hours+3)+1)]
            valid = [(hour,value) for hour,value in samples if value is not None]
            if baseline is None or len(valid)<3:
                continue
            rises = [(hour,value) for hour,value in valid if value-baseline>=10]
            predicted = bool(incoming)
            observed = bool(rises)
            cases.append({'city_id':city['id'],'time':at.isoformat(),'predicted_arrival_hours':arrival_hours if predicted else None,
                'observed_rise_hours':min((hour for hour,_ in rises),default=None),'max_rise_pm25':round(max(value-baseline for _,value in valid),2),
                'outcome':'hit' if predicted and observed else 'miss' if predicted else 'false_negative' if observed else 'correct_negative'})
    positives = [case for case in cases if case['predicted_arrival_hours'] is not None]
    report = {'id':f'arrival:{mode}:{utcnow()}','time':utcnow(),'source':'arrival association backtest','report_type':'arrival','demo_only':mode=='demo',
        'days':days,'cases':cases,'scored_cases':len(cases),'predicted_events':len(positives),
        'hit_rate':sum(case['outcome']=='hit' for case in positives)/len(positives) if positives else None,
        'misses':sum(case['outcome']=='miss' for case in cases),'false_negatives':sum(case['outcome']=='false_negative' for case in cases),
        'method':'12h issue times; first estimated arrival ≤18h; PM2.5 rise ≥10 µg/m³ within ±3h; minimum three station hours. Association only, no causal attribution.'}
    put('model_runs',[report],mode)
    return report
