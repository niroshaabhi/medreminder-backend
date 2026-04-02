# backend/routes/notifications.py
from flask import Blueprint, request, jsonify
from firebase_config import send_fcm_notification, send_fcm_to_topic

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/push', methods=['POST'])
def send_push():
    """Send FCM push notification to a device"""
    data  = request.get_json()
    token = data.get('token')
    title = data.get('title', '💊 MedRemind')
    body  = data.get('body', 'Time to take your medicine!')
    extra = data.get('data', {})

    if not token:
        return jsonify({'error': 'FCM token required'}), 400

    result = send_fcm_notification(token, title, body, extra)
    return jsonify(result)


@notifications_bp.route('/push-topic', methods=['POST'])
def send_push_topic():
    """Send FCM push notification to a topic (e.g. all caregivers of a patient)"""
    data  = request.get_json()
    topic = data.get('topic')
    title = data.get('title', '🚨 MedRemind Alert')
    body  = data.get('body', 'Your patient may have missed their medicine.')

    if not topic:
        return jsonify({'error': 'topic required'}), 400

    result = send_fcm_to_topic(topic, title, body)
    return jsonify(result)


@notifications_bp.route('/medicine-alarm', methods=['POST'])
def medicine_alarm():
    """
    Trigger a medicine alarm notification.
    Called by a scheduler when it's time for a medicine.
    """
    data   = request.get_json()
    uid    = data.get('uid')
    med    = data.get('medicine', {})
    token  = data.get('fcmToken')

    if not token:
        return jsonify({'error': 'fcmToken required'}), 400

    title = f"💊 Time for {med.get('name', 'your medicine')}!"
    body  = f"{med.get('dosage', 'Take as prescribed')} — Tap to confirm"

    result = send_fcm_notification(
        token, title, body,
        data={'uid': uid, 'medId': med.get('id', ''), 'action': 'reminder'}
    )
    return jsonify(result)
