# backend/routes/reminders.py
from flask import Blueprint, request, jsonify
from firebase_config import get_db
from models.habit_model import HabitModel
from datetime import datetime, timedelta
import threading

reminders_bp = Blueprint('reminders', __name__)
habit_model  = HabitModel()

# In-memory store for active reminder threads (use Redis in production)
_active_reminders = {}


@reminders_bp.route('/<uid>', methods=['GET'])
def get_reminders(uid):
    """Get all reminders for today"""
    try:
        db   = get_db()
        docs = db.collection('users').document(uid).collection('medicines').stream()
        today = datetime.now()
        reminders = []

        for doc in docs:
            med = doc.to_dict()
            if not med.get('active', True):
                continue
            for t in med.get('times', []):
                reminders.append({
                    'medId':     doc.id,
                    'medName':   med['name'],
                    'time':      t,
                    'mode':      med.get('mode', 'flex'),
                    'condition': med.get('condition', ''),
                    'dosage':    med.get('dosage', ''),
                })

        # Sort by time
        reminders.sort(key=lambda r: r['time'])
        return jsonify({'success': True, 'reminders': reminders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reminders_bp.route('/adjust-time', methods=['POST'])
def adjust_reminder_time():
    """
    AI Smart Mode: adjust reminder time based on patient habit.
    Only applies to 'flex' mode medicines.
    """
    data   = request.get_json()
    uid    = data.get('uid')
    med_id = data.get('medId')

    if not uid or not med_id:
        return jsonify({'error': 'uid and medId required'}), 400

    try:
        db      = get_db()
        med_ref = db.collection('users').document(uid).collection('medicines').document(med_id)
        med_doc = med_ref.get()

        if not med_doc.exists:
            return jsonify({'error': 'Medicine not found'}), 404

        med = med_doc.to_dict()

        # Only adjust flexible mode medicines
        if med.get('mode') != 'flex':
            return jsonify({'success': True, 'adjusted': False, 'reason': 'Strict mode — time unchanged'})

        log         = med.get('adherenceLog', [])
        old_times   = med.get('times', [])
        new_times   = []

        for scheduled_time in old_times:
            suggested = habit_model.predict_best_time(scheduled_time, log)
            new_times.append(suggested)

        if new_times != old_times:
            med_ref.update({'times': new_times})
            return jsonify({'success': True, 'adjusted': True, 'oldTimes': old_times, 'newTimes': new_times})

        return jsonify({'success': True, 'adjusted': False, 'reason': 'Times are already optimal'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reminders_bp.route('/missed', methods=['POST'])
def handle_missed():
    """
    Called when a patient does not confirm within the alert window.
    Sends caregiver notifications.
    """
    data   = request.get_json()
    uid    = data.get('uid')
    med_id = data.get('medId')

    try:
        from utils.notifications import send_whatsapp, send_sms
        db       = get_db()
        user_doc = db.collection('users').document(uid).get()
        med_doc  = db.collection('users').document(uid).collection('medicines').document(med_id).get()

        if not user_doc.exists or not med_doc.exists:
            return jsonify({'error': 'User or medicine not found'}), 404

        user = user_doc.to_dict()
        med  = med_doc.to_dict()
        msg  = (
            f"🚨 MedRemind Alert!\n"
            f"{user.get('name', 'Your patient')} has NOT taken "
            f"{med.get('name', 'their medicine')}.\n"
            f"Please check on them immediately."
        )

        cg_docs = db.collection('users').document(uid).collection('caregivers').stream()
        notified = 0
        for cg_doc in cg_docs:
            cg = cg_doc.to_dict()
            if 'WhatsApp' in cg.get('channel', []):
                send_whatsapp(cg['phone'], msg)
                notified += 1
            if 'SMS' in cg.get('channel', []):
                send_sms(cg['phone'], msg)
                notified += 1

        # Log missed event
        db.collection('users').document(uid).collection('missedDoses').add({
            'medId':     med_id,
            'medName':   med.get('name'),
            'timestamp': datetime.utcnow().isoformat(),
            'notified':  notified,
        })

        return jsonify({'success': True, 'caregiversNotified': notified})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
