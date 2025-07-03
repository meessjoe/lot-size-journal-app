from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.utils import secure_filename
from fpdf import FPDF
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret_key'

# Constants
USERS_FILE = 'users.json'
UPLOAD_FOLDER = 'uploads'
JOURNAL_FOLDER = 'journals'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(JOURNAL_FOLDER, exist_ok=True)

# Helpers
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def get_journal_file(username):
    return os.path.join(JOURNAL_FOLDER, f'{username}_journal.json')

def load_journal(username):
    path = get_journal_file(username)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return []

def save_journal(username, journal):
    with open(get_journal_file(username), 'w') as f:
        json.dump(journal, f, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    journal = load_journal(session['username'])
    filter_type = request.args.get('filter')
    if filter_type == 'complete':
        journal = [j for j in journal if j.get('result')]
    elif filter_type == 'incomplete':
        journal = [j for j in journal if not j.get('result')]
    return render_template('index.html', journal=journal)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid credentials.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return render_template('register.html', error='Username already exists.')
        users[username] = password
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/calculate', methods=['POST'])
def calculate():
    entry_price = float(request.form.get('entry_price', 0))
    stop_loss = float(request.form.get('stop_loss', 0))
    take_profit = float(request.form.get('take_profit', 0))
    risk_amount = float(request.form.get('risk_amount', 0))

    pip_difference = abs(entry_price - stop_loss)
    pip_value = 10  # $10 per pip per standard lot
    lot_size = risk_amount / (pip_difference * pip_value) if pip_difference else 0
    expected_profit = abs(take_profit - entry_price) * pip_value * lot_size

    return {
        'lot_size': round(lot_size, 2),
        'expected_profit': round(expected_profit, 2)
    }

@app.route('/save', methods=['POST'])
def save():
    if 'username' not in session:
        return redirect(url_for('login'))

    data = dict(request.form)
    data['date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    data['lot_size'] = request.form.get('lot_size')
    data['expected_profit'] = request.form.get('expected_profit')

    pre_image = request.files.get('pre_image')
    post_image = request.files.get('post_image')

    if pre_image and allowed_file(pre_image.filename):
        filename = secure_filename(pre_image.filename)
        pre_path = os.path.join(UPLOAD_FOLDER, filename)
        pre_image.save(pre_path)
        data['pre_image'] = pre_path

    if post_image and allowed_file(post_image.filename):
        filename = secure_filename(post_image.filename)
        post_path = os.path.join(UPLOAD_FOLDER, filename)
        post_image.save(post_path)
        data['post_image'] = post_path

    journal = load_journal(session['username'])
    journal.append(data)
    save_journal(session['username'], journal)

    return redirect(url_for('index'))

@app.route('/edit/<int:index>', methods=['POST'])
def edit(index):
    if 'username' not in session:
        return redirect(url_for('login'))

    journal = load_journal(session['username'])
    if index >= len(journal):
        return redirect(url_for('index'))

    journal[index]['result'] = request.form.get('result')
    journal[index]['observation'] = request.form.get('observation')

    post_image = request.files.get('post_image')
    if post_image and allowed_file(post_image.filename):
        filename = secure_filename(post_image.filename)
        post_path = os.path.join(UPLOAD_FOLDER, filename)
        post_image.save(post_path)
        journal[index]['post_image'] = post_path

    save_journal(session['username'], journal)
    return redirect(url_for('index'))

@app.route('/export_pdf')
def export_pdf():
    if 'username' not in session:
        return redirect(url_for('login'))

    journal = load_journal(session['username'])
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    for entry in journal:
        for k, v in entry.items():
            if 'image' not in k:
                pdf.cell(200, 10, txt=f"{k}: {v}", ln=True)
        pdf.ln(5)

    filepath = os.path.join(UPLOAD_FOLDER, f"{session['username']}_journal.pdf")
    pdf.output(filepath)
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
