from flask import Flask, render_template, request, redirect, url_for, send_file
import datetime
import os
import json
from werkzeug.utils import secure_filename
from fpdf import FPDF

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

JOURNAL_FILE = "journal_entries.json"

# Load journal
if os.path.exists(JOURNAL_FILE):
    with open(JOURNAL_FILE, "r") as file:
        journal_entries = json.load(file)
else:
    journal_entries = []

@app.route("/", methods=["GET", "POST"])
def index():
    expected_profit = ""
    lot_size = ""

    if request.method == "POST":
        # Form values
        pair_type = request.form.get("pair_type", "")
        symbol = request.form.get("symbol", "")
        direction = request.form.get("direction", "")
        entry = request.form.get("entry", "")
        stop_loss = request.form.get("stop_loss", "")
        take_profit = request.form.get("take_profit", "")
        risk_amount = request.form.get("risk_amount", "")
        expected_profit = request.form.get("expected_profit", "")

        save_trade = request.form.get("save_trade")
        decision = request.form.get("decision", "")
        result = request.form.get("result", "")
        observation = request.form.get("observation", "")

        # Uploads
        chart_image = request.files.get("chart_image")
        post_chart = request.files.get("post_chart")
        chart_image_filename = ""
        post_chart_filename = ""

        if chart_image and chart_image.filename:
            filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_") + secure_filename(chart_image.filename)
            chart_image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            chart_image_filename = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        if post_chart and post_chart.filename:
            filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_") + secure_filename(post_chart.filename)
            post_chart.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            post_chart_filename = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Lot size & expected profit
        try:
            if entry and stop_loss and risk_amount:
                entry = float(entry)
                stop_loss = float(stop_loss)
                risk_amount = float(risk_amount)

                pip_multiplier = 0.01 if "JPY" in symbol.upper() else 0.0001
                sl_pips = abs(entry - stop_loss) / pip_multiplier
                if sl_pips > 0:
                    lot_size = round(risk_amount / (sl_pips * 10), 2)

                if take_profit:
                    take_profit = float(take_profit)
                    tp_pips = abs(take_profit - entry) / pip_multiplier
                    expected_profit = round(lot_size * tp_pips * 10, 2)
        except Exception:
            lot_size = "Error"
            expected_profit = ""

        if save_trade:
            journal_entries.append({
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "pair_type": pair_type,
                "symbol": symbol,
                "direction": direction,
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_amount": risk_amount,
                "expected_profit": expected_profit,
                "chart_link": chart_image_filename,
                "decision": decision,
                "result": result,
                "post_chart": post_chart_filename,
                "observation": observation
            })
            with open(JOURNAL_FILE, "w") as file:
                json.dump(journal_entries, file, indent=4)

        return render_template("index.html", lot_size=lot_size, expected_profit=expected_profit, journal_entries=journal_entries, filter_option="All")

    # GET: filter logic
    filter_option = request.args.get("filter", "All")
    if filter_option == "Complete":
        filtered_entries = [e for e in journal_entries if e.get("result")]
    elif filter_option == "Incomplete":
        filtered_entries = [e for e in journal_entries if not e.get("result")]
    else:
        filtered_entries = journal_entries

    return render_template("index.html", lot_size=None, expected_profit=None, journal_entries=filtered_entries, filter_option=filter_option)

@app.route("/delete/<int:index>")
def delete(index):
    if 0 <= index < len(journal_entries):
        journal_entries.pop(index)
        with open(JOURNAL_FILE, "w") as file:
            json.dump(journal_entries, file, indent=4)
    return redirect(url_for("index"))

@app.route("/edit/<int:index>", methods=["GET", "POST"])
def edit(index):
    if index >= len(journal_entries):
        return redirect(url_for("index"))

    entry = journal_entries[index]

    if request.method == "POST":
        result = request.form.get("result", "")
        observation = request.form.get("observation", "")
        post_chart = request.files.get("post_chart")

        if post_chart and post_chart.filename:
            filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_") + secure_filename(post_chart.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            post_chart.save(path)
            entry["post_chart"] = path

        entry["result"] = result
        entry["observation"] = observation

        with open(JOURNAL_FILE, "w") as file:
            json.dump(journal_entries, file, indent=4)

        return redirect(url_for("index"))

    return render_template("edit.html", entry=entry, index=index)

@app.route("/export/pdf")
def export_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Trade Journal Export", ln=True, align='C')
    pdf.ln(10)

    for entry in journal_entries:
        pdf.set_font("Arial", style="B", size=11)
        pdf.cell(0, 10, f"{entry['date']} | {entry['symbol']} | {entry['direction']}", ln=True)

        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 8,
            f"Entry: {entry['entry']} | SL: {entry['stop_loss']} | TP: {entry['take_profit']}\n"
            f"Risk: {entry['risk_amount']} | Expected Profit: {entry['expected_profit']}\n"
            f"Result: {entry.get('result', 'N/A')}\n"
            f"Notes: {entry.get('observation', '')}"
        )
        pdf.ln(5)

    filename = "journal_export.pdf"
    pdf.output(filename)
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run()
