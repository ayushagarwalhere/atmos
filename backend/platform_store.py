"""Durable run ledger, evidence library and local full-text retrieval."""
import json
import re
import uuid
from .storage import connect, utcnow

def initialize():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, session_id TEXT, mode TEXT,
            city_id TEXT, status TEXT, created_at TEXT, updated_at TEXT, request TEXT, result TEXT, error TEXT);
        CREATE INDEX IF NOT EXISTS runs_session ON runs(session_id,created_at);
        CREATE TABLE IF NOT EXISTS run_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT, time TEXT, kind TEXT, payload TEXT);
        CREATE INDEX IF NOT EXISTS events_run ON run_events(run_id,sequence);
        CREATE TABLE IF NOT EXISTS artifacts (id TEXT PRIMARY KEY, run_id TEXT, mode TEXT,
            city_id TEXT, time TEXT, title TEXT, payload TEXT, delivery TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS evidence_search USING fts5(id UNINDEXED,mode UNINDEXED,city_id UNINDEXED,title,body);
        CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, run_id TEXT, city_id TEXT,
            mode TEXT, title TEXT, status TEXT, time TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS audit (sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT, action TEXT, subject TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS durable_jobs (id TEXT PRIMARY KEY, name TEXT, status TEXT, payload TEXT);
        ''')

def audit(action, subject, detail=None):
    with connect() as db:
        db.execute('INSERT INTO audit(time,action,subject,detail) VALUES (?,?,?,?)',
                   (utcnow(),action,subject,json.dumps(detail or {},allow_nan=False)))

def create_run(request):
    run_id = str(uuid.uuid4())
    session_id = request.get('session_id') or str(uuid.uuid4())
    with connect() as db:
        db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?)',
            (run_id,session_id,request['mode'],request['city_id'],'queued',utcnow(),utcnow(),json.dumps(request),None,None))
    emit(run_id,'queued',{'session_id':session_id})
    return get_run(run_id)

def get_run(run_id):
    with connect() as db:
        row = db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
    if not row:
        raise ValueError('Run not found')
    result = dict(row)
    for key in ('request','result'):
        result[key] = json.loads(result[key]) if result[key] else None
    return result

def list_runs(session_id=None, limit=30):
    with connect() as db:
        rows = db.execute('SELECT id FROM runs '+('WHERE session_id=? ' if session_id else '')+'ORDER BY created_at DESC LIMIT ?',
            (session_id,limit) if session_id else (limit,)).fetchall()
    return [get_run(row[0]) for row in rows]

def update_run(run_id,status,result=None,error=None):
    with connect() as db:
        db.execute('UPDATE runs SET status=?,updated_at=?,result=COALESCE(?,result),error=? WHERE id=?',
            (status,utcnow(),json.dumps(result,allow_nan=False) if result else None,error,run_id))

def emit(run_id,kind,payload):
    with connect() as db:
        cursor = db.execute('INSERT INTO run_events(run_id,time,kind,payload) VALUES (?,?,?,?)',
            (run_id,utcnow(),kind,json.dumps(payload,allow_nan=False)))
        return cursor.lastrowid

def events(run_id,after=0):
    with connect() as db:
        return [dict(row,payload=json.loads(row['payload'])) for row in db.execute(
            'SELECT * FROM run_events WHERE run_id=? AND sequence>? ORDER BY sequence',(run_id,after))]

def save_artifact(run_id,title,payload):
    run = get_run(run_id)
    artifact_id = str(uuid.uuid4())
    with connect() as db:
        db.execute('INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?,?)',(artifact_id,run_id,run['mode'],run['city_id'],utcnow(),title,json.dumps(payload,allow_nan=False),'local'))
        db.execute('INSERT INTO evidence_search VALUES (?,?,?,?,?)',(artifact_id,run['mode'],run['city_id'],title,json.dumps(payload)))
    audit('artifact.created',artifact_id,{'run_id':run_id,'mode':run['mode']})
    return artifact_id

def artifact(artifact_id):
    with connect() as db:
        row = db.execute('SELECT * FROM artifacts WHERE id=?',(artifact_id,)).fetchone()
    if not row:
        raise ValueError('Artifact not found')
    return dict(row,payload=json.loads(row['payload']))

def artifacts(mode=None):
    with connect() as db:
        rows = db.execute('SELECT id,run_id,mode,city_id,time,title,delivery FROM artifacts '+('WHERE mode=? ' if mode else '')+'ORDER BY time DESC LIMIT 50',(mode,) if mode else ()).fetchall()
    return [dict(row) for row in rows]

def search(query,mode,city_id=None):
    tokens = re.findall(r'[\w]+',query)[:12]
    if not tokens:
        return []
    expression = ' OR '.join('"'+token+'"' for token in tokens)
    with connect() as db:
        return [dict(row) for row in db.execute('SELECT id,title,snippet(evidence_search,4,\'[\',\']\',\'…\',24) AS excerpt FROM evidence_search WHERE evidence_search MATCH ? AND mode=? '+('AND city_id=? ' if city_id else '')+'ORDER BY rank LIMIT 10',(expression,mode,city_id) if city_id else (expression,mode))]

def create_action(run_id,title,payload):
    run = get_run(run_id)
    action_id = str(uuid.uuid4())
    with connect() as db:
        db.execute('INSERT INTO actions VALUES (?,?,?,?,?,?,?,?)',(action_id,run_id,run['city_id'],run['mode'],title,'proposed',utcnow(),json.dumps(payload)))
    audit('action.proposed',action_id,{'run_id':run_id})
    return action_id

def list_actions(mode=None):
    with connect() as db:
        return [dict(row,payload=json.loads(row['payload'])) for row in db.execute('SELECT * FROM actions '+('WHERE mode=? ' if mode else '')+'ORDER BY time DESC LIMIT 50',(mode,) if mode else ())]

def change_action(action_id,status):
    with connect() as db:
        cursor = db.execute('UPDATE actions SET status=?,time=? WHERE id=?',(status,utcnow(),action_id))
    if not cursor.rowcount:
        raise ValueError('Action not found')
    audit('action.status',action_id,{'status':status})

def save_job(value):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO durable_jobs VALUES (?,?,?,?)',(value['id'],value['name'],value['status'],json.dumps(value,allow_nan=False)))

def get_job(job_id):
    with connect() as db:
        row = db.execute('SELECT payload FROM durable_jobs WHERE id=?',(job_id,)).fetchone()
    return json.loads(row[0]) if row else None

def recover():
    # Calls are not silently replayed after a crash: a rerun creates new evidence.
    with connect() as db:
        ids = [row[0] for row in db.execute("SELECT id FROM runs WHERE status IN ('running','queued')")]
        jobs = [json.loads(row[0]) for row in db.execute("SELECT payload FROM durable_jobs WHERE status IN ('running','queued')")]
    for run_id in ids:
        update_run(run_id,'interrupted',error='Process restarted; rerun this analysis.')
        emit(run_id,'interrupted',{'reason':'Process restarted'})
    for value in jobs:
        value.update(status='interrupted',error='Process restarted; rerun this job.')
        save_job(value)
