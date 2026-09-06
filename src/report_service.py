"""Core report-generation logic, shared by the CLI (main.py) and the web UI (webapp.py)."""
from __future__ import annotations

import calendar
from datetime import date
from pathlib import Path

from config import OUTPUT_DIR
from graph_api import GraphAPIClient
from pdf_report import render_report
from report_data import build_ad_account_report, build_page_report


def previous_month_range(today: date | None = None) -> tuple[str, str]:
    today = today or date.today()
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month.fromordinal(first_of_this_month.toordinal() - 1)
    since = last_month_end.replace(day=1)
    return since.isoformat(), last_month_end.isoformat()


def month_range(month_str: str) -> tuple[str, str]:
    year, month = (int(x) for x in month_str.split("-"))
    since = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    until = date(year, month, last_day)
    return since.isoformat(), until.isoformat()


def generate_report(page_id: str, page_name: str, client_name: str | None = None,
                     ad_account_id: str | None = None, month: str | None = None) -> Path:
    """Runs the full pipeline (fetch -> aggregate -> render PDF) and returns the output path."""
    since, until = month_range(month) if month else previous_month_range()

    client = GraphAPIClient()

    # Page-level insights/content require a Page Access Token, not the raw
    # system-user token (Graph API error #190 otherwise).
    page_token = client.get_page_access_token(page_id)
    page_client = GraphAPIClient(token=page_token)

    page_info = page_client.get_page_info(page_id)
    insights_payload = page_client.get_page_insights(page_id, since, until)
    posts = page_client.get_page_posts_with_insights(page_id, since, until)

    report = build_page_report(
        page_id=page_id,
        page_name=page_name,
        page_info=page_info,
        insights_payload=insights_payload,
        posts=posts,
        since=since,
        until=until,
    )

    ad_report = None
    if ad_account_id:
        ad_rows = client.get_ad_account_insights(ad_account_id, since, until)
        ad_report = build_ad_account_report(ad_account_id, page_name, ad_rows)

    safe_name = page_name.replace(" ", "_")
    output_path = OUTPUT_DIR / f"{safe_name}_{since}_to_{until}.pdf"
    render_report(report, output_path, ad_report=ad_report, client_display_name=client_name)
    return output_path
