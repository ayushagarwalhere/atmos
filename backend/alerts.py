import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
import httpx
from .storage import put, records, setting, utcnow
from .providers import identity

DEFAULT_RULE = {'enabled':False,'pm25_threshold':120,'minimum_transport_score':.65,'minimum_interval_coverage':.8,'cooldown_hours':24,'channel':'in_app'}

def check_alerts(snapshot, send=False):
    rule = setting('alert_rule',DEFAULT_RULE)
    if not rule['enabled']:
        return {'alerts':[],'reason':'Alert rule is disabled'}
    events = []
    for city in snapshot['cities']:
        forecast = city['forecast']
        reasons = []
        if forecast.get('pm25') is None or forecast['pm25']<rule['pm25_threshold']:
            reasons.append('severity below threshold or missing forecast')
        if (city.get('transport_score') or 0)<rule['minimum_transport_score']:
            reasons.append('transport score below threshold')
        if not forecast.get('model_validated') or (forecast.get('empirical_test_coverage') or 0)<rule['minimum_interval_coverage']:
            reasons.append('real model validation/interval coverage insufficient')
        if forecast.get('scenario'):
            reasons.append('scenario prediction cannot trigger notifications')
        if snapshot['mode']=='demo':
            reasons.append('synthetic demo; delivery disabled')
        if city.get('air_stale'):
            reasons.append('stale station reading')
        if reasons:
            events.append({'city_id':city['id'],'status':'suppressed','reasons':reasons})
            continue
        past = records('alerts','live',start=(datetime.fromisoformat(snapshot['time'])-timedelta(hours=rule['cooldown_hours'])).isoformat(),city_id=city['id'])
        if any(event.get('status') in ('eligible','sent') for event in past):
            continue
        event = {'id':identity(city['id'],snapshot['time'],rule['pm25_threshold']),'time':utcnow(),'city_id':city['id'],'source':'threshold rule',
            'status':'eligible','channel':rule['channel'], 'message':f"Atmos screening alert for {city['name']}: predicted PM2.5 {forecast['pm25']} µg/m³ at {forecast['target_time']}; interval {forecast['interval']}. Verify official station/advisory updates.", 'forecast':forecast}
        if send and os.getenv('ALERT_SEND_ENABLED','false').lower()=='true' and rule['channel']!='in_app':
            try:
                deliver(event)
                event['status']='sent'
            except Exception as exc:
                event['status']='delivery_failed'
                event['error']=type(exc).__name__
        put('alerts',[event],'live')
        events.append(event)
    return {'alerts':events,'rule':rule,'external_delivery_enabled':os.getenv('ALERT_SEND_ENABLED','false').lower()=='true'}

def deliver(event):
    if event['channel']=='telegram':
        token,chat = os.getenv('TELEGRAM_BOT_TOKEN'),os.getenv('TELEGRAM_CHAT_ID')
        if not token or not chat:
            raise ValueError('Telegram credentials missing')
        with httpx.Client(timeout=15) as client:
            response = client.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':event['message']})
            response.raise_for_status()
    elif event['channel']=='email':
        message = EmailMessage()
        message['Subject']='Atmos smoke outlook alert'
        message['From']=os.environ['ALERT_EMAIL_FROM']
        message['To']=os.environ['ALERT_EMAIL_TO']
        message.set_content(event['message'])
        with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=15) as smtp:
            smtp.starttls()
            smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
            smtp.send_message(message)
