from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from fpdf import FPDF
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(120))

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    instrument = db.Column(db.String(20))
    pair = db.Column(db.String(20))
    direction = db.Column(db.String(10))
    entry_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    risk_amount = db.Column(db.Float)
    expected_profit = db.Column(db.Float)
    result = db.Column(db.String(10))
    decision = db.Column(db.String(300))
    observation = db.Column(db.String(300))
    pre_chart = db.Column(db.String(120))
    post_chart = db.Column(db.String(120))

# --- Auth ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        confirm = request.form['confirm_password']
        if not request.form['password'] == confirm:
            flash('Passwords do not match.')
            return redirect(url_for('signup'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('signup'))
        db.session.add(User(username=username, password=password))
        db.session.commit()
        flash('Signup successful. Please login.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Main App ---
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    expected_profit = None

    if request.method == 'POST':
        entry_price = float(request.form['entry_price'])
        stop_loss = float(request.form['stop_loss'])
        take_profit = float(request.form['take_profit'])
        risk_amount = float(request.form['risk_amount'])

        pip_difference = abs(entry_price - stop_loss)
        lot_size = risk_amount / (pip_difference * 10)
        expected_profit = abs(take_profit - entry_price) * lot_size * 10

        pre_chart_file = request.files.get('pre_chart')
        post_chart_file = request.files.get('post_chart')

        pre_chart_filename = secure_filename(pre_chart_file.filename) if pre_chart_file and pre_chart_file.filename else None
        post_chart_filename = secure_filename(post_chart_file.filename) if post_chart_file and post_chart_file.filename else None

        if pre_chart_filename:
            pre_chart_path = os.path.join(app.config['UPLOAD_FOLDER'], pre_chart_filename)
            pre_chart_file.save(pre_chart_path)

        if post_chart_filename:
            post_chart_path = os.path.join(app.config['UPLOAD_FOLDER'], post_chart_filename)
            post_chart_file.save(post_chart_path)

        entry = Entry(
            user_id=user_id,
            instrument=request.form['instrument'],
            pair=request.form['pair'],
            direction=request.form['direction'],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=risk_amount,
            expected_profit=expected_profit,
            result=request.form.get('result'),
            decision=request.form.get('decision'),
            pre_chart=pre_chart_filename,
            post_chart=post_chart_filename
        )
        db.session.add(entry)
        db.session.commit()
        return redirect(url_for('dashboard'))

    filter_option = request.args.get('filter')
    if filter_option == 'complete':
        entries = Entry.query.filter_by(user_id=user_id).filter(Entry.result != None).order_by(Entry.timestamp.desc()).all()
    elif filter_option == 'incomplete':
        entries = Entry.query.filter_by(user_id=user_id).filter(Entry.result == None).order_by(Entry.timestamp.desc()).all()
    else:
        entries = Entry.query.filter_by(user_id=user_id).order_by(Entry.timestamp.desc()).all()

    return render_template('dashboard.html', entries=entries, expected_profit=expected_profit, filter=filter_option)

@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    if 'user_id' not in session or entry.user_id != session['user_id']:
        return redirect(url_for('login'))

    if request.method == 'POST':
        entry.result = request.form['result']
        entry.observation = request.form['observation']

        post_chart_file = request.files.get('post_chart')
        if post_chart_file and post_chart_file.filename:
            filename = secure_filename(post_chart_file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            post_chart_file.save(path)
            entry.post_chart = filename

        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('edit.html', entry=entry)

@app.route('/delete/<int:entry_id>')
def delete_entry(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    if 'user_id' not in session or entry.user_id != session['user_id']:
        return redirect(url_for('login'))
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/export_pdf')
def export_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    entries = Entry.query.filter_by(user_id=user_id).order_by(Entry.timestamp.desc()).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for entry in entries:
        pdf.multi_cell(0, 10, txt=(
            f"Date: {entry.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
            f"Pair: {entry.pair} | Direction: {entry.direction} | Entry: {entry.entry_price}\n"
            f"SL: {entry.stop_loss} | TP: {entry.take_profit} | Risk: {entry.risk_amount} | Profit: {entry.expected_profit}\n"
            f"Result: {entry.result or 'N/A'} | Observation: {entry.observation or ''}\n\n"
        ))

    filename = "journal_export.pdf"
    pdf.output(filename)
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
