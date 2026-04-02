import os
import json
import tempfile
import firebase_admin
from firebase_admin import credentials, firestore, messaging

_db = None

def init_firebase():
    global _db

    if not firebase_admin._apps:
        creds_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')

        if creds_json:
            # Railway production
            creds_dict = json.loads(creds_json)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(creds_dict, f)
                temp_path = f.name
            cred = credentials.Certificate(temp_path)
        else:
            # Local Windows
            key_path = os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')
            cred = credentials.Certificate(key_path)

        firebase_admin.initialize_app(cred)
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

init_firebase()
