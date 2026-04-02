# backend/routes/caregivers.py
from flask import Blueprint, request, jsonify
from firebase_config import get_db
from datetime import datetime
import uuid

caregivers_bp = Blueprint('caregivers', __name__)


@caregivers_bp.route('/<uid>', methods=['GET'])
def get_caregivers(uid):
    """Get all caregivers for a patient"""
    try:
        db   = get_db()
        docs = db.collection('users').document(uid).collection('caregivers').stream()
        caregivers = [{'id': d.id, **d.to_dict()} for d in docs]
        return jsonify({'success': True, 'caregivers': caregivers})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@caregivers_bp.route('/<uid>', methods=['POST'])
def add_caregiver(uid):
    """Add a caregiver for a patient"""
    data = request.get_json()
    name  = data.get('name')
    phone = data.get('phone')
    if not name or not phone:
        return jsonify({'error': 'name and phone are required'}), 400
    try:
        db = get_db()
        cg = {
            'id':        str(uuid.uuid4()),
            'name':      name,
            'phone':     phone,
            'channel':   data.get('channel', ['WhatsApp', 'SMS']),
            'active':    True,
            'createdAt': datetime.utcnow().isoformat(),
        }
        db.collection('users').document(uid).collection('caregivers').document(cg['id']).set(cg)
        return jsonify({'success': True, 'caregiver': cg}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@caregivers_bp.route('/<uid>/<cg_id>', methods=['DELETE'])
def remove_caregiver(uid, cg_id):
    """Remove a caregiver"""
    try:
        db = get_db()
        db.collection('users').document(uid).collection('caregivers').document(cg_id).delete()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@caregivers_bp.route('/<uid>/notify-test', methods=['POST'])
def test_notify(uid):
    """Send a test notification to all caregivers"""
    try:
        from utils.notifications import send_whatsapp, send_sms
        db       = get_db()
        user_doc = db.collection('users').document(uid).get()
        user     = user_doc.to_dict() if user_doc.exists else {}
        msg      = (
            f"👋 MedRemind Test Alert\n"
            f"Hi! This is a test notification for {user.get('name', 'your patient')}. "
            f"You are successfully set up as a caregiver."
        )
        cg_docs  = db.collection('users').document(uid).collection('caregivers').stream()
        notified = 0
        for cg_doc in cg_docs:
            cg = cg_doc.to_dict()
            if cg.get('active', True):
                if 'WhatsApp' in cg.get('channel', []):
                    send_whatsapp(cg['phone'], msg)
                    notified += 1
                if 'SMS' in cg.get('channel', []):
                    send_sms(cg['phone'], msg)
                    notified += 1
        return jsonify({'success': True, 'notified': notified})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
