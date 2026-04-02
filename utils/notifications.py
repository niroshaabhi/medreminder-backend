# backend/utils/notifications.py
"""
WhatsApp & SMS notifications via Twilio
"""
import os
from twilio.rest import Client


def _get_client():
    sid   = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    if not sid or not token:
        print("⚠️  Twilio credentials not set. SMS/WhatsApp disabled.")
        return None
    return Client(sid, token)


def send_whatsapp(to_number: str, message: str) -> dict:
    """
    Send WhatsApp message via Twilio WhatsApp sandbox.
    Ensure 'to_number' is in format '+91XXXXXXXXXX'
    """
    client = _get_client()
    if not client:
        print(f"[DEMO] WhatsApp to {to_number}: {message}")
        return {'success': True, 'demo': True}
    try:
        from_whatsapp = os.getenv('TWILIO_WHATSAPP', 'whatsapp:+14155238886')
        msg = client.messages.create(
            body=message,
            from_=from_whatsapp,
            to=f'whatsapp:{to_number}'
        )
        return {'success': True, 'sid': msg.sid}
    except Exception as e:
        print(f"WhatsApp error: {e}")
        return {'success': False, 'error': str(e)}


def send_sms(to_number: str, message: str) -> dict:
    """Send SMS via Twilio"""
    client = _get_client()
    if not client:
        print(f"[DEMO] SMS to {to_number}: {message}")
        return {'success': True, 'demo': True}
    try:
        from_number = os.getenv('TWILIO_PHONE')
        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )
        return {'success': True, 'sid': msg.sid}
    except Exception as e:
        print(f"SMS error: {e}")
        return {'success': False, 'error': str(e)}
