# backend/firebase_config.py
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\NIROSHA\Downloads\medreminder (1)\medreminder\backend\serviceAccountKey.json"
import firebase_admin
from firebase_admin import credentials, firestore, messaging
import os

_db = None

def init_firebase():
    global _db

    # ✅ FIXED: check if already initialized before calling initialize_app
    if not firebase_admin._apps:
        key_path = os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')

        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
        else:
            project_id = os.getenv('FIREBASE_PROJECT_ID', 'medreminder-demo')
            firebase_admin.initialize_app(options={'projectId': project_id})

        print("✅ Firebase connected")

    _db = firestore.client()
    return _db

def get_db():
    global _db
    if _db is None:
        init_firebase()
    return _db

def send_fcm_notification(token: str, title: str, body: str, data: dict = None):
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=token,
        )
        response = messaging.send(message)
        return {'success': True, 'message_id': response}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def send_fcm_to_topic(topic: str, title: str, body: str, data: dict = None):
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            topic=topic,
        )
        response = messaging.send(message)
        return {'success': True, 'message_id': response}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ✅ Initialize once on import
init_firebase()