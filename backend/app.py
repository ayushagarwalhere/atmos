import asyncio
import os
import threading
import uuid
import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import agents
from . import platform_store as ledger, analysis, aws_services
from . import cloud_budget, simulation
from .alerts import DEFAULT_RULE, check_alerts
from .config import CITIES, ROOT
from .demo import seed_demo
from .forecast import train
from .providers import refresh, weather_refresh, openaq_refresh, facilities_refresh, guarded
from .service import snapshot, impact, advisory, import_csv, arrival_backtest
from .storage import init_db, providers, records, setting, set_setting, utcnow

jobs = {}
job_lock = threading.Lock()
refresh_lock = threading.Lock()
training_lock = threading.Lock()
Mode = Literal['live','demo']
City = Literal['delhi','chandigarh','ludhiana','lucknow']

def job(name, fn):
    with job_lock:
        active = next((dict(value) for value in jobs.values() if value['name']==name and value['status'] in ('queued','running')),None)
        if active:
            return active
        task_id = str(uuid.uuid4())
        jobs[task_id] = {'id':task_id,'name':name,'status':'queued','started_at':utcnow()}
        ledger.save_job(jobs[task_id])
    def run():
        jobs[task_id]['status']='running'
        ledger.save_job(jobs[task_id])
        try:
            jobs[task_id].update(status='complete',result=fn(),completed_at=utcnow())
        except Exception as exc:
            jobs[task_id].update(status='failed',error=str(exc) if isinstance(exc,ValueError) else type(exc).__name__,completed_at=utcnow())
        ledger.save_job(jobs[task_id])
    threading.Thread(target=run,daemon=True).start()
    return dict(jobs[task_id])

def refresh_job():
    with refresh_lock:
        refresh()
        current = snapshot('live',persist=True)
        alerts = check_alerts(current,send=True)
        return {'providers':providers(),'alerts':alerts}

@asynccontextmanager
async def lifespan(app):
    init_db()
    simulation.initialize()
    ledger.initialize()
    ledger.recover()
    seed_demo()
    from .storage import provider_status
    if not os.getenv('FIRMS_MAP_KEY'):
        provider_status('NASA FIRMS','missing_key','Set FIRMS_MAP_KEY or import FIRMS CSV')
    if not os.getenv('OPENAQ_API_KEY'):
        provider_status('OpenAQ','missing_key','Set OPENAQ_API_KEY or import station PM2.5 CSV')
    async def scheduler():
        while True:
            if os.getenv('ATMOS_DISABLE_SCHEDULER','false').lower()!='true':
                await asyncio.to_thread(seed_demo)
                await asyncio.to_thread(refresh_job)
            await asyncio.sleep(max(15,int(os.getenv('ATMOS_REFRESH_MINUTES','60')))*60)
    task = asyncio.create_task(scheduler())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title='Atmos smoke twin',version='1.0.0',lifespan=lifespan)

@app.middleware('http')
async def local_origin_guard(request:Request,call_next):
    origin = request.headers.get('origin')
    allowed_hosts = {'localhost','127.0.0.1'} | {host.strip().lower() for host in os.getenv('ATMOS_ALLOWED_HOSTS','').split(',') if host.strip()}
    if request.method not in ('GET','HEAD','OPTIONS') and origin and urlparse(origin).hostname not in allowed_hosts:
        return JSONResponse({'detail':'Use an allowed app origin for mutations'},status_code=403)
    token = os.getenv('ATMOS_API_TOKEN')
    if token and request.url.path.startswith('/api/') and request.headers.get('authorization')!=f'Bearer {token}':
        return JSONResponse({'detail':'Backend API token required'},status_code=401)
    return await call_next(request)

@app.exception_handler(ValueError)
async def validation_error(request,exc):
    return JSONResponse({'detail':str(exc)},status_code=400)

