from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pair = db.Column(db.String(50))
    direction = db.Column(db.String(10))
    entry_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    risk_amount = db.Column(db.Float)
    expected_profit = db.Column(db.Float)

# --- Routes ---
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            return 'User already exists'
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        entry = JournalEntry(
            user_id=session['user_id'],
            pair=request.form['pair'],
            direction=request.form['direction'],
            entry_price=request.form['entry_price'],
            stop_loss=request.form['stop_loss'],
            take_profit=request.form['take_profit'],
            risk_amount=request.form['risk_amount'],
            expected_profit=request.form['expected_profit']
        )
        db.session.add(entry)
        db.session.commit()

    entries = JournalEntry.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', entries=entries)

@app.route('/export')
def export_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    entries = JournalEntry.query.filter_by(user_id=session['user_id']).all()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for entry in entries:
        line = f"{entry.pair} | {entry.direction} | Entry: {entry.entry_price} | SL: {entry.stop_loss} | TP: {entry.take_profit} | Risk: {entry.risk_amount} | Profit: {entry.expected_profit}"
        pdf.cell(200, 10, txt=line, ln=True)

    filename = "journal_export.pdf"
    pdf.output(filename)
    return send_file(filename, as_attachment=True)

# --- Run App ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
