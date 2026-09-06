"""Renders a PageReport (+ optional AdAccountReport) into a PDF."""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from report_data import AdAccountReport, PageReport, generate_tips

NAVY = (24, 40, 72)
ACCENT = (0, 120, 212)
GREY = (110, 110, 110)
LIGHT_BG = (245, 247, 250)


def _sanitize(text: str) -> str:
    """Core PDF fonts (Helvetica) only support latin-1. Post captions often
    contain emoji, so drop anything outside that range rather than crash."""
    return text.encode("latin-1", errors="ignore").decode("latin-1")


class ReportPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, f"Page {self.page_no()} - royal300", align="C")


def _stat_box(pdf: ReportPDF, x: float, y: float, w: float, label: str, value: str):
    pdf.set_xy(x, y)
    pdf.set_fill_color(*LIGHT_BG)
    pdf.rect(x, y, w, 22, style="F")
    pdf.set_xy(x, y + 3)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*NAVY)
    pdf.cell(w, 8, value, align="C")
    pdf.set_xy(x, y + 12)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GREY)
    pdf.cell(w, 6, label, align="C")


def render_report(report: PageReport, output_path: Path, ad_report: AdAccountReport | None = None,
                   client_display_name: str | None = None) -> Path:
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # --- Title block ---
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 12, _sanitize(client_display_name or report.page_name), ln=True)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 8, f"Monthly Performance Report  |  {report.period_since} to {report.period_until}", ln=True)
    pdf.ln(4)

    # --- Stat boxes ---
    box_w = 44
    gap = 4
    x0 = pdf.get_x()
    y0 = pdf.get_y()
    stats = [
        ("Followers", f"{report.followers:,}"),
        ("Net Growth", f"{report.net_growth:+,}"),
        ("Impressions", f"{report.impressions:,}"),
        ("Engagement Rate", f"{report.engagement_rate}%"),
    ]
    for i, (label, value) in enumerate(stats):
        _stat_box(pdf, x0 + i * (box_w + gap), y0, box_w, label, value)
    pdf.set_y(y0 + 30)

    # --- Ad account summary (optional) ---
    if ad_report:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 10, "Ad Account Summary", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        rows = [
            ("Spend", f"Rs.{ad_report.spend:,.2f}"),
            ("Impressions", f"{ad_report.impressions:,}"),
            ("Reach", f"{ad_report.reach:,}"),
            ("Clicks", f"{ad_report.clicks:,}"),
            ("CTR", f"{ad_report.ctr:.2f}%"),
            ("CPC", f"Rs.{ad_report.cpc:.2f}"),
        ]
        col_w = 45
        for i, (label, value) in enumerate(rows):
            if i % 4 == 0 and i > 0:
                pdf.ln(8)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(col_w, 8, f"{label}:", border=0)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(col_w - 15, 8, value, border=0)
        pdf.ln(14)

    # --- Top 5 posts ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 10, "Top Posts by Views", ln=True)

    if not report.top_posts:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 8, "No posts with recorded impressions this period.", ln=True)
    else:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(90, 8, "Post", border=0, fill=True)
        pdf.cell(40, 8, "Impressions", border=0, fill=True, align="R")
        pdf.cell(40, 8, "Engaged Users", border=0, fill=True, align="R")
        pdf.ln(8)

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(30, 30, 30)
        for idx, post in enumerate(report.top_posts):
            fill = idx % 2 == 0
            pdf.set_fill_color(*LIGHT_BG)
            pdf.cell(90, 8, _sanitize(post.message[:55]), border=0, fill=fill)
            pdf.cell(40, 8, f"{post.impressions:,}", border=0, fill=fill, align="R")
            pdf.cell(40, 8, f"{post.engaged_users:,}", border=0, fill=fill, align="R")
            pdf.ln(8)
    pdf.ln(8)

    # --- Tips ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 10, "Tips for Next Month", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    for tip in generate_tips(report):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 6, _sanitize(f"-  {tip}"))
        pdf.ln(2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path