@app.exception_handler(RequestValidationError)
async def request_validation_error(request,exc):
    # Omit raw inputs: non-finite JSON numbers cannot be encoded into an error response.
    return JSONResponse({'detail': [{'loc': error['loc'], 'msg': error['msg'], 'type': error['type']}
        for error in exc.errors()]},status_code=422)

@app.get('/api/health')
def health():
    return {'status':'ok','time':utcnow(),'providers':providers(),'agents':agents.runtime_status(),
        'platform':aws_services.status(),
        'scheduler_minutes':max(15,int(os.getenv('ATMOS_REFRESH_MINUTES','60'))),'default_mode':os.getenv('ATMOS_DEFAULT_MODE','demo')}

@app.get('/api/twin')
def get_twin(mode:Mode='demo',at:str|None=None,horizon:int=Query(6,ge=1,le=48)):
    return snapshot(mode,at,horizon)

class Scenario(BaseModel):
    mode:Mode='demo'
    city_id:City='delhi'
    horizon:int=Field(6,ge=1,le=48)
    at:str|None=None
    direction:float|None=Field(None,ge=0,le=360)
    speed:float|None=Field(None,ge=0,le=150)
    multiplier:float=Field(1,ge=0,le=4)
    rain_mm:float|None=Field(None,ge=0,le=200)
    cloud_cover_pct:float|None=Field(None,ge=0,le=100)
    humidity_pct:float|None=Field(None,ge=0,le=100)
    temperature_c:float|None=Field(None,ge=-90,le=65)
    boundary_layer_height:float|None=Field(None,ge=0,le=10000)
    smoke_factor:float=Field(1,ge=0,le=3)
    burning:Literal['unspecified','crop_residue','wildfire','waste']='unspecified'

@app.post('/api/scenario')
def scenario(body:Scenario):
    data = snapshot(**body.model_dump(exclude={'city_id'}))
    data['impact'] = impact(data,body.city_id)
    return data

class SimulationRequest(Scenario):
    name: str = Field('Regional what-if', min_length=1, max_length=100, pattern=r'.*\S.*')
    session_id: str = Field(min_length=16, max_length=100, pattern=r'^[a-zA-Z0-9-]+$')

@app.post('/api/simulations')
def run_simulation(body:SimulationRequest):
    return simulation.execute(body.model_dump())

@app.get('/api/simulations')
def list_simulations(session_id: str = Query(min_length=16, max_length=100), mode: Mode = 'demo'):
    return {'runs': simulation.history(session_id, mode)}

@app.get('/api/simulations/{run_id}')
def get_simulation(run_id: str, session_id: str = Query(min_length=16, max_length=100)):
    result = simulation.get_run(run_id, session_id)
    if not result:
        raise HTTPException(404, 'Simulation not found in this session')
    return result

@app.post('/api/refresh')
def refresh_data():
    return job('refresh',refresh_job)

@app.get('/api/jobs/{task_id}')
def get_job(task_id:str):
    if task_id not in jobs:
        saved = ledger.get_job(task_id)
        if saved:
            return saved
        raise HTTPException(404,'Job not found')
    return dict(jobs[task_id])

class Training(BaseModel):
    mode:Mode='live'
    horizon:int=Field(6,ge=1,le=48)
    allow_demo:bool=False

@app.post('/api/train')
def train_models(body:Training):
    def run():
        with training_lock:
            return train(body.mode,body.horizon,body.allow_demo)
    return job(f'train-{body.mode}-{body.horizon}',run)

class Backtest(BaseModel):
    mode:Mode='live'
    days:int=Field(7,ge=1,le=60)

@app.post('/api/backtest')
def backtest(body:Backtest):
    return job(f'backtest-{body.mode}',lambda:arrival_backtest(body.mode,body.days))

@app.get('/api/models')
def model_reports(mode:Mode='live'):
    return {'reports':records('model_runs',mode)[-20:]}

@app.get('/api/history')
def history(mode:Mode='live'):
    result = {}
    for kind in ('fires','wind','aqi'):
        rows = records(kind,mode)
        result[kind] = {'count':len(rows),'start':rows[0]['time'] if rows else None,'end':rows[-1]['time'] if rows else None}
    return result

