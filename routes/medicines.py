# backend/routes/medicines.py
from flask import Blueprint, request, jsonify
from firebase_config import get_db
from datetime import datetime, timedelta
import uuid
import traceback

medicines_bp = Blueprint('medicines', __name__)


# ─────────────────────────────────────────────
# GET  /api/medicines/<uid>
# ─────────────────────────────────────────────
@medicines_bp.route('/<uid>', methods=['GET'])
def get_medicines(uid):
    """Return all medicines for a patient."""
    try:
        db   = get_db()
        docs = (
            db.collection('users')
              .document(uid)
              .collection('medicines')
              .stream()
        )
        meds = [{'id': d.id, **d.to_dict()} for d in docs]
        return jsonify({'success': True, 'medicines': meds})
    except Exception as e:
        print(f'[get_medicines] ERROR: {e}')
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# POST  /api/medicines/<uid>
# ─────────────────────────────────────────────
@medicines_bp.route('/<uid>', methods=['POST'])
def add_medicine(uid):
    try:
        data = request.get_json(force=True)

        required = ['name', 'dosage', 'freq', 'condition', 'mode', 'times']
        missing  = [f for f in required if f not in data]
        if missing:
            return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400

        if data['mode'] not in ('flex', 'strict'):
            return jsonify({'error': 'mode must be "flex" or "strict"'}), 400

        db  = get_db()
        med = {
            'id':           str(uuid.uuid4()),
            'name':         data['name'].strip(),
            'dosage':       data['dosage'].strip(),
            'freq':         data['freq'],
            'condition':    data['condition'],
            'mode':         data['mode'],
            'times':        data['times'],
            'active':       True,
            'adherenceLog': [],
            'createdAt':    datetime.utcnow().isoformat(),
        }

        (
            db.collection('users')
              .document(uid)
              .collection('medicines')
              .document(med['id'])
              .set(med)
        )

        return jsonify({'success': True, 'medicine': med}), 201

    except Exception as e:
        print(f'[add_medicine] ERROR: {e}')
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# GET  /api/medicines/<uid>/adherence
# ✅ FIXED: moved ABOVE /<uid>/<med_id> routes
#    to prevent Flask route conflict
# ─────────────────────────────────────────────
@medicines_bp.route('/<uid>/adherence', methods=['GET'])
def get_adherence(uid):
    try:
        days  = int(request.args.get('days', 7))
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()

        db   = get_db()
        docs = (
            db.collection('users')
              .document(uid)
              .collection('medicines')
              .stream()
        )

        total_doses   = 0
        taken_doses   = 0
        skipped_doses = 0
        by_medicine   = []

        for doc in docs:
            med      = doc.to_dict()
            log      = med.get('adherenceLog', [])
            windowed = [e for e in log if e.get('timestamp', '') >= since]

            m_total   = len(windowed)
            m_taken   = sum(1 for e in windowed if e.get('action') == 'taken')
            m_skipped = sum(1 for e in windowed if e.get('action') == 'skip')

            total_doses   += m_total
            taken_doses   += m_taken
            skipped_doses += m_skipped

            by_medicine.append({
                'id':        doc.id,
                'name':      med.get('name'),
                'total':     m_total,
                'taken':     m_taken,
                'skipped':   m_skipped,
                'adherence': round(m_taken / m_total * 100) if m_total else 0,
            })

        overall = round(taken_doses / total_doses * 100) if total_doses else 0

        return jsonify({
            'success':    True,
            'adherence':  overall,
            'taken':      taken_doses,
            'skipped':    skipped_doses,
            'total':      total_doses,
            'days':       days,
            'byMedicine': by_medicine,
        })

    except Exception as e:
        print(f'[get_adherence] ERROR: {e}')
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# POST  /api/medicines/<uid>/<med_id>/confirm
# ✅ FIXED: moved ABOVE /<uid>/<med_id> PUT/DELETE
# ─────────────────────────────────────────────
@medicines_bp.route('/<uid>/<med_id>/confirm', methods=['POST'])
def confirm_dose(uid, med_id):
    try:
        data   = request.get_json(force=True)
        action = data.get('action', 'taken')

        if action not in ('taken', 'skip', 'later'):
            return jsonify({'error': 'action must be taken | skip | later'}), 400

        db      = get_db()
        med_ref = (
            db.collection('users')
              .document(uid)
              .collection('medicines')
              .document(med_id)
        )
        med_doc = med_ref.get()
        if not med_doc.exists:
            return jsonify({'error': 'Medicine not found'}), 404

        log_entry = {
            'timestamp':     datetime.utcnow().isoformat(),
            'action':        action,
            'scheduledTime': data.get('scheduledTime', ''),
        }

        med_data    = med_doc.to_dict()
        current_log = med_data.get('adherenceLog', [])
        current_log.append(log_entry)

        update_payload = {'adherenceLog': current_log}

        if med_data.get('mode') == 'flex' and action == 'taken':
            actual_time = datetime.utcnow().strftime('%H:%M')
            update_payload['times'] = _nudge_times(
                scheduled_times=med_data.get('times', []),
                scheduled_slot=data.get('scheduledTime', ''),
                actual_time=actual_time,
            )

        med_ref.update(update_payload)

        if action == 'skip':
            _notify_caregivers_missed(uid, med_id)

        return jsonify({'success': True, 'action': action})

    except Exception as e:
        print(f'[confirm_dose] ERROR: {e}')
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# PUT  /api/medicines/<uid>/<med_id>
# ─────────────────────────────────────────────
@medicines_bp.route('/<uid>/<med_id>', methods=['PUT'])
def update_medicine(uid, med_id):
    try:
        data = request.get_json(force=True)

        for protected in ('id', 'adherenceLog', 'createdAt'):
            data.pop(protected, None)

        data['updatedAt'] = datetime.utcnow().isoformat()

        db  = get_db()
        ref = (
            db.collection('users')
              .document(uid)
              .collection('medicines')
              .document(med_id)
        )
        if not ref.get().exists:
            return jsonify({'error': 'Medicine not found'}), 404

        ref.update(data)
        return jsonify({'success': True})

    except Exception as e:
        print(f'[update_medicine] ERROR: {e}')
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# DELETE  /api/medicines/<uid>/<med_id>
# ─────────────────────────────────────────────
@medicines_bp.route('/<uid>/<med_id>', methods=['DELETE'])
def delete_medicine(uid, med_id):
    try:
        db  = get_db()
        ref = (
            db.collection('users')
              .document(uid)
              .collection('medicines')
              .document(med_id)
        )
        if not ref.get().exists:
            return jsonify({'error': 'Medicine not found'}), 404

        ref.delete()
        return jsonify({'success': True})

    except Exception as e:
        print(f'[delete_medicine] ERROR: {e}')
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────
def _nudge_times(scheduled_times, scheduled_slot, actual_time, alpha=0.2):
    if not scheduled_slot or not actual_time:
        return scheduled_times

    def to_minutes(t):
        h, m = map(int, t.split(':'))
        return h * 60 + m

    def to_hhmm(minutes):
        minutes = minutes % (24 * 60)
        return f'{minutes // 60:02d}:{minutes % 60:02d}'

    sched_min  = to_minutes(scheduled_slot)
    actual_min = to_minutes(actual_time)
    nudged_min = round(sched_min + alpha * (actual_min - sched_min))
    nudged_str = to_hhmm(nudged_min)

    return [nudged_str if t == scheduled_slot else t for t in scheduled_times]


def _notify_caregivers_missed(uid, med_id):
    try:
        from utils.notifications import send_whatsapp, send_sms
        db       = get_db()
        user_doc = db.collection('users').document(uid).get()
        med_doc  = (
            db.collection('users')
              .document(uid)
              .collection('medicines')
              .document(med_id)
              .get()
        )
        if not user_doc.exists or not med_doc.exists:
            return

        user = user_doc.to_dict()
        med  = med_doc.to_dict()
        msg  = (
            f"⚠️ MedRemind Alert: "
            f"{user.get('name', 'Patient')} skipped "
            f"{med.get('name', 'a medicine')}. "
            f"Please check on them."
        )

        caregivers = (
            db.collection('users')
              .document(uid)
              .collection('caregivers')
              .stream()
        )
        for cg_doc in caregivers:
            cg       = cg_doc.to_dict()
            channels = cg.get('channel', [])
            if 'WhatsApp' in channels:
                send_whatsapp(cg['phone'], msg)
            if 'SMS' in channels:
                send_sms(cg['phone'], msg)

    except Exception as e:
        print(f'[caregiver notify] error: {e}')