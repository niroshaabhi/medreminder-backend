import os
import json
import base64
import firebase_admin
from firebase_admin import credentials

creds_base64 = os.environ.get("FIREBASE_CREDENTIALS")

if creds_base64:
    creds_json = json.loads(base64.b64decode(creds_base64).decode("utf-8"))
    cred = credentials.Certificate(creds_json)
else:
    cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred)