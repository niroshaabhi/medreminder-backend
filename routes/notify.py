# backend/routes/notify.py
from flask import Blueprint, request, jsonify
from twilio.rest import Client
import os
from pywebpush import webpush, WebPushException
import json
notify_bp = Blueprint('notify', __name__)

TWILIO_SID   = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_FROM  = os.environ.get('TWILIO_PHONE')
TWILIO_WA    = os.environ.get('TWILIO_WHATSAPP_FROM')


def get_twilio_client():
    return Client(TWILIO_SID, TWILIO_TOKEN)


def send_whatsapp(to_phone, message):
    try:
        client = get_twilio_client()
        clean_phone = to_phone.replace(' ', '')
        client.messages.create(
            from_=TWILIO_WA,
            to=f'whatsapp:{clean_phone}',
            body=message
        )
        print(f'✅ WhatsApp sent to {clean_phone}')
    except Exception as e:
        print(f'❌ WhatsApp error: {e}')


def send_sms(to_phone, message):
    try:
        client = get_twilio_client()
        clean_phone = to_phone.replace(' ', '')
        client.messages.create(
            from_=TWILIO_FROM,
            to=clean_phone,
            body=message
        )
        print(f'✅ SMS sent to {clean_phone}')
    except Exception as e:
        print(f'❌ SMS error: {e}')


@notify_bp.route('/missed', methods=['POST'])
def notify_missed():
    """Called when patient clicks Skip or Later"""
    data         = request.get_json()
    caregivers   = data.get('caregivers', [])
    patient_name = data.get('patientName', 'Your patient')
    med_name     = data.get('medicineName', 'a medicine')
    action       = data.get('action', 'skip')

    if action == 'later':
        message = (
            f"⏰ MedRemind Alert\n"
            f"{patient_name} has snoozed their medicine: {med_name}.\n"
            f"Reminder set for 30 minutes."
        )
    else:
        message = (
            f"🚨 MedRemind Alert\n"
            f"{patient_name} has skipped their medicine: {med_name}.\n"
            f"Please check on them."
        )

    for cg in caregivers:
        phone    = cg.get('phone', '')
        channels = cg.get('channel', [])
        if not phone:
            continue
        if 'WhatsApp' in channels:
            send_whatsapp(phone, message)
        if 'SMS' in channels:
            send_sms(phone, message)

    return jsonify({'success': True, 'notified': len(caregivers)})


@notify_bp.route('/taken', methods=['POST'])
def notify_taken():
    """Called when patient clicks Taken"""
    data         = request.get_json()
    caregivers   = data.get('caregivers', [])
    patient_name = data.get('patientName', 'Your patient')
    med_name     = data.get('medicineName', 'a medicine')

    message = (
        f"✅ MedRemind Update\n"
        f"{patient_name} has taken their medicine: {med_name}.\n"
        f"All good!"
    )

    for cg in caregivers:
        phone    = cg.get('phone', '')
        channels = cg.get('channel', [])
        if not phone:
            continue
        if 'WhatsApp' in channels:
            send_whatsapp(phone, message)
        if 'SMS' in channels:
            send_sms(phone, message)

    return jsonify({'success': True, 'notified': len(caregivers)})


@notify_bp.route('/test', methods=['POST'])
def notify_test():
    """Called when Send Test Alert button is clicked"""
    data         = request.get_json()
    caregivers   = data.get('caregivers', [])
    patient_name = data.get('patientName', 'Your patient')

    message = (
        f"👋 MedRemind Test Alert\n"
        f"Hi! This is a test notification for {patient_name}.\n"
        f"You are successfully set up as a caregiver."
    )

    for cg in caregivers:
        phone    = cg.get('phone', '')
        channels = cg.get('channel', [])
        if not phone:
            continue
        if 'WhatsApp' in channels:
            send_whatsapp(phone, message)
        if 'SMS' in channels:
            send_sms(phone, message)

    return jsonify({'success': True, 'notified': len(caregivers)})


@notify_bp.route('/skip-alert', methods=['POST'])
def skip_alert():
    data         = request.get_json()
    caregivers   = data.get('caregivers', [])
    patient_name = data.get('patientName', 'Patient')
    medicine     = data.get('medicineName', 'Medicine')
    skipped_at   = data.get('skippedAt', '')

    msg = (
        f"🚨 *MedRemind Alert*\n\n"
        f"⚠️ *{patient_name} skipped their medicine!*\n\n"
        f"💊 Medicine: *{medicine}*\n"
        f"🕐 Skipped at: {skipped_at}\n\n"
        f"Please check on them. 🙏"
    )

    notified = 0
    for cg in caregivers:
        phone = cg.get('phone', '').replace(' ', '').replace('-', '')
        if not phone:
            continue
        channels = cg.get('channel', [])
        if 'WhatsApp' in channels:
            send_whatsapp(phone, msg)
            notified += 1
        if 'SMS' in channels:
            send_sms(phone, msg)
            notified += 1

    return jsonify({'success': True, 'notified': notified})


# ✅ NEW — 30 min late reminder route
@notify_bp.route('/late-reminder', methods=['POST'])
def late_reminder():
    data         = request.get_json()
    caregivers   = data.get('caregivers', [])
    patient_name = data.get('patientName', 'Patient')
    medicine     = data.get('medicineName', 'Medicine')

    msg = (
        f"⏰ *MedRemind Follow-up*\n\n"
        f"🔴 *{patient_name} still hasn't taken their medicine!*\n\n"
        f"💊 Medicine: *{medicine}*\n"
        f"⚠️ It's been 30 minutes since they snoozed.\n\n"
        f"Please check on them urgently. 🙏"
    )

    notified = 0
    for cg in caregivers:
        phone = cg.get('phone', '').replace(' ', '').replace('-', '')
        if not phone:
            continue
        channels = cg.get('channel', [])
        if 'WhatsApp' in channels:
            send_whatsapp(phone, msg)
            notified += 1
        if 'SMS' in channels:
            send_sms(phone, msg)
            notified += 1

    return jsonify({'success': True, 'notified': notified})
from pywebpush import webpush, WebPushException
import json

VAPID_PUBLIC_KEY  = os.environ.get('VAPID_PUBLIC_KEY')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
VAPID_EMAIL       = "mailto:niroshaabhi2211@gmail.com"

# Store subscriptions in memory (simple approach)
push_subscriptions = {}

@notify_bp.route('/save-subscription', methods=['POST'])
def save_subscription():
    data         = request.get_json()
    user_id      = data.get('userId')
    subscription = data.get('subscription')
    if user_id and subscription:
        push_subscriptions[user_id] = subscription
        print(f'✅ Push subscription saved for {user_id}')
    return jsonify({'success': True})


@notify_bp.route('/push', methods=['POST'])
def send_push():
    data    = request.get_json()
    user_id = data.get('userId')
    title   = data.get('title', 'MedRemind Alert')
    body    = data.get('body', 'Time to take your medicine!')

    subscription = push_subscriptions.get(user_id)
    if not subscription:
        return jsonify({'error': 'No subscription found'}), 404

    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps({'title': title, 'body': body}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_EMAIL}
        )
        return jsonify({'success': True})
    except WebPushException as e:
        return jsonify({'error': str(e)}), 500