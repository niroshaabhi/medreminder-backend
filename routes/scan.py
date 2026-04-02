# backend/routes/scan.py
from flask import Blueprint, request, jsonify
from groq import Groq
import base64
import json
import os
import re

scan_bp = Blueprint('scan', __name__)
client  = Groq(api_key=os.getenv('GROQ_API_KEY'))

TIMES_MAP = {
    'Once daily':        ['08:00'],
    'Twice daily':       ['08:00', '20:00'],
    'Three times daily': ['08:00', '14:00', '20:00'],
    'As needed':         ['08:00'],
}

FREQ_MAP = {
    'once':        'Once daily',
    'twice':       'Twice daily',
    'two times':   'Twice daily',
    'bd':          'Twice daily',
    'bid':         'Twice daily',
    'three times': 'Three times daily',
    'tid':         'Three times daily',
    'tds':         'Three times daily',
    'as needed':   'As needed',
    'sos':         'As needed',
    'prn':         'As needed',
}

def normalise_freq(raw: str) -> str:
    if not raw:
        return 'Once daily'
    raw_lower = raw.lower()
    for key, val in FREQ_MAP.items():
        if key in raw_lower:
            return val
    return 'Once daily'


@scan_bp.route('/prescription', methods=['POST'])
def scan_prescription():
    if 'prescription' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file  = request.files['prescription']
    fname = file.filename.lower()

    if fname.endswith('.pdf'):
        return jsonify({
            'success':   True,
            'medicines': [],
            'message':   'PDF scanning not supported yet. Please upload JPG or PNG.'
        })

    try:
        image_bytes  = file.read()
        b64_image    = base64.b64encode(image_bytes).decode('utf-8')
        content_type = file.content_type or 'image/jpeg'
        if content_type not in ('image/jpeg', 'image/png', 'image/gif', 'image/webp'):
            content_type = 'image/jpeg'

        prompt = """You are a medical prescription reader.

Look at this prescription image and extract ONLY the medicine names written on it.

Ignore everything else: doctor name, patient name, date, hospital, address, diagnosis, signature.

Return ONLY raw JSON with no markdown, no explanation, no backticks:

{
  "medicines": [
    {
      "name":      "Medicine name with strength exactly as written e.g. Metformin 500mg",
      "dosage":    "Dosage instructions exactly as written e.g. 1 tablet twice daily after meals",
      "freq":      "One of exactly: Once daily | Twice daily | Three times daily | As needed",
      "condition": "Best guess from: 🩸 Diabetes | ❤️ Hypertension | 🌬️ Asthma | 💓 Heart Disease | 🧠 Neurological | 🦴 Bone & Joint | 💊 Other",
      "mode":      "strict if it is insulin or blood pressure medicine, flex for everything else"
    }
  ]
}

If no medicine names are readable, return: {"medicines": []}
"""

        response = client.chat.completions.create(
            model    = 'meta-llama/llama-4-scout-17b-16e-instruct',
            messages = [
                {
                    'role':    'user',
                    'content': [
                        {
                            'type':      'image_url',
                            'image_url': {'url': f'data:{content_type};base64,{b64_image}'},
                        },
                        {
                            'type': 'text',
                            'text': prompt,
                        },
                    ],
                }
            ],
            max_tokens  = 1024,
            temperature = 0.1,
        )

        raw_text = response.choices[0].message.content.strip()
        raw_text = re.sub(r'^```(?:json)?', '', raw_text, flags=re.MULTILINE).strip()
        raw_text = re.sub(r'```$',          '', raw_text, flags=re.MULTILINE).strip()

        parsed    = json.loads(raw_text)
        medicines = parsed.get('medicines', [])

        result = []
        for m in medicines:
            if not m.get('name', '').strip():
                continue
            freq = normalise_freq(m.get('freq', ''))
            result.append({
                'name':      m.get('name',      '').strip(),
                'dosage':    m.get('dosage',    '').strip(),
                'freq':      freq,
                'condition': m.get('condition', '💊 Other').strip(),
                'mode':      m.get('mode',      'flex').strip(),
                'times':     TIMES_MAP.get(freq, ['08:00']),
            })

        return jsonify({
            'success':   True,
            'medicines': result,
            'count':     len(result),
        })

    except json.JSONDecodeError:
        return jsonify({'error': 'Could not parse prescription. Try a clearer image.'}), 422
    except Exception as e:
        print(f'[scan] error: {e}')
        return jsonify({'error': str(e)}), 500