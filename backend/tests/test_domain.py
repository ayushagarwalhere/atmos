from datetime import datetime, timedelta, timezone
import pytest
from backend.transport import cluster_fires, transport_links, drift, distance
from backend.service import snapshot, import_csv, pm25_subindex
from backend.storage import records, put, set_setting
from backend.forecast import train, predict_city, hourly_air
from backend.config import CITIES

def test_dbscan_keeps_isolated_detections():
    fires=[{'id':str(index),'lat':lat,'lon':lon,'frp':5,'confidence_score':.65,'time':'2026-10-01T12:00:00+00:00','source':'test'} for index,(lat,lon) in enumerate([(30,75),(30.01,75.01),(31.5,76.8)])]
    clusters=cluster_fires(fires)
    assert sorted(c['fire_count'] for c in clusters)==[1,2]
    assert sum(c['total_frp'] for c in clusters)==15
    assert sum(c['isolated'] for c in clusters)==1

def test_meteorological_wind_and_hourly_drift():
    at=datetime(2026,10,1,tzinfo=timezone.utc)
    cluster={'id':'fire','lat':30,'lon':75,'fire_count':8,'total_frp':40,'mean_detection_confidence':.8}
    city=dict(drift(cluster,90,100),id='city')
    winds=[{'lat':30,'lon':75,'time':(at+timedelta(hours=hour)).isoformat(),'speed_kmh':20,'direction_deg':270} for hour in range(48)]
    east=transport_links([cluster],[city],winds,at)[0]
    west=transport_links([cluster],[city],winds,at,direction=90)[0]
    calm=transport_links([cluster],[city],winds,at,speed=0)[0]
    assert east['arrives'] and east['travel_hours']==5
    assert not west['arrives'] and not calm['arrives']
    assert east['path'][1]['lon']>75
    assert 0<=east['transport_score']<=1
    assert distance(cluster,city)==pytest.approx(100,rel=.001)

def test_live_demo_partition_and_invalid_import(client):
    live=client.get('/api/twin?mode=live').json()
    demo=client.get('/api/twin?mode=demo').json()
    assert len(demo['clusters'])>0
    assert live['fires_count']==0
    assert all(city['forecast']['pm25'] is None for city in live['cities'])
    response=client.post('/api/import',json={'kind':'aqi','csv':'city_id,station_id,time,pm25\ndelhi,x,2026-10-01T12:00:00,70\n'})
    assert response.status_code==400
    assert 'offset' in response.json()['detail']
    assert client.post('/api/scenario',json={'speed':-2}).status_code==422

def test_scenario_recomputes_paths_and_does_not_fake_persistence_response(client):
    baseline=client.get('/api/twin?mode=demo').json()
    changed=client.post('/api/scenario',json={'mode':'demo','direction':90,'speed':18,'multiplier':2}).json()
    assert changed['total_frp']==pytest.approx(baseline['total_frp']*2,abs=.01)
    assert changed['edges'][0]['path'][1]!=baseline['edges'][0]['path'][1]
    assert changed['cities'][0]['forecast']['scenario']
    assert not changed['cities'][0]['forecast']['interval_valid_for_scenario']

def test_history_slider_has_real_time_dependent_data(client):
    now=client.get('/api/twin?mode=demo').json()
    at=(datetime.fromisoformat(now['time'])-timedelta(hours=24)).isoformat()
    past=snapshot('demo',at=at)
    assert past['time']!=now['time']
    assert past['cities'][0]['observed_pm25']!=now['cities'][0]['observed_pm25']
    assert all(datetime.fromisoformat(cluster['time'])<=datetime.fromisoformat(at) for cluster in past['clusters'])

def test_pm25_subindex_is_not_overall_aqi():
    assert pm25_subindex(30)==50
    assert pm25_subindex(90)==200
    assert pm25_subindex(250)==400

def test_demo_training_requires_explicit_opt_in():
    with pytest.raises(ValueError,match='Synthetic'):
        train('demo',6)

def test_real_ml_comparison_chronology_and_intervals(isolated_storage):
    report=train('demo',6,True)
    assert {'persistence','linear','xgboost','lightgbm'}<=report['comparison'].keys()
    assert not report['failures'] and not report['unavailable']
    assert report['demo_only'] and not report['validated_for_live']
    boundaries=[datetime.fromisoformat(value) for value in report['split']['boundaries']]
    assert boundaries==sorted(boundaries)
    assert datetime.fromisoformat(report['training_end'])+timedelta(hours=6)<boundaries[0]
    assert 0<=report['interval']['test_coverage']<=1
    assert report['interval']['calibration_rows']>=30
    now=snapshot('demo')['time']
    prediction=predict_city(CITIES[0],datetime.fromisoformat(now),'demo',6)
    assert prediction['interval'][0]<=prediction['pm25']<=prediction['interval'][1]
    assert prediction['explanations']

def test_sdk_orchestrator_executes_specialists_without_invented_numbers(client):
    response=client.post('/api/chat',json={'mode':'demo','message':'What if fires double?','city_id':'delhi'})
    assert response.status_code==200
    result=response.json()
    assert result['agent']=='scenario'
    assert result['agent_error'] is None
    assert result['framework']['framework']=='AWS Strands Agents SDK'
    assert result['trace'][0]['tool']=='scenario_evidence'
    assert result['evidence']['scenario']['fire_multiplier']==2
    strategy=client.post('/api/chat',json={'mode':'demo','message':'Give school guidance','audience':'principal'}).json()
    assert strategy['agent']=='strategy'
    assert 'Synthetic' in strategy['answer']

def test_demo_and_scenario_cannot_send_alerts(monkeypatch):
    from backend.alerts import check_alerts, DEFAULT_RULE
    deliveries=[]
    monkeypatch.setenv('ALERT_SEND_ENABLED','true')
    monkeypatch.setattr('backend.alerts.deliver',lambda event:deliveries.append(event))
    set_setting('alert_rule',dict(DEFAULT_RULE,enabled=True,pm25_threshold=1,minimum_transport_score=0,channel='telegram'))
    result=check_alerts(snapshot('demo'),send=True)
    assert not deliveries
    assert all(event['status']=='suppressed' for event in result['alerts'])
    assert all('synthetic demo; delivery disabled' in event['reasons'] for event in result['alerts'])
    set_setting('alert_rule',DEFAULT_RULE)

def test_incomplete_real_history_cannot_claim_ml_success(client):
    with pytest.raises(ValueError):
        train('live',6)

def test_arrival_backtest_publishes_misses(client):
    from backend.service import arrival_backtest
    report=arrival_backtest('demo',2)
    assert report['demo_only'] and report['cases']
    assert 'misses' in report and 'false_negatives' in report
    assert {case['outcome'] for case in report['cases']}<={'hit','miss','false_negative','correct_negative'}
