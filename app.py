import os
import json
import base64
import firebase_admin
from firebase_admin import credentials
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Firebase initialization
creds_base64 = os.environ.get("FIREBASE_CREDENTIALS")
if creds_base64:
    creds_json = json.loads(base64.b64decode(creds_base64).decode("utf-8"))
    cred = credentials.Certificate(creds_json)
else:
    cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred)

# Flask app
app = Flask(__name__)
CORS(app, origins=["https://medreminder-frontend2-64ut.vercel.app"])

# Register blueprints
from routes.auth import auth_bp
from routes.caregivers import caregivers_bp
from routes.medicines import medicines_bp
from routes.notifications import notifications_bp
from routes.notify import notify_bp
from routes.reminders import reminders_bp
from routes.scan import scan_bp

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(caregivers_bp, url_prefix="/caregivers")
app.register_blueprint(medicines_bp, url_prefix="/medicines")
app.register_blueprint(notifications_bp, url_prefix="/notifications")
app.register_blueprint(notify_bp, url_prefix="/notify")
app.register_blueprint(reminders_bp, url_prefix="/reminders")
app.register_blueprint(scan_bp, url_prefix="/scan")

@app.route("/")
def home():
    return {"status": "MedReminder Backend is running! ✅"}

# ✅ Keep-alive ping route
@app.route("/ping")
def ping():
    return {"status": "awake"}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)