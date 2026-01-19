from flask import Flask, request, jsonify, send_from_directory
import os
import csv
import json
from datetime import datetime
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
VERSIONS_FILE = os.path.join(BASE_DIR, "versions.json")

os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

def load_versions():
    if not os.path.exists(VERSIONS_FILE):
        return []
    with open(VERSIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_versions(versions):
    with open(VERSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)

def parse_csv(filepath):
    """Parse CSV into dict mapping test_case -> float value.
    Expected CSV columns: test_case,value (header optional)."""
    results = {}
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        headers = None
        first = next(reader, None)
        if first is None:
            return results
        # detect header
        if len(first) >= 2 and (first[0].lower() == 'test_case' or first[1].lower() == 'value'):
            headers = first
        else:
            # first row is data
            try:
                key = first[0]
                val = float(first[1])
                results[key] = val
            except Exception:
                pass
        for row in reader:
            if not row:
                continue
            try:
                key = row[0]
                val = float(row[1])
                results[key] = val
            except Exception:
                continue
    return results

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'no file part'}), 400
    file = request.files['file']
    version = request.form.get('version') or request.headers.get('X-Version') or None
    if not version:
        return jsonify({'error': 'version is required (form field `version`)'}), 400
    if file.filename == '':
        return jsonify({'error': 'no selected file'}), 400
    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    stored_name = f"{version}_{timestamp}_{filename}"
    path = os.path.join(DATA_DIR, stored_name)
    file.save(path)
    parsed = parse_csv(path)
    versions = load_versions()
    versions.append({
        'version': version,
        'filename': stored_name,
        'uploaded_at': datetime.utcnow().isoformat() + 'Z',
        'summary_count': len(parsed)
    })
    save_versions(versions)
    return jsonify({'ok': True, 'version': version, 'summary_count': len(parsed)})

@app.route('/api/versions', methods=['GET'])
def versions_list():
    versions = load_versions()
    return jsonify(versions)

@app.route('/api/compare', methods=['GET'])
def compare():
    v1 = request.args.get('v1')
    v2 = request.args.get('v2')
    if not v1 or not v2:
        return jsonify({'error': 'provide v1 and v2 query parameters'}), 400
    versions = load_versions()
    # find latest file for version name (match on version field)
    def find_file_for_version(v):
        for entry in reversed(versions):
            if entry.get('version') == v:
                return entry.get('filename')
        return None
    f1 = find_file_for_version(v1)
    f2 = find_file_for_version(v2)
    if not f1 or not f2:
        return jsonify({'error': 'one or both versions not found'}), 404
    p1 = parse_csv(os.path.join(DATA_DIR, f1))
    p2 = parse_csv(os.path.join(DATA_DIR, f2))
    # Prepare comparison where keys exist in either
    keys = sorted(set(p1.keys()) | set(p2.keys()))
    table = []
    labels = []
    data_v1 = []
    data_v2 = []
    for k in keys:
        val1 = p1.get(k)
        val2 = p2.get(k)
        delta = None
        pct = None
        if val1 is not None and val2 is not None:
            delta = val2 - val1
            try:
                pct = (delta / val1) * 100 if val1 != 0 else None
            except Exception:
                pct = None
        table.append({'test_case': k, 'v1': val1, 'v2': val2, 'delta': delta, 'pct_change': pct})
        labels.append(k)
        data_v1.append(val1 if val1 is not None else 0)
        data_v2.append(val2 if val2 is not None else 0)
    return jsonify({'table': table, 'chart': {'labels': labels, 'datasets': [
        {'label': v1, 'data': data_v1},
        {'label': v2, 'data': data_v2}
    ]}})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)