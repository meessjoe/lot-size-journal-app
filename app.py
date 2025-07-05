from flask import Flask, render_template, request, redirect, url_for
import os
import json
from datetime import datetime

app = Flask(__name__)
JOURNAL_FILE = "journal_entries.json"

# Load journal data
def load_journal():
    if not os.path.exists(JOURNAL_FILE):
        return []
    with open(JOURNAL_FILE, "r") as f:
        return json.load(f)

# Save journal data
def save_journal(entries):
    with open(JOURNAL_FILE, "w") as f:
        json.dump(entries, f, indent=4)

# Calculate lot size and expected profit
def calculate_lot_size(entry_price, stop_loss, risk_amount, take_profit):
    if entry_price and stop_loss and risk_amount:
        sl_diff = abs(float(entry_price) - float(stop_loss))
        pip_value_per_standard_lot = 10
        lot_size = round(float(risk_amount) / (sl_diff * pip_value_per_standard_lot), 2)
    else:
        lot_size = None

    if lot_size and take_profit:
        tp_diff = abs(float(take_profit) - float(entry_price))
        expected_profit = round(tp_diff * lot_size * 10, 2)
    else:
        expected_profit = None

    return lot_size, expected_profit

@app.route("/", methods=["GET"])
def index():
    filter_value = request.args.get("filter")
    journal = load_journal()
    if filter_value == "complete":
        journal = [entry for entry in journal if entry.get("result")]
    elif filter_value == "incomplete":
        journal = [entry for entry in journal if not entry.get("result")]
    return render_template("index.html", journal=journal)

@app.route("/calculate", methods=["POST"])
def calculate():
    form = request.form
    entry_price = form.get("entry_price")
    stop_loss = form.get("stop_loss")
    take_profit = form.get("take_profit")
    risk_amount = form.get("risk_amount")

    lot_size, expected_profit = calculate_lot_size(entry_price, stop_loss, risk_amount, take_profit)

    journal = load_journal()
    return render_template("index.html", journal=journal, lot_size=lot_size, expected_profit=expected_profit, request=request)

@app.route("/save", methods=["POST"])
def save():
    form = request.form
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "entry_price": form.get("entry_price"),
        "stop_loss": form.get("stop_loss"),
        "take_profit": form.get("take_profit"),
        "risk_amount": form.get("risk_amount"),
        "lot_size": form.get("lot_size"),
        "expected_profit": form.get("expected_profit"),
        "result": form.get("result"),
        "observation": form.get("observation")
    }
    journal = load_journal()
    journal.insert(0, entry)
    save_journal(journal)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
