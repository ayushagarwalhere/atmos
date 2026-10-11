"""Conservative per-application reservations, not an AWS billing hard stop."""
import math
import os
from .storage import connect, utcnow

def reserve(service,amount=0,units=1):
    if not math.isfinite(amount) or amount<0 or not isinstance(units,int) or units<1:
        raise ValueError('Invalid cloud reservation')
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS cloud_reservations (time TEXT,service TEXT,usd REAL,units INTEGER)')
        db.execute('BEGIN IMMEDIATE')
        if service=='bedrock':
            spent,calls = db.execute("SELECT COALESCE(SUM(usd),0),COALESCE(SUM(units),0) FROM cloud_reservations WHERE service='bedrock'").fetchone()
            ceiling = min(5,float(os.getenv('ATMOS_BEDROCK_RESERVATION_LIMIT_USD','5')))
            if not math.isfinite(ceiling) or ceiling<=0 or spent+amount>ceiling or calls+units>100:
                raise ValueError('Atmos Bedrock reservation/call limit reached; paid calls are paused.')
        else:
            calls = db.execute("SELECT COALESCE(SUM(units),0) FROM cloud_reservations WHERE service!='bedrock'").fetchone()[0]
            if calls+units>1000:
                raise ValueError('Atmos AWS data-service call limit reached.')
        db.execute('INSERT INTO cloud_reservations VALUES (?,?,?,?)',(utcnow(),service,amount,units))

def inference_reservation(input_bytes,max_output=512):
    input_rate = float(os.getenv('ATMOS_BEDROCK_INPUT_USD_PER_MILLION','0'))
    output_rate = float(os.getenv('ATMOS_BEDROCK_OUTPUT_USD_PER_MILLION','0'))
    if not math.isfinite(input_rate) or not math.isfinite(output_rate) or input_rate<=0 or output_rate<=0:
        raise ValueError('Verify this model/region pricing and set the Bedrock per-million input/output rates before paid inference.')
    if input_bytes<0 or input_bytes>50000 or max_output<1 or max_output>512:
        raise ValueError('Atmos Bedrock request limit: 50 KB text/tool input and 512 output tokens.')
    # Byte-based overestimate plus formatting allowance; do not refund failed calls.
    estimated_input = math.ceil(input_bytes*1.25)+2048
    return (estimated_input*input_rate+max_output*output_rate)/1000000

def status():
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS cloud_reservations (time TEXT,service TEXT,usd REAL,units INTEGER)')
        rows = db.execute('SELECT service,SUM(usd) AS reserved_usd,SUM(units) AS calls FROM cloud_reservations GROUP BY service').fetchall()
    return {'user_allowance_usd':25,'bedrock_reservation_ceiling_usd':min(5,float(os.getenv('ATMOS_BEDROCK_RESERVATION_LIMIT_USD','5'))),
        'max_bedrock_calls':100,'max_data_service_calls':1000,'reservations':[dict(row) for row in rows],
        'note':'Application reservations/call limits are not an account-wide billing cap. Storage, taxes, other applications and changed pricing are outside this ledger.'}
