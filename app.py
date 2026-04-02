from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
from pywebpush import webpush, WebPushException
import os
import json

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# ✅ VAPID Keys for Push Notifications
VAPID_PRIVATE_KEY = "LS0tLS1CRUdJTiBFQyBQUklWQVRFIEtFWS0tLS0tCk1IY0NBUUVFSU1ZYnNUT0srZThmRUVQb1dVYXYzL0V1QTg2UVQrMmhMV0p4N0V5Z28xUnZvQW9HQ0NxR1NNNDkKQXdFSG9VUURRZ0FFWkI1OTRUb1pxZUtCTlFpNzBpTGlBbWVyZWlkQm4xNGVOZTFCMkREMlQybW9LcVNHYnFwegpqSWc4Y2M0aithZEhhS0hFbXZLOFI3c0ZQbmZMM1ViUWhBPT0KLS0tLS1FTkQgRUMgUFJJVkFURSBLRVktLS0tLQo="
VAPID_PUBLIC_KEY  = "BGQefeE6GanigTUIu9Ii4gJnq3onQZ9eHjXtQdgw9k9pqCqkhm6qc4yIPHHOI_mnR2ihxJryvEe7BT53y91G0IQ="
VAPID_CLAIMS      = {"sub": "mailto:you@example.com"}

# ✅ Store push subscriptions
subscriptions = []

from routes.auth          import auth_bp
from routes.medicines     import medicines_bp
from routes.scan          import scan_bp
from routes.reminders     import reminders_bp
from routes.caregivers    import caregivers_bp
from routes.notifications import notifications_bp
from routes.notify        import notify_bp

app.register_blueprint(auth_bp,          url_prefix='/api/auth')
app.register_blueprint(medicines_bp,     url_prefix='/api/medicines')
app.register_blueprint(scan_bp,          url_prefix='/api/scan')
app.register_blueprint(reminders_bp,     url_prefix='/api/reminders')
app.register_blueprint(caregivers_bp,    url_prefix='/api/caregivers')
app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
app.register_blueprint(notify_bp,        url_prefix='/api/notify')

@app.route('/api/health')
def health():
    return {'status': 'ok', 'message': 'MedRemind API is running 💊'}

# ✅ Save push subscription from browser
@app.route('/api/save-subscription', methods=['POST'])
def save_subscription():
    sub = request.json
    if sub not in subscriptions:
        subscriptions.append(sub)
    return jsonify({"status": "saved"})

# ✅ Send push notification
@app.route('/api/send-reminder', methods=['POST'])
def send_reminder():
    medicine_name = request.json.get("medicine", "your medicine")
    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps({
                    "title": "Med Reminder 💊",
                    "body": f"Time to take {medicine_name}!"
                }),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as ex:
            print("Push error:", ex)
    return jsonify({"status": "sent"})

if __name__ == '__main__':
    print("💊 MedRemind API starting on http://localhost:5000")
    app.run(debug=True, port=5000)