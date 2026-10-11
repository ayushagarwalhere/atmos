"""Reproducible what-if runs and explicitly synthetic demo responses."""
import json
import math
import uuid
from .storage import connect, utcnow


def demo_response(baseline, alternative, weather, horizon):
    """An illustrative recipe, never used for live observations or calibration."""
    if baseline.get('pm25') is None:
        return alternative
    observed, effective = weather['observed'], weather['effective']
    base_features = baseline.get('feature_values', {})
    changed_features = alternative.get('feature_values', {})
    base_frp = base_features.get('upwind_frp') or 0
    changed_frp = changed_features.get('upwind_frp') or 0
    contributions = {'upwind_frp': 12 * (changed_frp - base_frp) / (abs(base_frp) + 25)}
    for name, coefficient in [('speed_kmh', -1.4), ('rain_mm', -5), ('cloud_cover_pct', .18),
                              ('humidity_pct', .08), ('temperature_c', -.15)]:
        before, after = observed.get(name), effective.get(name)
        if before is not None and after is not None:
            contributions['wind_speed_kmh' if name == 'speed_kmh' else name] = coefficient * (after - before)
    before, after = observed.get('boundary_layer_height'), effective.get('boundary_layer_height')
    if before is not None and after is not None:
        contributions['boundary_layer_height'] = 10 * math.log(max(50, before) / max(50, after))
    gain = math.sqrt(min(24, horizon) / 6)
    value = round(min(2000, max(0, baseline['pm25'] + sum(contributions.values()) * gain)), 2)
    return dict(alternative, pm25=value, delta_pm25=round(value - (baseline.get('baseline_pm25') or baseline['pm25']), 2),
                model='demo-response', model_validated=False, interval=None, nominal_coverage=None,
                empirical_test_coverage=None, scenario=True, interval_valid_for_scenario=False,
                reason='Illustrative synthetic response recipe; not a calibrated air-quality forecast.',
                explanations=[{'feature': name, 'contribution_pm25': round(amount * gain, 2),
                               'method': 'Synthetic demo assumption'}
                              for name, amount in sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)],
                response_method='Synthetic weather/fire sensitivity recipe. Coefficients are demonstration assumptions, not measured causal effects.')


def initialize():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS simulation_runs (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL, created_at TEXT NOT NULL,
            mode TEXT NOT NULL, city_id TEXT NOT NULL, name TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS simulations_session ON simulation_runs(session_id,created_at);
        ''')


def execute(request):
    from .service import snapshot, impact
    moment = request.get('at')
    baseline = snapshot(request['mode'], moment, request['horizon'])
    inputs = {name: value for name, value in request.items()
              if name not in ('name', 'session_id', 'city_id', 'mode', 'at', 'horizon')}
    alternative = snapshot(request['mode'], baseline['time'], request['horizon'], **inputs)
    comparisons = []
    for before, after in zip(baseline['cities'], alternative['cities']):
        base, value = before['forecast']['pm25'], after['forecast']['pm25']
        comparisons.append({'city_id': after['id'], 'name': after['name'], 'baseline_pm25': base,
                            'scenario_pm25': value, 'difference': round(value - base, 2) if base is not None and value is not None else None,
                            'baseline_arrival': before['arrival_hours'], 'scenario_arrival': after['arrival_hours'],
                            'baseline_transport_score': before['transport_score'], 'scenario_transport_score': after['transport_score']})
    result = {'id': str(uuid.uuid4()), 'name': request['name'].strip(), 'created_at': utcnow(),
              'mode': request['mode'], 'city_id': request['city_id'], 'horizon': request['horizon'],
              'at': baseline['time'], 'inputs': inputs, 'comparisons': comparisons,
              'baseline': baseline, 'scenario': alternative,
              'impact': {'baseline': impact(baseline, request['city_id']), 'scenario': impact(alternative, request['city_id'])},
              'cloud_delivery': {'status': 'local', 'detail': 'Saved on the persistent EC2 data volume.'},
              'note': 'Synthetic demonstration assumptions; not an operational forecast.' if request['mode'] == 'demo'
                      else 'Only available observed inputs are used. Missing measurements remain unavailable.'}
    with connect() as db:
        db.execute('INSERT INTO simulation_runs VALUES (?,?,?,?,?,?,?)',
                   (result['id'], request['session_id'], result['created_at'], result['mode'], result['city_id'], result['name'], json.dumps(result, allow_nan=False)))
    # Cloud delivery can fail independently; a local run remains inspectable.
    from . import aws_services
    if aws_services.configured() and aws_services.writes_enabled():
        try:
            result['cloud_delivery'] = aws_services.publish_simulation(result)
        except Exception as error:
            result['cloud_delivery'] = {'status': 'pending', 'detail': f'Local run saved; cloud delivery failed ({type(error).__name__}).'}
        with connect() as db:
            db.execute('UPDATE simulation_runs SET payload=? WHERE id=?', (json.dumps(result, allow_nan=False), result['id']))
    return result


def history(session_id, mode):
    with connect() as db:
        rows = db.execute('SELECT id,name,created_at,mode,city_id,payload FROM simulation_runs WHERE session_id=? AND mode=? ORDER BY created_at DESC LIMIT 30',
                          (session_id, mode)).fetchall()
    result = []
    for row in rows:
        payload = json.loads(row['payload'])
        selected = next(item for item in payload['comparisons'] if item['city_id'] == row['city_id'])
        result.append({key: row[key] for key in ('id', 'name', 'created_at', 'mode', 'city_id')} |
                      {'horizon': payload['horizon'], 'at': payload['at'], 'comparison': selected})
    return result


def get_run(run_id, session_id):
    with connect() as db:
        row = db.execute('SELECT payload FROM simulation_runs WHERE id=? AND session_id=?', (run_id, session_id)).fetchone()
    return json.loads(row['payload']) if row else None
