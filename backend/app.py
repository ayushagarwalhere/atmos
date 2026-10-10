import asyncio
import os
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Literal
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import agents
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
    def run():
        jobs[task_id]['status']='running'
        try:
            jobs[task_id].update(status='complete',result=fn(),completed_at=utcnow())
        except Exception as exc:
            jobs[task_id].update(status='failed',error=str(exc) if isinstance(exc,ValueError) else type(exc).__name__,completed_at=utcnow())
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
    seed_demo()
    from .storage import provider_status
    if not os.getenv('FIRMS_MAP_KEY'):
        provider_status('NASA FIRMS','missing_key','Set FIRMS_MAP_KEY or import FIRMS CSV')
    if not os.getenv('OPENAQ_API_KEY'):
        provider_status('OpenAQ','missing_key','Set OPENAQ_API_KEY or import station PM2.5 CSV')
    async def scheduler():
        while True:
            if os.getenv('ATMOS_DISABLE_SCHEDULER','false').lower()!='true':
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
    if request.method not in ('GET','HEAD','OPTIONS') and origin and urlparse(origin).hostname not in ('localhost','127.0.0.1'):
        return JSONResponse({'detail':'Use the local app origin for mutations'},status_code=403)
    token = os.getenv('ATMOS_API_TOKEN')
    if token and request.url.path.startswith('/api/') and request.headers.get('authorization')!=f'Bearer {token}':
        return JSONResponse({'detail':'Backend API token required'},status_code=401)
    return await call_next(request)

@app.exception_handler(ValueError)
async def validation_error(request,exc):
    return JSONResponse({'detail':str(exc)},status_code=400)

@app.get('/api/health')
def health():
    return {'status':'ok','time':utcnow(),'providers':providers(),'agents':agents.runtime_status(),
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

@app.post('/api/scenario')
def scenario(body:Scenario):
    data = snapshot(body.mode,body.at,body.horizon,body.direction,body.speed,body.multiplier)
    data['impact'] = impact(data,body.city_id)
    return data

@app.post('/api/refresh')
def refresh_data():
    return job('refresh',refresh_job)

@app.get('/api/jobs/{task_id}')
def get_job(task_id:str):
    if task_id not in jobs:
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
def get_impact(city_id:City='delhi',mode:Mode='demo',horizon:int=Query(6,ge=1,le=48)):
    return impact(snapshot(mode,horizon=horizon),city_id)

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
        {'direction':body.direction,'speed':body.speed,'multiplier':body.multiplier})

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
    'wind':'city_id,time,speed_kmh,direction_deg,lat,lon,boundary_layer_height\ndelhi,2026-10-09T12:00:00+00:00,18,310,28.6139,77.2090,500\n',
    'aqi':'city_id,station_id,time,pm25,lat,lon\ndelhi,station-001,2026-10-09T12:00:00+00:00,65,28.6139,77.2090\n',
    'facilities':'city_id,time,name,kind,lat,lon,population\ndelhi,2026-10-09T12:00:00+00:00,Example school,school,28.61,77.2,\n',
    'news':'city_id,time,title,url\ndelhi,2026-10-09T12:00:00+00:00,Source headline,https://www.pib.gov.in/\n',
}

@app.get('/api/import/templates/{kind}')
def template(kind:str):
    if kind not in TEMPLATES:
        raise HTTPException(404,'Template not found')
    return PlainTextResponse(TEMPLATES[kind],media_type='text/csv',headers={'Content-Disposition':f'attachment; filename=atmos-{kind}-template.csv'})

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

if (ROOT/'dist').exists():
    app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='frontend')
