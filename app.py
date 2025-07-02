from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.utils import secure_filename
import os
import json
import datetime
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Set upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Journal file
JOURNAL_FILE = 'journal_entries.json'

# Load or initialize journal
if os.path.exists(JOURNAL_FILE):
    with open(JOURNAL_FILE, 'r') as f:
        journal_entries = json.load(f)
else:
    journal_entries = {}

# Dummy user database
users = {"admin": "admin123", "user": "pass123"}

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return "User already exists"
        users[username] = password
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_entries = journal_entries.get(username, [])
    filtered_entries = user_entries

    if request.method == 'POST':
        instrument = request.form.get('instrument')
        pair = request.form.get('pair')
        direction = request.form.get('direction')
        entry = request.form.get('entry')
        stop_loss = request.form.get('stop_loss')
        take_profit = request.form.get('take_profit')
        risk = request.form.get('risk')
        expected_profit = request.form.get('expected_profit')
        decision = request.form.get('decision')
        result = request.form.get('result')
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # Handle file uploads
        pre_image = request.files.get('pre_image')
        post_image = request.files.get('post_image')
        pre_image_path = post_image_path = ""

        if pre_image and pre_image.filename:
            pre_filename = secure_filename(pre_image.filename)
            pre_image_path = os.path.join(app.config['UPLOAD_FOLDER'], pre_filename)
            pre_image.save(pre_image_path)

        if post_image and post_image.filename:
            post_filename = secure_filename(post_image.filename)
            post_image_path = os.path.join(app.config['UPLOAD_FOLDER'], post_filename)
            post_image.save(post_image_path)

        entry_data = {
            "date": date,
            "instrument": instrument,
            "pair": pair,
            "direction": direction,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk": risk,
            "expected_profit": expected_profit,
            "pre_image": pre_image_path,
            "decision": decision,
            "result": result,
            "post_image": post_image_path
        }

        journal_entries.setdefault(username, []).insert(0, entry_data)

        with open(JOURNAL_FILE, 'w') as f:
            json.dump(journal_entries, f)

        return redirect(url_for('dashboard'))

    # Filter
    filter_status = request.args.get('filter')
    if filter_status == 'complete':
        filtered_entries = [e for e in user_entries if e.get('result') in ['Win', 'Lose']]
    elif filter_status == 'incomplete':
        filtered_entries = [e for e in user_entries if not e.get('result') or e['result'] == '--']

    return render_template('dashboard.html', entries=filtered_entries)

@app.route('/calculate', methods=['POST'])
def calculate():
    entry = float(request.form.get('entry'))
    stop_loss = float(request.form.get('stop_loss'))
    take_profit = float(request.form.get('take_profit'))
    risk = float(request.form.get('risk'))
    direction = request.form.get('direction')
    instrument = request.form.get('instrument')

    pip_value = 10  # fixed pip value for 1 lot

    if direction == 'Buy':
        stop_diff = abs(entry - stop_loss)
        tp_diff = abs(take_profit - entry)
    else:
        stop_diff = abs(stop_loss - entry)
        tp_diff = abs(entry - take_profit)

    lot_size = round(risk / (stop_diff * pip_value), 2) if stop_diff != 0 else 0
    expected_profit = round(tp_diff * pip_value * lot_size, 2)

    return {
        'lot_size': lot_size,
        'expected_profit': expected_profit
    }

@app.route('/export_pdf')
def export_pdf():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_entries = journal_entries.get(username, [])

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Lot Size Trade Journal", ln=True, align='C')

    for entry in user_entries:
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Date: {entry['date']} | Pair: {entry['pair']} | Direction: {entry['direction']}", ln=True)
        pdf.cell(200, 10, txt=f"Entry: {entry['entry']} | SL: {entry['stop_loss']} | TP: {entry['take_profit']}", ln=True)
        pdf.cell(200, 10, txt=f"Risk: {entry['risk']} | Expected Profit: {entry['expected_profit']} | Result: {entry['result']}", ln=True)
        pdf.cell(200, 10, txt=f"Decision: {entry['decision']}", ln=True)

    export_path = 'journal_export.pdf'
    pdf.output(export_path)

    return send_file(export_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
