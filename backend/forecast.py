import math
from datetime import datetime, timedelta
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .config import CITIES, DATA_DIR
from .storage import put, records, utcnow
from .transport import bearing, distance

FEATURES = ['recent_pm25', 'pm25_lag_3h', 'pm25_lag_12h', 'upwind_fire_count', 'upwind_frp', 'travel_hours',
    'wind_speed_kmh', 'wind_sin', 'wind_cos', 'boundary_layer_height', 'hour_sin', 'hour_cos', 'weekday']

def hourly_air(mode):
    rows = records('aqi', mode)
    if not rows:
        return {}
    frame = pd.DataFrame(rows)
    frame['hour'] = pd.to_datetime(frame.time, utc=True).dt.floor('h')
    # Equal station weighting: collapse duplicate readings before taking the city median.
    per_station = frame.groupby(['city_id', 'station_id', 'hour']).pm25.mean()
    return {(city, time.to_pydatetime()): float(value) for (city, time), value in per_station.groupby(['city_id', 'hour']).median().items()}

def feature_row(city, at, air, fires, winds, direction=None, speed=None, multiplier=1):
    recent = [(time, value) for (name,time),value in air.items() if name == city['id'] and time <= at and time >= at-timedelta(hours=3)]
    if not recent:
        return None
    recent_time, pm25 = max(recent)
    candidates = [w for w in winds if w.get('city_id') == city['id'] and abs((datetime.fromisoformat(w['time'])-at).total_seconds()) < 3601]
    if not candidates:
        return None
    wind = min(candidates, key=lambda w: abs((datetime.fromisoformat(w['time'])-at).total_seconds()))
    speed = wind['speed_kmh'] if speed is None else speed
    direction = wind['direction_deg'] if direction is None else direction
    toward = (direction+180)%360
    upwind_count, upwind_frp, travel_sum, weights = 0., 0., 0., 0.
    for fire in fires:
        time = datetime.fromisoformat(fire['time'])
        if not at-timedelta(hours=24) < time <= at:
            continue
        angular = math.radians(bearing(fire,city)-toward)
        alignment = max(0, math.cos(angular))**6
        dist = distance(fire,city)
        weight = alignment*math.exp(-dist/500)*fire['confidence_score']
        upwind_count += weight*multiplier
        upwind_frp += weight*fire['frp']*multiplier
        travel_sum += weight*min(72, dist/max(1,speed))
        weights += weight
    features = [pm25, air.get((city['id'], at-timedelta(hours=3)), pm25), air.get((city['id'], at-timedelta(hours=12)), pm25),
        upwind_count, upwind_frp, travel_sum/weights if weights else 0, speed,
        math.sin(math.radians(direction)), math.cos(math.radians(direction)), wind.get('boundary_layer_height'),
        math.sin(2*math.pi*at.hour/24), math.cos(2*math.pi*at.hour/24), at.weekday()]
    return {'values': [float(v) if v is not None else np.nan for v in features], 'observed_at': recent_time.isoformat(),
        'wind_source': wind['source'], 'scenario_out_of_distribution': direction is not None and multiplier != 1}

def training_rows(mode, horizon):
    air = hourly_air(mode)
    fires, winds = records('fires',mode), records('wind',mode)
    rows = []
    # Index winds/fires into bounded windows to avoid repeated whole-history scans.
    wind_index = {}
    fire_index = {}
    for row in winds:
        wind_index.setdefault((row.get('city_id'),datetime.fromisoformat(row['time'])), []).append(row)
    for row in fires:
        hour = datetime.fromisoformat(row['time']).replace(minute=0,second=0,microsecond=0)
        fire_index.setdefault(hour, []).append(row)
    for city in CITIES:
        for (name, time), pm in sorted(air.items(), key=lambda item: item[0][1]):
            if name != city['id'] or (name,time+timedelta(hours=horizon)) not in air:
                continue
            if any((name,time-timedelta(hours=lag)) not in air for lag in (3,12)):
                continue
            fire_window = [f for lag in range(24) for f in fire_index.get(time-timedelta(hours=lag), [])]
            wind_window = [w for offset in (-1,0,1) for w in wind_index.get((name,time+timedelta(hours=offset)), [])]
            # Never use future wind in a training feature.
            wind_window = [w for w in wind_window if datetime.fromisoformat(w['time']) <= time]
            feature = feature_row(city,time,air,fire_window,wind_window)
            if feature:
                rows.append({'time':time,'city_id':name,'x':feature['values'],'y':air[(name,time+timedelta(hours=horizon))]})
    return rows

