"""Renders an executive performance PDF with Facebook analytics (Pages 1 & 2)
and Instagram analytics (Pages 3 & 4 if connected), featuring high-resolution Donut Pie Charts
and MoM comparison tables with explicit month names.
"""
from __future__ import annotations

import calendar
import os
from pathlib import Path

from fpdf import FPDF

from report_data import AdAccountReport, PageReport, generate_tips, generate_instagram_tips

NAVY = (16, 27, 51)
ACCENT = (0, 120, 212)
GREY = (110, 110, 110)
LIGHT_BG = (246, 248, 251)
WHITE = (255, 255, 255)
GREEN = (30, 138, 62)
RED = (192, 57, 43)
BORDER_COLOR = (226, 232, 240)
REEL_COLOR = (124, 58, 237)      # Purple
VIDEO_COLOR = (225, 29, 72)      # Rose
GRAPHIC_COLOR = (2, 132, 199)    # Blue
IG_GRADIENT = (193, 53, 132)     # Instagram Magenta


def _sanitize(text: str) -> str:
    """Core PDF fonts (Helvetica) only support latin-1. Drop emojis/unsupported chars."""
    if not text:
        return ""
    clean = (
        text.replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", "-")
        .replace("•", "*")
    )
    return clean.encode("latin-1", errors="ignore").decode("latin-1")


def _format_date_dmy(date_str: str) -> str:
    """Converts YYYY-MM-DD or ISO timestamp to DD/MM/YYYY."""
    if not date_str:
        return ""
    clean = str(date_str).strip()[:10]
    parts = clean.split("-")
    if len(parts) == 3 and len(parts[0]) == 4:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return clean


def _get_month_label(date_str: str) -> str:
    """Converts '2026-08-01' or '2026-08' to 'August 2026'."""
    if not date_str:
        return ""
    parts = str(date_str).strip()[:10].split("-")
    if len(parts) >= 2:
        try:
            m_idx = int(parts[1])
            y = parts[0]
            return f"{calendar.month_name[m_idx]} {y}"
        except Exception:
            pass
    return date_str