class HistoryLoad(BaseModel):
    start:date
    end:date

@app.post('/api/history/load')
def load_history(body:HistoryLoad):
    if body.end<body.start or (body.end-body.start).days>90 or body.end>=date.today():
        raise ValueError('Choose a past date range up to 90 days; obtain historical fires through NASA CSV imports.')
    def run():
        guarded('Open-Meteo',lambda:weather_refresh(body.start.isoformat(),body.end.isoformat()))
        guarded('OpenAQ',lambda:openaq_refresh(body.start.isoformat()+'T00:00:00+00:00',(body.end+timedelta(days=1)).isoformat()+'T00:00:00+00:00'))
        return {'providers':providers(),'note':'Historical fire detections still require NASA archived CSV import.'}
    return job('history',run)

@app.get('/api/impact')
def get_impact(city_id:City='delhi',mode:Mode='demo',horizon:int=Query(6,ge=1,le=48),at:str|None=None):
    return impact(snapshot(mode,at=at,horizon=horizon),city_id)

@app.post('/api/facilities/{city_id}')
def load_facilities(city_id:City):
    return job(f'facilities-{city_id}',lambda: {'imported':facilities_refresh(city_id)})

@app.get('/api/advisory')
def get_advisory(city_id:City='delhi',mode:Mode='demo',audience:Literal['principal','parent','official']='principal'):
    city = next(c for c in snapshot(mode)['cities'] if c['id']==city_id)
    return {'text':advisory(city,audience,mode),'city_id':city_id,'audience':audience}

class Chat(Scenario):
    message:str=Field(min_length=1,max_length=2000)
    audience:Literal['principal','parent','official']='principal'

@app.post('/api/chat')
def ask(body:Chat):
    return agents.chat(body.message,body.city_id,body.mode,body.audience,body.horizon,
        body.model_dump(exclude={'message','city_id','mode','audience','horizon','at'}))

class CSVImport(BaseModel):
    kind:Literal['fires','wind','aqi','facilities','news']
    mode:Mode='live'
    source:str=Field('User CSV import',min_length=3,max_length=200)
    csv:str=Field(max_length=10000000)

@app.post('/api/import')
def import_data(body:CSVImport):
    return import_csv(body.kind,body.csv,body.mode,body.source)

TEMPLATES = {
    'fires':'latitude,longitude,time,confidence,frp\n30.3,75.5,2026-10-09T12:00:00+00:00,n,8.5\n',
    'wind':'city_id,time,speed_kmh,direction_deg,lat,lon,boundary_layer_height,rain_mm,cloud_cover_pct,humidity_pct,temperature_c\ndelhi,2026-10-09T12:00:00+00:00,18,310,28.6139,77.2090,500,0,40,65,28\n',
    'aqi':'city_id,station_id,time,pm25,lat,lon\ndelhi,station-001,2026-10-09T12:00:00+00:00,65,28.6139,77.2090\n',
    'facilities':'city_id,time,name,kind,lat,lon,population\ndelhi,2026-10-09T12:00:00+00:00,Example school,school,28.61,77.2,\n',
    'news':'city_id,time,title,url\ndelhi,2026-10-09T12:00:00+00:00,Source headline,https://www.pib.gov.in/\n',
}