def metrics(actual, predicted):
    return {'mae': round(float(mean_absolute_error(actual,predicted)),3), 'rmse': round(float(math.sqrt(mean_squared_error(actual,predicted))),3)}

def artifact_path(mode, horizon):
    return DATA_DIR / f'model-{mode}-{horizon}h.joblib'

def train(mode='live', horizon=6, allow_demo=False):
    if mode == 'demo' and not allow_demo:
        raise ValueError('Synthetic data cannot validate a real model. Explicitly enable demo training for a pipeline check.')
    rows = training_rows(mode,horizon)
    times = sorted(set(r['time'] for r in rows))
    if len(rows)<240 or len(times)<24*14:
        raise ValueError(f'Need at least 14 days of matched fire/wind/PM2.5 history and 240 supervised rows; found {len(times)} hours and {len(rows)} rows.')
    cuts = [times[int(len(times)*fraction)] for fraction in (.5,.7,.85)]
    blocks = [
        [r for r in rows if r['time']+timedelta(hours=horizon)<cuts[0]],
        [r for r in rows if cuts[0]<=r['time'] and r['time']+timedelta(hours=horizon)<cuts[1]],
        [r for r in rows if cuts[1]<=r['time'] and r['time']+timedelta(hours=horizon)<cuts[2]],
        [r for r in rows if r['time']>=cuts[2]],
    ]
    if min(map(len,blocks))<30:
        raise ValueError('Insufficient rows after chronological splits and horizon purge; import more history.')
    arrays = [(np.array([r['x'] for r in block]),np.array([r['y'] for r in block])) for block in blocks]
    x_train,y_train = arrays[0]
    x_select,y_select = arrays[1]
    x_cal,y_cal = arrays[2]
    x_test,y_test = arrays[3]
    candidates = {'linear': make_pipeline(SimpleImputer(keep_empty_features=True),StandardScaler(),Ridge(alpha=10))}
    unavailable = []
    try:
        from xgboost import XGBRegressor
        candidates['xgboost'] = make_pipeline(SimpleImputer(keep_empty_features=True),XGBRegressor(n_estimators=100,max_depth=3,learning_rate=.06,n_jobs=2,random_state=41))
    except ImportError:
        unavailable.append('xgboost')
    try:
        from lightgbm import LGBMRegressor
        candidates['lightgbm'] = make_pipeline(SimpleImputer(keep_empty_features=True),LGBMRegressor(n_estimators=100,max_depth=4,num_leaves=15,learning_rate=.06,n_jobs=2,random_state=41,verbosity=-1))
    except ImportError:
        unavailable.append('lightgbm')
    comparison = {'persistence': {'selection':metrics(y_select,x_select[:,0]),'test':metrics(y_test,x_test[:,0])}}
    failures = []
    for name, model in list(candidates.items()):
        try:
            model.fit(x_train,y_train)
            comparison[name] = {'selection':metrics(y_select,model.predict(x_select)), 'test':metrics(y_test,model.predict(x_test))}
        except Exception as exc:
            failures.append({'model':name,'error':type(exc).__name__})
            candidates.pop(name)
    best = min(comparison, key=lambda name: comparison[name]['selection']['mae'])
    # Test block is reported only. Selection must not use test performance.
    improvement = 1-comparison[best]['selection']['mae']/max(.001,comparison['persistence']['selection']['mae'])
    selected = best if improvement >= .05 else 'persistence'
    model = candidates.get(selected)
    predict = lambda x: np.maximum(0, model.predict(x) if model is not None else x[:,0])
    residuals = np.abs(y_cal-predict(x_cal))
    level = min(1, math.ceil((len(residuals)+1)*.9)/len(residuals))
    radius = float(np.quantile(residuals,level,method='higher'))
    test_pred = predict(x_test)
    coverage = float(np.mean((y_test>=np.maximum(0,test_pred-radius)) & (y_test<=test_pred+radius)))
    report = {'id':f'model:{mode}:{horizon}:{utcnow()}', 'time':utcnow(),'source':'chronological evaluation','mode':mode,'horizon':horizon,
        'selected_model':selected,'comparison':comparison,'selection_improvement':round(improvement,3), 'unavailable':unavailable,'failures':failures,
        'interval':{'method':'split conformal, 90% nominal; temporal dependence may reduce coverage','radius':round(radius,3),'test_coverage':round(coverage,3), 'calibration_rows':len(y_cal)},
        'split':{'method':'50% train / 20% model selection / 15% calibration / 15% test; horizon purged at boundaries',
            'boundaries':[t.isoformat() for t in cuts], 'rows':[len(b) for b in blocks]},
        'training_end': max(r['time'] for r in blocks[0]).isoformat(),
        'validated_for_live':mode=='live' and selected!='persistence' and comparison[selected]['test']['mae']<comparison['persistence']['test']['mae'] and coverage>=.8,
        'demo_only':mode=='demo', 'features':FEATURES,
        'limitations':['Weather archive features are retrospective hindcasts, not an operational forecast-vintage backtest.',
            'Fire availability/quality may be incomplete. Source counts do not prove causality.', 'Intervals are empirical; distribution shifts and correlated city samples reduce reliability.']}
    joblib.dump({'model':model,'report':report,'radius':radius,'background':x_train[:100]}, artifact_path(mode,horizon))
    put('model_runs',[report],mode)
    return report

