from datetime import datetime
import math
import joblib
import pytest
from backend.config import CITIES
from backend.forecast import FEATURES, feature_row, hourly_air, artifact_path
from backend.service import snapshot, import_csv
from backend.storage import records

def test_weather_overrides_preserve_observations_and_baseline(client):
    base = client.get('/api/twin?mode=demo').json()
    response = client.post('/api/scenario',json={'mode':'demo','rain_mm':12,'cloud_cover_pct':95,'humidity_pct':90,
        'boundary_layer_height':200,'temperature_c':18,'smoke_factor':2,'burning':'crop_residue'})
    assert response.status_code == 200, response.text
    changed = response.json()
    assert changed['scenario']['rain_mm'] == 12
    for before, after in zip(base['cities'],changed['cities']):
        assert before['observed_pm25'] == after['observed_pm25']
        assert before['forecast']['pm25'] == after['baseline_forecast']['pm25']
        assert after['weather']['effective']['rain_mm'] == 12
        assert after['weather']['effective']['cloud_cover_pct'] == 95
        assert after['forecast']['feature_values']['rain_mm'] == 12
        assert after['forecast']['scenario'] and not after['forecast']['interval_valid_for_scenario']
        assert len(after['environment']['notes']) == 4
        assert after['environment']['references']

def test_emission_proxy_changes_frp_feature_without_changing_fire_counts(isolated_storage):
    now=datetime.fromisoformat(snapshot('demo')['time'])
    context=(hourly_air('demo'),records('fires','demo'),records('wind','demo'))
    baseline=feature_row(CITIES[0],now,*context)
    changed=feature_row(CITIES[0],now,*context,smoke_factor=2)
    values=dict(zip(FEATURES,baseline['values']))
    altered=dict(zip(FEATURES,changed['values']))
    assert altered['upwind_fire_count'] == values['upwind_fire_count']
    assert altered['upwind_frp'] == pytest.approx(2*values['upwind_frp'])

def test_no_fire_and_zero_smoke_have_no_transport_arrival(client):
    for settings in ({'multiplier':0},{'smoke_factor':0}):
        data=client.post('/api/scenario',json={'mode':'demo',**settings}).json()
        assert not any(edge['arrives'] for edge in data['edges'])
        assert all(city['arrival_hours'] is None for city in data['cities'])
        assert all(city['observed_pm25'] is not None for city in data['cities'])

def test_legacy_model_artifact_falls_back_instead_of_crashing(isolated_storage):
    path=artifact_path('demo',1)
    joblib.dump({'report':{'features':['old_schema']}},path)
    try:
        data=snapshot('demo',horizon=1,rain_mm=4)
        assert data['cities'][0]['forecast']['model'] == 'persistence'
        assert 'retrain' in data['cities'][0]['forecast']['reason']
    finally:
        path.unlink()

def test_weather_import_accepts_old_columns_and_keeps_missing_values(client):
    result=import_csv('wind','city_id,time,speed_kmh,direction_deg\ndelhi,2026-10-01T12:00:00+00:00,10,270\n')
    assert result['imported_rows'] == 1
    row=records('wind','live')[-1]
    assert row['rain_mm'] is None and row['cloud_cover_pct'] is None
    with pytest.raises(ValueError,match='cloud_cover_pct'):
        import_csv('wind','city_id,time,speed_kmh,direction_deg,cloud_cover_pct\ndelhi,2026-10-01T12:00:00+00:00,10,270,NaN\n')

@pytest.mark.parametrize('fields',[{'rain_mm':-1},{'cloud_cover_pct':101},{'smoke_factor':4},{'burning':'confirmed_stubble'},{'humidity_pct':float('inf')}])
def test_invalid_weather_scenarios_rejected(client,fields):
    # Use raw JSON for non-finite input so client-side encoding cannot reject it first.
    import json
    response=client.post('/api/scenario',content=json.dumps({'mode':'demo',**fields}),headers={'Content-Type':'application/json'})
    assert response.status_code == 422

def test_weather_chat_uses_explicit_rain_and_cloud_inputs(client):
    result=client.post('/api/chat',json={'mode':'demo','message':'What happens with 8 mm rain and 90% clouds?'}).json()
    assert result['agent'] == 'scenario'
    assert result['evidence']['scenario']['rain_mm'] == 8
    assert result['evidence']['scenario']['cloud_cover_pct'] == 90
    assert 'Rain' in str(result['evidence']['environment']['notes'])

def test_strands_graph_keeps_weather_scenario_evidence(client,monkeypatch):
    from backend import analysis, platform_store as ledger
    monkeypatch.setenv('ATMOS_AWS_MODE','disabled')
    run=ledger.create_run({'mode':'demo','city_id':'delhi','horizon':6,'audience':'principal','rain_mm':7,
        'cloud_cover_pct':88,'smoke_factor':1.5,'burning':'waste','session_id':'weather-check'})
    result=analysis.execute(run['id'])
    assert result['status'] == 'complete', result['error']
    scenario=result['result']['agents']['scenario']
    assert scenario['inputs']['rain_mm'] == 7
    assert scenario['environment']['weather']['effective']['cloud_cover_pct'] == 88
    assert 'Waste burning' in scenario['environment']['notes'][-1]['text']

def test_user_inputs_drive_live_forecast_without_provider_keys(client):
    time = snapshot('demo')['time']
    for kind, csv in [
        ('wind', f'city_id,time,speed_kmh,direction_deg,rain_mm,cloud_cover_pct\ndelhi,{time},20,310,6,85\n'),
        ('aqi', f'city_id,station_id,time,pm25\ndelhi,uploaded-station,{time},123\n')]:
        response=client.post('/api/import',json={'kind':kind,'mode':'live','source':'User supplied integration data','csv':csv})
        assert response.status_code == 200
    data=client.post('/api/scenario',json={'mode':'live','rain_mm':4}).json()
    city=data['cities'][0]
    assert city['observed_pm25'] == 123
    assert city['forecast']['pm25'] == 123
    assert city['weather']['observed']['rain_mm'] == 6
    assert city['forecast']['feature_values']['rain_mm'] == 4
    assert city['weather']['source'] == 'User supplied integration data'
    assert city['forecast']['model'] == 'persistence'

def test_deployment_origin_can_be_configured_without_accepting_other_sites(client,monkeypatch):
    monkeypatch.setenv('ATMOS_ALLOWED_HOSTS','atmos.example.com')
    accepted=client.post('/api/scenario',json={'mode':'demo'},headers={'Origin':'https://atmos.example.com'})
    rejected=client.post('/api/scenario',json={'mode':'demo'},headers={'Origin':'https://other.example.com'})
    assert accepted.status_code == 200
    assert rejected.status_code == 403

def test_incomplete_user_csv_returns_readable_validation_error(client):
    response=client.post('/api/import',json={'kind':'aqi','csv':'city_id,pm25\ndelhi,100\n'})
    assert response.status_code == 400
    assert 'required columns' in response.json()['detail']
