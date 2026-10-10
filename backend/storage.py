import json
import sqlite3
from datetime import datetime, timezone
from .config import DATA_DIR

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def connect():
    db = sqlite3.connect(DATA_DIR / 'atmos.sqlite', timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    return db

def init_db():
    with connect() as db:
        for table in ('fires', 'wind', 'aqi', 'stations', 'facilities', 'predictions', 'model_runs', 'alerts', 'news'):
            db.execute(f'''CREATE TABLE IF NOT EXISTS {table} (
                id TEXT NOT NULL, mode TEXT NOT NULL, time TEXT NOT NULL,
                city_id TEXT, source TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY (id, mode))''')
            db.execute(f'CREATE INDEX IF NOT EXISTS idx_{table}_time ON {table}(mode,time,city_id)')
        db.execute('CREATE TABLE IF NOT EXISTS provider_runs (provider TEXT PRIMARY KEY, time TEXT, status TEXT, detail TEXT, count INTEGER)')
        db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')

TABLES = {'fires', 'wind', 'aqi', 'stations', 'facilities', 'predictions', 'model_runs', 'alerts', 'news'}

def put(table, rows, mode):
    assert table in TABLES and mode in ('live', 'demo')
    with connect() as db:
        db.executemany(f'INSERT OR REPLACE INTO {table} VALUES (?,?,?,?,?,?)', [
            (str(row['id']), mode, row['time'], row.get('city_id'), row['source'], json.dumps(row, allow_nan=False)) for row in rows
        ])

def records(table, mode='live', start=None, end=None, city_id=None):
    assert table in TABLES
    query = f'SELECT payload FROM {table} WHERE mode=?'
    params = [mode]
    for field, op, value in [('time', '>=', start), ('time', '<=', end), ('city_id', '=', city_id)]:
        if value is not None:
            query += f' AND {field}{op}?'
            params.append(value)
    with connect() as db:
        return [json.loads(row[0]) for row in db.execute(query + ' ORDER BY time', params)]

def provider_status(provider, status, detail, count=0):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO provider_runs VALUES (?,?,?,?,?)', (provider, utcnow(), status, detail, count))

def providers():
    with connect() as db:
        return [dict(row) for row in db.execute('SELECT * FROM provider_runs ORDER BY provider')]

def setting(key, default=None):
    with connect() as db:
        row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

def set_setting(key, value):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value)))
