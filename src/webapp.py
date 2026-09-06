"""Local web UI for generating royal300 Meta reports.

Run with: python src/webapp.py
Then open http://127.0.0.1:5000 in a browser.

This stays local-only (not deployed) since it holds/uses the Meta system-user
token from .env - never expose this outside your own machine.
"""
from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from report_service import generate_report, previous_month_range

app = Flask(__name__)

# Known clients (from `python src/list_assets.py`). Add more here as the
# system user is assigned to additional Pages/ad accounts.
CLIENTS = [
    {
        "key": "royal300",
        "label": "ROYAL 300",
        "page_id": "105034859277727",
        "ad_account_id": "act_690294929258317",
    },
    {
        "key": "happyvalley",
        "label": "Happy Valley Park",
        "page_id": "127586478173741",
        "ad_account_id": None,
    },
    {
        "key": "floriza",
        "label": "Floriza - Skin & Hair Clinic",
        "page_id": "1149414344915545",
        "ad_account_id": None,
    },
]
CLIENTS_BY_KEY = {c["key"]: c for c in CLIENTS}


@app.route("/")
def index():
    default_since, _ = previous_month_range()
    default_month = default_since[:7]  # YYYY-MM
    return render_template("index.html", clients=CLIENTS, default_month=default_month)


@app.route("/generate", methods=["POST"])
def generate():
    key = request.form.get("client")
    month = request.form.get("month") or None
    client = CLIENTS_BY_KEY.get(key)
    if not client:
        return jsonify({"error": "Unknown client selected."}), 400

    try:
        pdf_path: Path = generate_report(
            page_id=client["page_id"],
            page_name=client["label"],
            client_name=client["label"],
            ad_account_id=client.get("ad_account_id"),
            month=month,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=pdf_path.name,
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