def persistence_interval(air, city_id, at, horizon):
    differences = [abs(air[(name,time+timedelta(hours=horizon))]-value) for (name,time),value in air.items()
        if name==city_id and time+timedelta(hours=horizon)<=at and time>=at-timedelta(days=30) and (name,time+timedelta(hours=horizon)) in air]
    return float(np.quantile(differences,.9)) if len(differences)>=30 else None

def predict_city(city, at, mode, horizon=6, direction=None, speed=None, multiplier=1, context=None):
    air, fires, winds = context or (hourly_air(mode),records('fires',mode),records('wind',mode))
    feature = feature_row(city,at,air,fires,winds,direction,speed,multiplier)
    latest = [(time,value) for (name,time),value in air.items() if name==city['id'] and time<=at]
    if not latest:
        return {'city_id':city['id'],'pm25':None,'interval':None,'model':'unavailable','reason':'No station PM2.5 readings available','explanations':[]}
    observed_time, observed = max(latest)
    stale = (at-observed_time).total_seconds()>3*3600
    if stale:
        return {'city_id':city['id'],'pm25':None,'interval':None,'model':'unavailable','reason':'Latest station reading is more than 3 hours old','observed_at':observed_time.isoformat(),'explanations':[]}
    path = artifact_path(mode,horizon)
    artifact = joblib.load(path) if path.exists() else None
    if artifact and datetime.fromisoformat(artifact['report']['training_end'])>at:
        artifact = None
    model = artifact['model'] if artifact and feature else None
    value = float(max(0, model.predict(np.array([feature['values']]))[0])) if model is not None else observed
    radius = artifact['radius'] if artifact and feature else persistence_interval(air,city['id'],at,horizon)
    report = artifact['report'] if artifact and feature else None
    explanations = []
    if model is not None and report['selected_model'] in ('xgboost','lightgbm'):
        try:
            import shap
            transformed = model.steps[0][1].transform(np.array([feature['values']]))
            values = shap.TreeExplainer(model.steps[-1][1]).shap_values(transformed)[0]
            explanations = [{'feature':FEATURES[index], 'contribution_pm25':round(float(values[index]),3)} for index in np.argsort(np.abs(values))[::-1][:5]]
        except Exception:
            explanations = [{'feature':'SHAP unavailable for this artifact','contribution_pm25':None}]
    elif model is not None:
        transformed = model[:-1].transform(np.array([feature['values']]))[0]
        coefficients = transformed*model.steps[-1][1].coef_
        explanations = [{'feature':FEATURES[index], 'contribution_pm25':round(float(coefficients[index]),3), 'method':'linear standardized contribution'} for index in np.argsort(abs(coefficients))[::-1][:5]]
    else:
        explanations = [{'feature':'Persistence uses the latest station PM2.5. Fire scenarios change transport, but PM2.5 response requires a trained model.', 'contribution_pm25':None}]
    scenario = direction is not None or speed is not None or multiplier != 1
    return {'city_id':city['id'],'pm25':round(value,2),'baseline_pm25':round(observed,2),'delta_pm25':round(value-observed,2),
        'interval':[round(max(0,value-radius),2),round(value+radius,2)] if radius is not None else None,
        'nominal_coverage':.9 if radius is not None else None,'empirical_test_coverage':report['interval']['test_coverage'] if report else None,
        'model':report['selected_model'] if report else 'persistence','model_validated':bool(report and report['validated_for_live']),
        'reason':None if model is not None else ('Wind unavailable; persistence fallback' if feature is None else 'No trained model beats the selection baseline; persistence used'),
        'observed_at':observed_time.isoformat(),'target_time':(at+timedelta(hours=horizon)).isoformat(),'horizon':horizon,'explanations':explanations,
        'scenario':scenario,'interval_valid_for_scenario':not scenario,'feature_values':dict(zip(FEATURES,[None if np.isnan(v) else round(v,3) for v in feature['values']])) if feature else {}}
