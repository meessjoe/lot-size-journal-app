from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
import os
from math import fabs

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journal_entries.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pair = db.Column(db.String(20))
    direction = db.Column(db.String(10))
    entry_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    risk_amount = db.Column(db.Float)
    expected_profit = db.Column(db.Float)
    result = db.Column(db.String(10))
    observation = db.Column(db.String(300))

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    lot_size = None
    if request.method == 'POST':
        entry_price = float(request.form['entry_price'])
        stop_loss = float(request.form['stop_loss'])
        risk_amount = float(request.form['risk_amount'])

        pip_difference = fabs(entry_price - stop_loss)
        pip_value = 10  # $10 per pip for 1 standard lot
        lot_size = round(risk_amount / (pip_difference * pip_value), 2)

        new_entry = JournalEntry(
            user_id=session['user_id'],
            pair=request.form['pair'],
            direction=request.form['direction'],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=float(request.form['take_profit']),
            risk_amount=risk_amount,
            expected_profit=round((float(request.form['take_profit']) - entry_price) * lot_size * pip_value, 2)
                if request.form['direction'] == 'BUY'
                else round((entry_price - float(request.form['take_profit'])) * lot_size * pip_value, 2),
            result=request.form.get('result'),
            observation=request.form.get('observation')
        )
        db.session.add(new_entry)
        db.session.commit()

    filter_option = request.args.get('filter', 'All')
    if filter_option == 'Complete':
        entries = JournalEntry.query.filter_by(user_id=session['user_id']).filter(JournalEntry.result != '').all()
    elif filter_option == 'Incomplete':
        entries = JournalEntry.query.filter_by(user_id=session['user_id']).filter(JournalEntry.result == '').all()
    else:
        entries = JournalEntry.query.filter_by(user_id=session['user_id']).all()

    return render_template('dashboard.html', entries=entries, lot_size=lot_size, current_filter=filter_option)

@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)

    if request.method == 'POST':
        entry.pair = request.form['pair']
        entry.direction = request.form['direction']
        entry.entry_price = float(request.form['entry_price'])
        entry.stop_loss = float(request.form['stop_loss'])
        entry.take_profit = float(request.form['take_profit'])
        entry.risk_amount = float(request.form['risk_amount'])
        entry.expected_profit = float(request.form['expected_profit'])
        entry.result = request.form.get('result')
        entry.observation = request.form.get('observation')

        db.session.commit()
        return redirect(url_for('index'))

    return render_template('edit.html', entry=entry)

@app.route('/delete/<int:entry_id>')
def delete_entry(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/export_pdf')
def export_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    entries = JournalEntry.query.filter_by(user_id=session['user_id']).all()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for entry in entries:
        txt = (
            f"Pair: {entry.pair} | Direction: {entry.direction} | Entry: {entry.entry_price} | SL: {entry.stop_loss} | TP: {entry.take_profit}\n"
            f"Risk: {entry.risk_amount} | Expected Profit: {entry.expected_profit} | Result: {entry.result or 'N/A'}\n"
            f"Observation: {entry.observation or ''}\n\n"
        )
        pdf.multi_cell(0, 10, txt)

    filename = "journal_export.pdf"
    pdf.output(filename)
    return send_file(filename, as_attachment=True)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return "Username already exists"
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Run App ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
,