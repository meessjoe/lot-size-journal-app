from flask import Flask, render_template, request, redirect, url_for, send_file
import os, json, uuid
from datetime import datetime
from fpdf import FPDF

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
JOURNAL_FILE = 'journal_entries.json'

def load_journal():
    if os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, 'r') as file:
            return json.load(file)
    return []

def save_journal(journal):
    with open(JOURNAL_FILE, 'w') as file:
        json.dump(journal, file, indent=2)

def calculate_lot_size(entry_price, sl_price, tp_price, risk_amount):
    pip_diff = abs(entry_price - sl_price)
    if pip_diff == 0:
        return 0, 0
    pip_value = 10
    lot_size = risk_amount / (pip_diff * pip_value)
    expected_profit = abs(tp_price - entry_price) * pip_value * lot_size
    return round(lot_size, 2), round(expected_profit, 2)

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    journal = load_journal()
    filter_val = request.args.get('filter', 'all')
    if filter_val == 'complete':
        journal = [j for j in journal if j.get('result')]
    elif filter_val == 'incomplete':
        journal = [j for j in journal if not j.get('result')]

    lot_size = expected_profit = None
    form_values = {
        'pair': '', 'entry': '', 'sl': '', 'tp': '', 'risk': ''
    }

    if request.method == 'POST':
        action = request.form.get('action')
        instrument = request.form['instrument']
        pair = request.form['pair']
        direction = request.form['direction']
        entry = float(request.form['entry'])
        sl = float(request.form['sl'])
        tp = float(request.form['tp'])
        risk = float(request.form['risk'])
        pre_image = request.files.get('pre_image')

        form_values.update({
            'pair': pair, 'entry': entry, 'sl': sl,
            'tp': tp, 'risk': risk
        })

        lot_size, expected_profit = calculate_lot_size(entry, sl, tp, risk)

        if action == 'save':
            filename = None
            if pre_image and pre_image.filename:
                ext = pre_image.filename.rsplit('.', 1)[-1]
                filename = f"{uuid.uuid4().hex}.{ext}"
                pre_image.save(os.path.join(UPLOAD_FOLDER, filename))

            new_entry = {
                'id': uuid.uuid4().hex,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'instrument': instrument,
                'pair': pair,
                'direction': direction,
                'entry': entry,
                'sl': sl,
                'tp': tp,
                'risk': risk,
                'lot_size': lot_size,
                'expected_profit': expected_profit,
                'pre_image': filename,
                'result': '',
                'observation': '',
                'post_image': ''
            }
            journal.insert(0, new_entry)
            save_journal(journal)
            return redirect(url_for('dashboard'))

    return render_template('dashboard.html', journal=journal, lot_size=lot_size,
                           expected_profit=expected_profit, **form_values)

@app.route('/edit/<entry_id>', methods=['GET', 'POST'])
def edit(entry_id):
    journal = load_journal()
    entry = next((e for e in journal if e['id'] == entry_id), None)
    if not entry:
        return "Entry not found", 404

    if request.method == 'POST':
        entry['result'] = request.form['result']
        entry['observation'] = request.form['observation']
        post_image = request.files.get('post_image')
        if post_image and post_image.filename:
            ext = post_image.filename.rsplit('.', 1)[-1]
            filename = f"{uuid.uuid4().hex}.{ext}"
            post_image.save(os.path.join(UPLOAD_FOLDER, filename))
            entry['post_image'] = filename
        save_journal(journal)
        return redirect(url_for('dashboard'))

    return render_template('edit.html', entry=entry)

@app.route('/delete/<entry_id>')
def delete(entry_id):
    journal = load_journal()
    journal = [e for e in journal if e['id'] != entry_id]
    save_journal(journal)
    return redirect(url_for('dashboard'))

@app.route('/export/pdf')
def export_pdf():
    journal = load_journal()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for entry in journal:
        pdf.cell(200, 10, txt=f"Date: {entry['date']}", ln=True)
        pdf.cell(200, 10, txt=f"Instrument: {entry['instrument']}  Pair: {entry['pair']}  Direction: {entry['direction']}", ln=True)
        pdf.cell(200, 10, txt=f"Entry: {entry['entry']}  SL: {entry['sl']}  TP: {entry['tp']}  Risk: {entry['risk']}", ln=True)
        pdf.cell(200, 10, txt=f"Lot Size: {entry['lot_size']}  Expected Profit: {entry['expected_profit']}", ln=True)
        if entry.get('result'):
            pdf.cell(200, 10, txt=f"Result: {entry['result']}  Observation: {entry.get('observation', '')}", ln=True)
        pdf.ln(5)

    output_path = "journal_export.pdf"
    pdf.output(output_path)
    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

