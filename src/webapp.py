"""Local web UI for generating royal300 Meta reports.

Run with: python src/webapp.py
Then open http://127.0.0.1:5000 in a browser.

This stays local-only (not deployed) since it holds/uses the Meta system-user
token from .env - never expose this outside your own machine.
"""
from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from graph_api import GraphAPIClient
from report_service import generate_report, previous_month_range

app = Flask(__name__)


def load_available_pages() -> list[dict]:
    """Dynamically queries Meta Graph API for all pages assigned to this system user."""
    try:
        client = GraphAPIClient()
        raw_pages = client.list_assigned_pages()
        if raw_pages:
            return [
                {
                    "page_id": str(p["id"]),
                    "label": p.get("name", "Unnamed Page"),
                    "fans": p.get("fan_count", 0),
                }
                for p in raw_pages
            ]
    except Exception as e:
        print(f"Notice: Failed to fetch live pages ({e}), falling back to cache.")

    return [
        {"page_id": "127586478173741", "label": "Happy Valley Park", "fans": 48733},
        {"page_id": "1149414344915545", "label": "Floriza - Skin & Hair Clinic", "fans": 70},
        {"page_id": "105034859277727", "label": "ROYAL 300", "fans": 28},
    ]


@app.route("/")
def index():
    pages = load_available_pages()
    default_since, _ = previous_month_range()
    default_month = default_since[:7]  # YYYY-MM
    return render_template("index.html", pages=pages, default_month=default_month)


@app.route("/api/pages")
def api_pages():
    pages = load_available_pages()
    return jsonify({"pages": pages})


@app.route("/generate", methods=["POST"])
def generate():
    page_id = request.form.get("page_id") or request.form.get("client")
    month = request.form.get("month") or None
    page_name = request.form.get("page_name")

    if not page_id:
        return jsonify({"error": "No page selected."}), 400

    pages = load_available_pages()
    matched = next((p for p in pages if p["page_id"] == str(page_id)), None)
    if matched:
        page_name = matched["label"]
    elif not page_name:
        page_name = f"Page_{page_id}"

    try:
        pdf_path: Path = generate_report(
            page_id=str(page_id),
            page_name=page_name,
            client_name=page_name,
            ad_account_id=None,  # As requested, ads are omitted/not needed
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
