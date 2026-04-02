# backend/routes/auth.py
from flask import Blueprint, request, jsonify
from firebase_admin import auth as firebase_auth
from firebase_config import get_db
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """Verify Firebase ID token from frontend"""
    data  = request.get_json()
    token = data.get('idToken')
    if not token:
        return jsonify({'error': 'No token provided'}), 400
    try:
        decoded = firebase_auth.verify_id_token(token)
        uid = decoded['uid']
        db  = get_db()
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()
        if user_doc.exists:
            return jsonify({'success': True, 'user': user_doc.to_dict()})
        return jsonify({'success': True, 'user': {'uid': uid, 'email': decoded.get('email')}})
    except Exception as e:
        return jsonify({'error': str(e)}), 401


@auth_bp.route('/profile', methods=['POST'])
def create_profile():
    """Create or update patient profile in Firestore"""
    data = request.get_json()
    uid  = data.get('uid')
    if not uid:
        return jsonify({'error': 'uid required'}), 400
    try:
        db = get_db()
        profile = {
            'uid':        uid,
            'name':       data.get('name', ''),
            'email':      data.get('email', ''),
            'age':        data.get('age', ''),
            'gender':     data.get('gender', ''),
            'conditions': data.get('conditions', []),
            'fcmToken':   data.get('fcmToken', ''),
            'createdAt':  datetime.utcnow().isoformat(),
            'updatedAt':  datetime.utcnow().isoformat(),
        }
        db.collection('users').document(uid).set(profile, merge=True)
        return jsonify({'success': True, 'profile': profile})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/profile/<uid>', methods=['GET'])
def get_profile(uid):
    """Fetch patient profile"""
    try:
        db  = get_db()
        doc = db.collection('users').document(uid).get()
        if doc.exists:
            return jsonify({'success': True, 'profile': doc.to_dict()})
        return jsonify({'error': 'Profile not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/fcm-token', methods=['POST'])
def update_fcm_token():
    """Update FCM push notification token"""
    data = request.get_json()
    uid  = data.get('uid')
    token = data.get('fcmToken')
    if not uid or not token:
        return jsonify({'error': 'uid and fcmToken required'}), 400
    try:
        db = get_db()
        db.collection('users').document(uid).update({'fcmToken': token})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