def _generate_content_pie_chart(cb, temp_dir: Path) -> Path | None:
    """Generates a high-resolution donut pie chart for Facebook content ratio."""
    if cb.total_posts == 0:
        return None

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        labels = []
        sizes = []
        colors = []
        explode = []

        if cb.reels_count > 0:
            labels.append(f"Reels\n({cb.reels_count})")
            sizes.append(cb.reels_count)
            colors.append("#7c3aed")
            explode.append(0.04)

        if cb.videos_count > 0:
            labels.append(f"Long Video\n({cb.videos_count})")
            sizes.append(cb.videos_count)
            colors.append("#e11d48")
            explode.append(0.04)

        if cb.graphics_count > 0:
            labels.append(f"Graphics\n({cb.graphics_count})")
            sizes.append(cb.graphics_count)
            colors.append("#0284c7")
            explode.append(0.04)

        fig, ax = plt.subplots(figsize=(3.4, 3.4), dpi=220)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        wedges, texts, autotexts = ax.pie(
            sizes,
            explode=explode,
            labels=labels,
            colors=colors,
            autopct="%1.0f%%",
            pctdistance=0.72,
            startangle=140,
            textprops={"fontsize": 8.5, "color": "#101b33", "weight": "bold"},
            wedgeprops=dict(width=0.46, edgecolor="#ffffff", linewidth=2.5),
        )

        for autotext in autotexts:
            autotext.set_color("#ffffff")
            autotext.set_fontsize(9)
            autotext.set_weight("bold")

        ax.axis("equal")
        plt.tight_layout()

        temp_dir.mkdir(parents=True, exist_ok=True)
        chart_path = temp_dir / "fb_content_ratio_pie.png"
        plt.savefig(chart_path, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return chart_path
    except Exception as e:
        print(f"Notice: Failed to render FB pie chart: {e}")
        return None


def _generate_ig_content_pie_chart(cb, temp_dir: Path) -> Path | None:
    """Generates a high-resolution donut pie chart for Instagram content ratio."""
    if cb.total_posts == 0:
        return None

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        labels = []
        sizes = []
        colors = []
        explode = []

        if cb.reels_count > 0:
            labels.append(f"Reels\n({cb.reels_count})")
            sizes.append(cb.reels_count)
            colors.append("#7c3aed")
            explode.append(0.04)

        if cb.carousels_count > 0:
            labels.append(f"Carousels\n({cb.carousels_count})")
            sizes.append(cb.carousels_count)
            colors.append("#f59e0b")  # Amber
            explode.append(0.04)

        if cb.images_count > 0:
            labels.append(f"Photos\n({cb.images_count})")
            sizes.append(cb.images_count)
            colors.append("#06b6d4")  # Cyan
            explode.append(0.04)

        fig, ax = plt.subplots(figsize=(3.4, 3.4), dpi=220)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        wedges, texts, autotexts = ax.pie(
            sizes,
            explode=explode,
            labels=labels,
            colors=colors,
            autopct="%1.0f%%",
            pctdistance=0.72,
            startangle=140,
            textprops={"fontsize": 8.5, "color": "#101b33", "weight": "bold"},
            wedgeprops=dict(width=0.46, edgecolor="#ffffff", linewidth=2.5),
        )

        for autotext in autotexts:
            autotext.set_color("#ffffff")
            autotext.set_fontsize(9)
            autotext.set_weight("bold")

        ax.axis("equal")
        plt.tight_layout()

        temp_dir.mkdir(parents=True, exist_ok=True)
        chart_path = temp_dir / "ig_content_ratio_pie.png"
        plt.savefig(chart_path, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return chart_path
    except Exception as e:
        print(f"Notice: Failed to render IG pie chart: {e}")
        return None


class ReportPDF(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, f"Page {self.page_no()} of {{nb}}  |  royal300 Monthly Meta Analytics", align="C")


def _draw_kpi_card(pdf: ReportPDF, x: float, y: float, w: float, h: float,
                   title: str, value: str, subtext: str, delta_pct: str | None = None):
    pdf.set_xy(x, y)
    pdf.set_fill_color(*LIGHT_BG)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.rect(x, y, w, h, style="FD")

    pdf.set_xy(x + 2, y + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*GREY)
    pdf.cell(w - 4, 4, title.upper(), align="C")

    pdf.set_xy(x + 2, y + 8)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*NAVY)
    pdf.cell(w - 4, 7, value, align="C")

    pdf.set_xy(x + 2, y + 16)
    pdf.set_font("Helvetica", "", 7.5)
    if delta_pct and delta_pct != "N/A":
        if delta_pct.startswith("+"):
            pdf.set_text_color(*GREEN)
        elif delta_pct.startswith("-"):
            pdf.set_text_color(*RED)
        else:
            pdf.set_text_color(*GREY)
        pdf.cell(w - 4, 4, f"{subtext} ({delta_pct} MoM)", align="C")
    else:
        pdf.set_text_color(*GREY)
        pdf.cell(w - 4, 4, subtext, align="C")


def render_report(report: PageReport, output_path: Path, ad_report: AdAccountReport | None = None,
                   client_display_name: str | None = None) -> Path:
    pdf = ReportPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=False)

    temp_chart_dir = output_path.parent / "temp_charts"

    # =========================================================================
    # PAGE 1: FACEBOOK EXECUTIVE SCORECARD & CONTENT MIX + PIE CHART
    # =========================================================================
    pdf.add_page()

    # Top Brand Bar
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 5, style="F")

    # Header
    pdf.set_xy(15, 12)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 10, _sanitize(client_display_name or report.page_name), ln=True)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 5, "MONTHLY FACEBOOK PERFORMANCE REPORT", ln=True)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*GREY)
    since_dmy = _format_date_dmy(report.period_since)
    until_dmy = _format_date_dmy(report.period_until)
    prev_txt = ""
    if report.previous_period:
        prev_since_dmy = _format_date_dmy(report.previous_period.period_since)
        prev_until_dmy = _format_date_dmy(report.previous_period.period_until)
        prev_txt = f" (Comparison: {prev_since_dmy} to {prev_until_dmy})"
    pdf.cell(0, 4.5, f"Reporting Period: {since_dmy} to {until_dmy}{prev_txt}", ln=True)

    # Connected Accounts Line
    if report.instagram:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*IG_GRADIENT)
        ig_line = f"Connected Instagram: @{report.instagram.username}  |  Followers: {report.instagram.followers:,}  |  Total Media: {report.instagram.media_count:,}"
        pdf.cell(0, 4.5, _sanitize(ig_line), ln=True)
        pdf.ln(2)
    else:
        pdf.ln(5)

    # --- 1. KPI Scorecard (4 Cards) ---
    kpi_y = pdf.get_y()
    card_w = 42.5
    gap = 3.3
    x0 = 15.0

    # KPI 1: Followers
    net_str = f"{report.net_growth:+d} Net Gain"
    _draw_kpi_card(
        pdf, x0, kpi_y, card_w, 23,
        "Month-End Followers",
        f"{report.followers:,}",
        net_str,
        report.mom_growth.formatted_pct if report.previous_period else None,
    )

    # KPI 2: Views / Impressions
    _draw_kpi_card(
        pdf, x0 + (card_w + gap), kpi_y, card_w, 23,
        "Total Views / Reach",
        f"{report.impressions:,}",
        "Media Views",
        report.mom_impressions.formatted_pct if report.previous_period else None,
    )

    # KPI 3: Engagement
    _draw_kpi_card(
        pdf, x0 + 2 * (card_w + gap), kpi_y, card_w, 23,
        "Total Engagements",
        f"{report.engagement:,}",
        "Reactions, Comments, Clicks",
        report.mom_engagement.formatted_pct if report.previous_period else None,
    )

    # KPI 4: Engagement Rate
    _draw_kpi_card(
        pdf, x0 + 3 * (card_w + gap), kpi_y, card_w, 23,
        "Engagement Rate",
        f"{report.engagement_rate}%",
        "Interactions/View",
        report.mom_engagement_rate.formatted_pct if report.previous_period else None,
    )

    pdf.set_y(kpi_y + 28)

    # --- 2. Month-over-Month Comparison Table ---
    if report.previous_period:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 8, "Month-over-Month (MoM) Growth Comparison", ln=True)

        # Table Header with explicit month names
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        col_w = [52, 45, 45, 38]

        prev_label = f"Previous Month ({_get_month_label(report.previous_period.period_since)})"
        curr_label = f"Current Month ({_get_month_label(report.period_since)})"
        headers = ["Key Performance Metric", prev_label, curr_label, "MoM Change"]

        for i, h in enumerate(headers):
            align = "L" if i == 0 else "R"
            pdf.cell(col_w[i], 6.5, f"  {h}  ", border=0, fill=True, align=align)
        pdf.ln(6.5)

        mom_rows = [
            ("Page Followers (Month-End)", f"{report.previous_period.followers:,}", f"{report.followers:,}", report.mom_followers.formatted_pct),
            ("Net New Followers", f"{report.previous_period.net_growth:+d}", f"{report.net_growth:+d}", report.mom_growth.formatted_pct),
            ("Total Content Views / Impressions", f"{report.previous_period.impressions:,}", f"{report.impressions:,}", report.mom_impressions.formatted_pct),
            ("Total Engagements (Interactions)", f"{report.previous_period.engagement:,}", f"{report.engagement:,}", report.mom_engagement.formatted_pct),
            ("Average Engagement Rate", f"{report.previous_period.engagement_rate}%", f"{report.engagement_rate}%", report.mom_engagement_rate.formatted_pct),
            ("Total Posts Published", f"{report.previous_period.content_breakdown.total_posts}", f"{report.content_breakdown.total_posts}", report.mom_posts.formatted_pct),
        ]

        pdf.set_font("Helvetica", "", 8)
        for idx, (label, prev_val, curr_val, pct) in enumerate(mom_rows):
            fill = (idx % 2 == 1)
            pdf.set_fill_color(*LIGHT_BG)
            pdf.set_text_color(*NAVY)
            pdf.cell(col_w[0], 6, f"  {label}", fill=fill)
            pdf.cell(col_w[1], 6, f"{prev_val}  ", fill=fill, align="R")
            pdf.cell(col_w[2], 6, f"{curr_val}  ", fill=fill, align="R")

            if pct and pct.startswith("+"):
                pdf.set_text_color(*GREEN)
            elif pct and pct.startswith("-"):
                pdf.set_text_color(*RED)
            else:
                pdf.set_text_color(*GREY)
            pdf.cell(col_w[3], 6, f"{pct}  ", fill=fill, align="R")
            pdf.ln(6)

        pdf.ln(4)

    # --- 3. Content Publishing Breakdown with Donut Pie Chart ---
    cb = report.content_breakdown
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, f"Content Publishing Record & Ratio (Total: {cb.total_posts} Posts)", ln=True)

    box_y = pdf.get_y()
    card_stack_w = 114.0
    pie_w = 62.0
    card_h = 16.0

    # 1. Reels Card
    pdf.set_xy(15, box_y)
    pdf.set_fill_color(*LIGHT_BG)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.rect(15, box_y, card_stack_w, card_h, style="FD")
    pdf.set_xy(18, box_y + 2.5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*REEL_COLOR)
    reels_pct = round((cb.reels_count / cb.total_posts * 100) if cb.total_posts else 0)
    pdf.cell(50, 4, f"REELS (Short Video): {cb.reels_count} Posts ({reels_pct}%)", ln=False)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*NAVY)
    pdf.cell(60, 4, f"Total Views: {cb.reels_views:,}", ln=True, align="R")
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*GREY)
    pdf.cell(110, 4, f"Avg Views / Reel: {cb.reels_avg_views:,}", ln=True)

    # 2. Long Video Card
    pdf.set_xy(15, box_y + card_h + 2.5)
    pdf.set_fill_color(*LIGHT_BG)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.rect(15, box_y + card_h + 2.5, card_stack_w, card_h, style="FD")
    pdf.set_xy(18, box_y + card_h + 5.0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*VIDEO_COLOR)
    vid_pct = round((cb.videos_count / cb.total_posts * 100) if cb.total_posts else 0)
    pdf.cell(50, 4, f"LONG VIDEO: {cb.videos_count} Posts ({vid_pct}%)", ln=False)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*NAVY)
    pdf.cell(60, 4, f"Total Views: {cb.videos_views:,}", ln=True, align="R")
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*GREY)
    pdf.cell(110, 4, f"Avg Views / Video: {cb.videos_avg_views:,}", ln=True)

    # 3. Graphics Card
    pdf.set_xy(15, box_y + 2 * (card_h + 2.5))
    pdf.set_fill_color(*LIGHT_BG)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.rect(15, box_y + 2 * (card_h + 2.5), card_stack_w, card_h, style="FD")
    pdf.set_xy(18, box_y + 2 * (card_h + 2.5) + 2.5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*GRAPHIC_COLOR)
    gra_pct = round((cb.graphics_count / cb.total_posts * 100) if cb.total_posts else 0)
    pdf.cell(50, 4, f"GRAPHICS / PHOTOS: {cb.graphics_count} Posts ({gra_pct}%)", ln=False)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*NAVY)
    pdf.cell(60, 4, f"Total Views: {cb.graphics_views:,}", ln=True, align="R")
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*GREY)
    pdf.cell(110, 4, f"Avg Views / Graphic: {cb.graphics_avg_views:,}", ln=True)

    # Render Donut Pie Chart on Right
    chart_path = _generate_content_pie_chart(cb, temp_chart_dir)
    if chart_path and chart_path.exists():
        pdf.image(str(chart_path), x=15 + card_stack_w + 4, y=box_y - 2, w=pie_w)

    # =========================================================================
    # PAGE 2: TOP 5 FACEBOOK POSTS & STRATEGIC RECOMMENDATIONS
    # =========================================================================
    pdf.add_page()

    # Top Brand Bar
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 5, style="F")

    pdf.set_xy(15, 12)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, "Top 5 Performing Facebook Posts of the Month", ln=True)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 5, "Ranked by total impressions/views and audience interactions (reactions, comments, shares).", ln=True)
    pdf.ln(3)

    # Top Posts Table
    col_w = [10, 26, 74, 35, 35]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    pdf.cell(col_w[0], 7, "#", border=0, fill=True, align="C")
    pdf.cell(col_w[1], 7, "Format", border=0, fill=True)
    pdf.cell(col_w[2], 7, "Caption / Excerpt", border=0, fill=True)
    pdf.cell(col_w[3], 7, "Views / Impr.", border=0, fill=True, align="R")
    pdf.cell(col_w[4], 7, "Interactions", border=0, fill=True, align="R")
    pdf.ln(7)

    if not report.top_posts:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*GREY)
        pdf.cell(180, 10, "No Facebook post data recorded for this period.", border=1, align="C")
        pdf.ln(10)
    else:
        pdf.set_font("Helvetica", "", 8)
        for idx, post in enumerate(report.top_posts):
            fill = (idx % 2 == 1)
            pdf.set_fill_color(*LIGHT_BG)
            pdf.set_text_color(*NAVY)

            pdf.cell(col_w[0], 10, f"#{idx + 1}", border=0, fill=fill, align="C")

            type_label = post.content_type.replace("_", " ")
            if post.content_type == "REEL":
                pdf.set_text_color(*REEL_COLOR)
            elif post.content_type == "LONG_VIDEO":
                pdf.set_text_color(*VIDEO_COLOR)
            else:
                pdf.set_text_color(*GRAPHIC_COLOR)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.cell(col_w[1], 10, f"[{type_label}]", border=0, fill=fill)

            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*NAVY)
            post_date = _format_date_dmy(post.created_time) if post.created_time else ""
            date_prefix = f"[{post_date}] " if post_date else ""
            clean_msg = _sanitize(post.message[:45]) + ("..." if len(post.message) > 45 else "")
            caption = f"{date_prefix}{clean_msg}" if clean_msg else (f"[{post_date}] Post update" if post_date else "Post update")
            pdf.cell(col_w[2], 10, caption, border=0, fill=fill)

            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(col_w[3], 10, f"{post.impressions:,}  ", border=0, fill=fill, align="R")

            pdf.set_font("Helvetica", "", 7.5)
            interaction_txt = f"{post.engaged_users:,} (rx:{post.reactions})"
            pdf.cell(col_w[4], 10, f"{interaction_txt}  ", border=0, fill=fill, align="R")
            pdf.ln(10)

    pdf.ln(8)

    # --- Strategic Recommendations (Facebook Tips) ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, "Actionable Insights & Next-Month Strategy", ln=True)

    tips = generate_tips(report)
    for tip in tips:
        card_y = pdf.get_y()
        pdf.set_fill_color(*LIGHT_BG)
        pdf.set_draw_color(*BORDER_COLOR)

        tip_text = _sanitize(tip)
        pdf.set_xy(15, card_y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*ACCENT)
        pdf.cell(6, 5, ">", border=0)

        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(174, 5, tip_text)
        pdf.ln(3)

    # Optional Ad Account Summary if present
    if ad_report:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 6, "Meta Ads Summary (Campaign Performance)", ln=True)
        ad_text = (f"Spend: Rs.{ad_report.spend:,.2f}  |  Reach: {ad_report.reach:,}  |  "
                   f"Impressions: {ad_report.impressions:,}  |  Clicks: {ad_report.clicks:,}  |  "
                   f"CTR: {ad_report.ctr:.2f}%  |  CPC: Rs.{ad_report.cpc:.2f}")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 5, ad_text, ln=True)

    # =========================================================================
    # PAGES 3 & 4: INSTAGRAM PERFORMANCE REPORT (IF CONNECTED)
    # =========================================================================
    ig = report.instagram_report
    if ig:
        # ---------------------------------------------------------------------
        # PAGE 3: INSTAGRAM EXECUTIVE SCORECARD & CONTENT MIX + PIE CHART
        # ---------------------------------------------------------------------
        pdf.add_page()

        # Top Brand Bar (Instagram Accent)
        pdf.set_fill_color(*IG_GRADIENT)
        pdf.rect(0, 0, 210, 5, style="F")

        # Header
        pdf.set_xy(15, 12)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 10, _sanitize(client_display_name or report.page_name), ln=True)

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*IG_GRADIENT)
        pdf.cell(0, 5, "MONTHLY INSTAGRAM PERFORMANCE REPORT", ln=True)

        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*GREY)
        since_dmy = _format_date_dmy(ig.period_since)
        until_dmy = _format_date_dmy(ig.period_until)
        prev_txt = ""
        if ig.previous_period:
            prev_since_dmy = _format_date_dmy(ig.previous_period.period_since)
            prev_until_dmy = _format_date_dmy(ig.previous_period.period_until)
            prev_txt = f" (Comparison: {prev_since_dmy} to {prev_until_dmy})"
        pdf.cell(0, 4.5, f"Reporting Period: {since_dmy} to {until_dmy}{prev_txt}", ln=True)

        # Profile Handle Row
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*IG_GRADIENT)
        handle_line = f"Instagram Account: @{ig.username}  |  Profile Followers: {ig.followers:,}  |  Published Media: {ig.content_breakdown.total_posts}"
        pdf.cell(0, 4.5, _sanitize(handle_line), ln=True)
        pdf.ln(3)

        # --- 1. Instagram KPI Scorecard (4 Cards) ---
        ig_kpi_y = pdf.get_y()
        card_w = 42.5
        gap = 3.3
        x0 = 15.0

        _draw_kpi_card(
            pdf, x0, ig_kpi_y, card_w, 23,
            "Instagram Followers",
            f"{ig.followers:,}",
            "Profile Followers",
            ig.mom_followers.formatted_pct if ig.previous_period else None,
        )
        _draw_kpi_card(
            pdf, x0 + (card_w + gap), ig_kpi_y, card_w, 23,
            "Total Reach",
            f"{ig.reach:,}",
            "Accounts Reached",
            ig.mom_reach.formatted_pct if ig.previous_period else None,
        )
        _draw_kpi_card(
            pdf, x0 + 2 * (card_w + gap), ig_kpi_y, card_w, 23,
            "Total Views",
            f"{ig.views:,}",
            "Impressions / Plays",
            ig.mom_views.formatted_pct if ig.previous_period else None,
        )
        _draw_kpi_card(
            pdf, x0 + 3 * (card_w + gap), ig_kpi_y, card_w, 23,
            "Engagement Rate",
            f"{ig.engagement_rate}%",
            "Interactions / View",
            ig.mom_engagement_rate.formatted_pct if ig.previous_period else None,
        )

        pdf.set_y(ig_kpi_y + 28)

        # --- 2. Instagram Month-over-Month Comparison Table ---
        if ig.previous_period:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(*NAVY)
            pdf.cell(0, 8, "Instagram Month-over-Month (MoM) Growth Comparison", ln=True)

            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(*IG_GRADIENT)
            pdf.set_text_color(*WHITE)
            col_w = [52, 45, 45, 38]

            prev_ig_label = f"Previous Month ({_get_month_label(ig.previous_period.period_since)})"
            curr_ig_label = f"Current Month ({_get_month_label(ig.period_since)})"
            headers = ["Key Performance Metric", prev_ig_label, curr_ig_label, "MoM Change"]

            for i, h in enumerate(headers):
                align = "L" if i == 0 else "R"
                pdf.cell(col_w[i], 6.5, f"  {h}  ", border=0, fill=True, align=align)
            pdf.ln(6.5)

            ig_mom_rows = [
                ("Account Followers", f"{ig.previous_period.followers:,}", f"{ig.followers:,}", ig.mom_followers.formatted_pct),
                ("Accounts Reached (Unique)", f"{ig.previous_period.reach:,}", f"{ig.reach:,}", ig.mom_reach.formatted_pct),
                ("Total Content Views / Plays", f"{ig.previous_period.views:,}", f"{ig.views:,}", ig.mom_views.formatted_pct),
                ("Total Content Interactions", f"{ig.previous_period.interactions:,}", f"{ig.interactions:,}", ig.mom_interactions.formatted_pct),
                ("Average Engagement Rate", f"{ig.previous_period.engagement_rate}%", f"{ig.engagement_rate}%", ig.mom_engagement_rate.formatted_pct),
                ("Total Posts / Reels Published", f"{ig.previous_period.content_breakdown.total_posts}", f"{ig.content_breakdown.total_posts}", ig.mom_posts.formatted_pct),
            ]

            pdf.set_font("Helvetica", "", 8)
            for idx, (label, prev_val, curr_val, pct) in enumerate(ig_mom_rows):
                fill = (idx % 2 == 1)
                pdf.set_fill_color(*LIGHT_BG)
                pdf.set_text_color(*NAVY)
                pdf.cell(col_w[0], 6, f"  {label}", fill=fill)
                pdf.cell(col_w[1], 6, f"{prev_val}  ", fill=fill, align="R")
                pdf.cell(col_w[2], 6, f"{curr_val}  ", fill=fill, align="R")

                if pct and pct.startswith("+"):
                    pdf.set_text_color(*GREEN)
                elif pct and pct.startswith("-"):
                    pdf.set_text_color(*RED)
                else:
                    pdf.set_text_color(*GREY)
                pdf.cell(col_w[3], 6, f"{pct}  ", fill=fill, align="R")
                pdf.ln(6)

            pdf.ln(4)

        # --- 3. Instagram Content Publishing Breakdown with Donut Pie Chart ---
        ig_cb = ig.content_breakdown
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 8, f"Instagram Publishing Record & Content Mix (Total: {ig_cb.total_posts} Posts)", ln=True)

        ig_box_y = pdf.get_y()
        card_stack_w = 114.0
        pie_w = 62.0
        card_h = 16.0

        # Reels Card
        pdf.set_xy(15, ig_box_y)
        pdf.set_fill_color(*LIGHT_BG)
        pdf.set_draw_color(*BORDER_COLOR)
        pdf.rect(15, ig_box_y, card_stack_w, card_h, style="FD")
        pdf.set_xy(18, ig_box_y + 2.5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*REEL_COLOR)
        ig_reels_pct = round((ig_cb.reels_count / ig_cb.total_posts * 100) if ig_cb.total_posts else 0)
        pdf.cell(50, 4, f"REELS (Short Video): {ig_cb.reels_count} Posts ({ig_reels_pct}%)", ln=False)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*NAVY)
        pdf.cell(60, 4, f"Total Views: {ig_cb.reels_views:,}", ln=True, align="R")
        pdf.set_x(18)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*GREY)
        pdf.cell(110, 4, f"Avg Views / Reel: {ig_cb.reels_avg_views:,}", ln=True)

        # Carousels Card
        pdf.set_xy(15, ig_box_y + card_h + 2.5)
        pdf.set_fill_color(*LIGHT_BG)
        pdf.set_draw_color(*BORDER_COLOR)
        pdf.rect(15, ig_box_y + card_h + 2.5, card_stack_w, card_h, style="FD")
        pdf.set_xy(18, ig_box_y + card_h + 5.0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(245, 158, 11)  # Amber
        ig_car_pct = round((ig_cb.carousels_count / ig_cb.total_posts * 100) if ig_cb.total_posts else 0)
        pdf.cell(50, 4, f"CAROUSELS (Multi-Slide): {ig_cb.carousels_count} Posts ({ig_car_pct}%)", ln=False)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*NAVY)
        pdf.cell(60, 4, f"Total Views: {ig_cb.carousels_views:,}", ln=True, align="R")
        pdf.set_x(18)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*GREY)
        pdf.cell(110, 4, f"Avg Views / Carousel: {ig_cb.carousels_avg_views:,}", ln=True)

        # Photos Card
        pdf.set_xy(15, ig_box_y + 2 * (card_h + 2.5))
        pdf.set_fill_color(*LIGHT_BG)
        pdf.set_draw_color(*BORDER_COLOR)
        pdf.rect(15, ig_box_y + 2 * (card_h + 2.5), card_stack_w, card_h, style="FD")
        pdf.set_xy(18, ig_box_y + 2 * (card_h + 2.5) + 2.5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(6, 182, 212)  # Cyan
        ig_img_pct = round((ig_cb.images_count / ig_cb.total_posts * 100) if ig_cb.total_posts else 0)
        pdf.cell(50, 4, f"PHOTOS / SINGLE POSTS: {ig_cb.images_count} Posts ({ig_img_pct}%)", ln=False)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*NAVY)
        pdf.cell(60, 4, f"Total Views: {ig_cb.images_views:,}", ln=True, align="R")
        pdf.set_x(18)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*GREY)
        pdf.cell(110, 4, f"Avg Views / Photo: {ig_cb.images_avg_views:,}", ln=True)

        # Render Pie Chart on Right
        ig_pie_path = _generate_ig_content_pie_chart(ig_cb, temp_chart_dir)
        if ig_pie_path and ig_pie_path.exists():
            pdf.image(str(ig_pie_path), x=15 + card_stack_w + 4, y=ig_box_y - 2, w=pie_w)

        # ---------------------------------------------------------------------
        # PAGE 4: TOP 5 INSTAGRAM POSTS & REELS + STRATEGIC RECOMMENDATIONS
        # ---------------------------------------------------------------------
        pdf.add_page()

        # Top Brand Bar
        pdf.set_fill_color(*IG_GRADIENT)
        pdf.rect(0, 0, 210, 5, style="F")

        pdf.set_xy(15, 12)
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 8, "Top 5 Performing Instagram Posts & Reels of the Month", ln=True)

        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 5, "Ranked by total views/reach and community interactions (likes, comments, saves, shares).", ln=True)
        pdf.ln(3)

        # Top Posts Table
        col_w = [10, 26, 74, 35, 35]
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*IG_GRADIENT)
        pdf.set_text_color(*WHITE)
        pdf.cell(col_w[0], 7, "#", border=0, fill=True, align="C")
        pdf.cell(col_w[1], 7, "Format", border=0, fill=True)
        pdf.cell(col_w[2], 7, "Caption / Excerpt", border=0, fill=True)
        pdf.cell(col_w[3], 7, "Views / Reach", border=0, fill=True, align="R")
        pdf.cell(col_w[4], 7, "Interactions", border=0, fill=True, align="R")
        pdf.ln(7)

        if not ig.top_posts:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*GREY)
            pdf.cell(180, 10, "No Instagram post data recorded for this period.", border=1, align="C")
            pdf.ln(10)
        else:
            pdf.set_font("Helvetica", "", 8)
            for idx, post in enumerate(ig.top_posts):
                fill = (idx % 2 == 1)
                pdf.set_fill_color(*LIGHT_BG)
                pdf.set_text_color(*NAVY)

                pdf.cell(col_w[0], 10, f"#{idx + 1}", border=0, fill=fill, align="C")

                type_label = post.media_type
                if post.media_type == "REEL":
                    pdf.set_text_color(*REEL_COLOR)
                elif post.media_type == "CAROUSEL":
                    pdf.set_text_color(245, 158, 11)
                else:
                    pdf.set_text_color(6, 182, 212)
                pdf.set_font("Helvetica", "B", 7.5)
                pdf.cell(col_w[1], 10, f"[{type_label}]", border=0, fill=fill)

                pdf.set_font("Helvetica", "", 7.5)
                pdf.set_text_color(*NAVY)
                post_date = _format_date_dmy(post.created_time) if post.created_time else ""
                date_prefix = f"[{post_date}] " if post_date else ""
                clean_msg = _sanitize(post.caption[:45]) + ("..." if len(post.caption) > 45 else "")
                caption = f"{date_prefix}{clean_msg}" if clean_msg else (f"[{post_date}] Instagram post" if post_date else "Instagram post")
                pdf.cell(col_w[2], 10, caption, border=0, fill=fill)

                pdf.set_font("Helvetica", "B", 8)
                views_str = f"{post.views:,}" if post.views else f"{post.reach:,}"
                pdf.cell(col_w[3], 10, f"{views_str}  ", border=0, fill=fill, align="R")

                pdf.set_font("Helvetica", "", 7.5)
                inter_txt = f"{post.total_interactions:,} (lk:{post.likes})"
                pdf.cell(col_w[4], 10, f"{inter_txt}  ", border=0, fill=fill, align="R")
                pdf.ln(10)

        pdf.ln(8)

        # --- Instagram Strategic Recommendations ---
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 8, "Instagram Actionable Insights & Strategic Recommendations", ln=True)

        ig_tips = generate_instagram_tips(ig)
        for tip in ig_tips:
            card_y = pdf.get_y()
            pdf.set_fill_color(*LIGHT_BG)
            pdf.set_draw_color(*BORDER_COLOR)

            tip_text = _sanitize(tip)
            pdf.set_xy(15, card_y)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*IG_GRADIENT)
            pdf.cell(6, 5, ">", border=0)

            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(174, 5, tip_text)
            pdf.ln(3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path
