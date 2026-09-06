"""CLI entry point: generates one client's monthly PDF report.

Usage:
    python src/main.py --page-id 123456789 --page-name "Happy Valley Park" \
        [--ad-account-id act_690294929258317] [--month 2026-08] [--client-name "Happy Valley Park"]

If --month is omitted, defaults to the previous full calendar month.
"""
from __future__ import annotations

import argparse

from report_service import generate_report


def main():
    parser = argparse.ArgumentParser(description="Generate a royal300 monthly Meta report PDF")
    parser.add_argument("--page-id", required=True, help="Facebook Page numeric ID")
    parser.add_argument("--page-name", required=True, help="Page name (used in report + filename)")
    parser.add_argument("--client-name", default=None, help="Display name on the PDF (defaults to page name)")
    parser.add_argument("--ad-account-id", default=None, help="e.g. act_690294929258317 (optional)")
    parser.add_argument("--month", default=None, help="YYYY-MM (defaults to previous calendar month)")
    args = parser.parse_args()

    print(f"Generating report for '{args.page_name}'...")
    output_path = generate_report(
        page_id=args.page_id,
        page_name=args.page_name,
        client_name=args.client_name,
        ad_account_id=args.ad_account_id,
        month=args.month,
    )
    print(f"Done. Report saved to: {output_path}")


if __name__ == "__main__":
    main()