@app.get('/api/import/templates/{kind}')
def template(kind:str):
    if kind not in TEMPLATES:
        raise HTTPException(404,'Template not found')
    example_time = datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0).isoformat()
    return PlainTextResponse(TEMPLATES[kind].replace('2026-10-09T12:00:00+00:00',example_time),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename=atmos-{kind}-template.csv'})

class AlertRule(BaseModel):
    enabled:bool=False
    pm25_threshold:float=Field(120,ge=1,le=1000)
    minimum_transport_score:float=Field(.65,ge=0,le=1)
    minimum_interval_coverage:float=Field(.8,ge=.5,le=1)
    cooldown_hours:int=Field(24,ge=1,le=168)
    channel:Literal['in_app','telegram','email']='in_app'

@app.get('/api/alerts')
def get_alerts(mode:Mode='live'):
    return {'rule':setting('alert_rule',DEFAULT_RULE),'events':records('alerts',mode)[-30:],
        'external_delivery_enabled':os.getenv('ALERT_SEND_ENABLED','false').lower()=='true'}

@app.put('/api/alerts/rule')
def alert_rule(body:AlertRule):
    set_setting('alert_rule',body.model_dump())
    return body.model_dump()

@app.post('/api/alerts/check')
def evaluate_alerts(body:Backtest):
    return check_alerts(snapshot(body.mode,persist=True),send=False)

class AnalysisRequest(Scenario):
    session_id:str|None=Field(None,pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    message:str=Field('Analyze this city and scenario',max_length=2000)
    audience:Literal['principal','parent','official']='principal'

@app.post('/api/analysis')
def start_analysis(body:AnalysisRequest):
    return analysis.start(body.model_dump())

@app.get('/api/runs')
def runs(session_id:str|None=None):
    return {'runs':ledger.list_runs(session_id)}

@app.get('/api/runs/{run_id}')
def run_detail(run_id:str):
    return ledger.get_run(run_id)

@app.get('/api/runs/{run_id}/events')
async def run_stream(run_id:str,request:Request,after:int=Query(0,ge=0)):
    ledger.get_run(run_id)
    async def stream():
        cursor = after
        while not await request.is_disconnected():
            batch = await asyncio.to_thread(ledger.events,run_id,cursor)
            for event in batch:
                cursor = event['sequence']
                yield f"id: {cursor}\ndata: {json.dumps(event)}\n\n"
            current = await asyncio.to_thread(ledger.get_run,run_id)
            if current['status'] in ('complete','failed','interrupted'):
                break
            if not batch:
                yield ': keepalive\n\n'
            await asyncio.sleep(.7)
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@app.get('/api/artifacts')
def artifact_list(mode:Mode='demo'):
    return {'artifacts':ledger.artifacts(mode)}

@app.get('/api/artifacts/{artifact_id}')
def artifact_detail(artifact_id:str):
    return ledger.artifact(artifact_id)

@app.get('/api/evidence/search')
def evidence_search(q:str=Query(min_length=1,max_length=500),mode:Mode='demo',city_id:City|None=None):
    return aws_services.retrieve(q,mode,city_id)

@app.get('/api/actions')
def action_list(mode:Mode='demo'):
    return {'actions':ledger.list_actions(mode)}

class ActionStatus(BaseModel):
    status:Literal['proposed','accepted','in_progress','done','dismissed']

@app.patch('/api/actions/{action_id}')
def update_action(action_id:str,body:ActionStatus):
    ledger.change_action(action_id,body.status)
    return {'id':action_id,'status':body.status}

@app.get('/api/audit')
def audit_log():
    with ledger.connect() as db:
        return {'entries':[dict(row,detail=json.loads(row['detail'])) for row in db.execute('SELECT * FROM audit ORDER BY sequence DESC LIMIT 100')]}

@app.post('/api/aws/bootstrap')
def local_aws_bootstrap():
    return aws_services.bootstrap()

@app.get('/api/aws/check')
def check_aws_connection():
    return aws_services.connection_check()

@app.get('/api/aws/template')
def aws_infrastructure_template():
    return FileResponse(ROOT/'infra'/'cloud.yaml', media_type='application/yaml', filename='atmos-cloud.yaml')

@app.get('/api/aws/budget')
def cloud_budget_status():
    return cloud_budget.status()

@app.post('/api/aws/queue/process')
def process_queue():
    return job('sqs-analysis',aws_services.consume_one)

@app.post('/api/search/index')
def search_index():
    return job('opensearch-index',aws_services.index_evidence)

if (ROOT/'dist').exists():
    app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='frontend')
