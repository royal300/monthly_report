"""Renders a PageReport into an executive 2-page monthly performance PDF with content ratio pie chart."""
from __future__ import annotations

import os
from pathlib import Path

from fpdf import FPDF

from report_data import AdAccountReport, PageReport, generate_tips

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


def _sanitize(text: str) -> str:
    """Core PDF fonts (Helvetica) only support latin-1. Drop emojis/unsupported chars."""
    if not text:
        return ""
    clean = text.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
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


def _generate_content_pie_chart(cb, temp_dir: Path) -> Path | None:
    """Generates a high-resolution, modern donut pie chart for the content ratio."""
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
        chart_path = temp_dir / "content_ratio_pie.png"
        plt.savefig(chart_path, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return chart_path
    except Exception as e:
        print(f"Notice: Failed to render pie chart: {e}")
        return None


class ReportPDF(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, f"Page {self.page_no()} of 2  |  royal300 Monthly Meta Analytics", align="C")


def _draw_kpi_card(pdf: ReportPDF, x: float, y: float, w: float, h: float,
                   title: str, value: str, subtext: str, delta_pct: str | None = None):
    # Card Background
    pdf.set_xy(x, y)
    pdf.set_fill_color(*LIGHT_BG)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.rect(x, y, w, h, style="FD")

    # Title
    pdf.set_xy(x + 2, y + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*GREY)
    pdf.cell(w - 4, 4, title.upper(), align="C")

    # Main Value
    pdf.set_xy(x + 2, y + 8)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*NAVY)
    pdf.cell(w - 4, 7, value, align="C")

    # Subtext / MoM badge
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
    pdf.set_auto_page_break(auto=False)

    # =========================================================================
    # PAGE 1: EXECUTIVE KPI SCORECARD & CONTENT PUBLISHING MIX + PIE CHART
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

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GREY)
    since_dmy = _format_date_dmy(report.period_since)
    until_dmy = _format_date_dmy(report.period_until)
    prev_txt = ""
    if report.previous_period:
        prev_since_dmy = _format_date_dmy(report.previous_period.period_since)
        prev_until_dmy = _format_date_dmy(report.previous_period.period_until)
        prev_txt = f" (Comparison: {prev_since_dmy} to {prev_until_dmy})"
    pdf.cell(0, 5, f"Reporting Period: {since_dmy} to {until_dmy}{prev_txt}", ln=True)
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

        # Table Header
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        col_w = [50, 42, 42, 46]
        headers = ["Key Metric", "Previous Month", "Current Month", "MoM Change"]
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

            # Color for change
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

    # Left Column: 3 Stacked Cards (Reels, Long Video, Graphics)
    card_h = 16.0
    gap_y = 2.5

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
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(*GREY)
    pdf.cell(card_stack_w - 6, 4, f"Average Views per Reel: {cb.reels_avg_views:,}", ln=True)

    # 2. Long Video Card
    y_vid = box_y + card_h + gap_y
    pdf.set_xy(15, y_vid)
    pdf.rect(15, y_vid, card_stack_w, card_h, style="FD")
    pdf.set_xy(18, y_vid + 2.5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*VIDEO_COLOR)
    vid_pct = round((cb.videos_count / cb.total_posts * 100) if cb.total_posts else 0)
    pdf.cell(50, 4, f"LONG VIDEO: {cb.videos_count} Posts ({vid_pct}%)", ln=False)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*NAVY)
    pdf.cell(60, 4, f"Total Views: {cb.videos_views:,}", ln=True, align="R")
    pdf.set_x(18)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(*GREY)
    pdf.cell(card_stack_w - 6, 4, f"Average Views per Video: {cb.videos_avg_views:,}", ln=True)

    # 3. Graphics & Photos Card
    y_gra = y_vid + card_h + gap_y
    pdf.set_xy(15, y_gra)
    pdf.rect(15, y_gra, card_stack_w, card_h, style="FD")
    pdf.set_xy(18, y_gra + 2.5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*GRAPHIC_COLOR)
    gra_pct = round((cb.graphics_count / cb.total_posts * 100) if cb.total_posts else 0)
    pdf.cell(50, 4, f"GRAPHICS & PHOTOS: {cb.graphics_count} Posts ({gra_pct}%)", ln=False)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*NAVY)
    pdf.cell(60, 4, f"Total Views: {cb.graphics_views:,}", ln=True, align="R")
    pdf.set_x(18)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(*GREY)
    pdf.cell(card_stack_w - 6, 4, f"Average Views per Graphic: {cb.graphics_avg_views:,}", ln=True)

    # Right Column: High-Resolution Donut Pie Chart
    chart_file = _generate_content_pie_chart(cb, output_path.parent)
    if chart_file and chart_file.exists():
        pdf.image(str(chart_file), x=133, y=box_y - 2, w=pie_w, h=pie_w)

    pdf.set_y(box_y + 57)

    # Content Distribution Bar
    if cb.total_posts > 0:
        bar_w = 180.0
        bar_h = 5.0
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 4, "CONTENT DISTRIBUTION MIX:", ln=True)

        bar_y = pdf.get_y()
        rw = (cb.reels_count / cb.total_posts) * bar_w
        vw = (cb.videos_count / cb.total_posts) * bar_w
        gw = bar_w - rw - vw

        cur_x = 15.0
        if rw > 0:
            pdf.set_fill_color(*REEL_COLOR)
            pdf.rect(cur_x, bar_y, rw, bar_h, style="F")
            cur_x += rw
        if vw > 0:
            pdf.set_fill_color(*VIDEO_COLOR)
            pdf.rect(cur_x, bar_y, vw, bar_h, style="F")
            cur_x += vw
        if gw > 0:
            pdf.set_fill_color(*GRAPHIC_COLOR)
            pdf.rect(cur_x, bar_y, gw, bar_h, style="F")

        pdf.set_y(bar_y + 6)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 4, f"Reels: {cb.reels_count} ({reels_pct}%) | Long Videos: {cb.videos_count} ({vid_pct}%) | Graphics/Photos: {cb.graphics_count} ({gra_pct}%)", ln=True)

    # Optional Ad Account Summary on Page 1 if present
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
    # PAGE 2: TOP 5 BEST PERFORMING CONTENT & STRATEGIC RECOMMENDATIONS
    # =========================================================================
    pdf.add_page()

    # Top Brand Bar
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 5, style="F")

    pdf.set_xy(15, 12)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, "Top 5 Performing Posts of the Month", ln=True)

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
        pdf.cell(180, 10, "No post data recorded for this period.", border=1, align="C")
        pdf.ln(10)
    else:
        pdf.set_font("Helvetica", "", 8)
        for idx, post in enumerate(report.top_posts):
            fill = (idx % 2 == 1)
            pdf.set_fill_color(*LIGHT_BG)
            pdf.set_text_color(*NAVY)

            # Post Number
            pdf.cell(col_w[0], 10, f"#{idx + 1}", border=0, fill=fill, align="C")

            # Content Type Badge
            type_label = post.content_type.replace("_", " ")
            if post.content_type == "REEL":
                pdf.set_text_color(*REEL_COLOR)
            elif post.content_type == "LONG_VIDEO":
                pdf.set_text_color(*VIDEO_COLOR)
            else:
                pdf.set_text_color(*GRAPHIC_COLOR)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.cell(col_w[1], 10, f"[{type_label}]", border=0, fill=fill)

            # Caption (truncated) with published date in DD/MM/YYYY
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*NAVY)
            post_date = _format_date_dmy(post.created_time) if post.created_time else ""
            date_prefix = f"[{post_date}] " if post_date else ""
            clean_msg = _sanitize(post.message[:45]) + ("..." if len(post.message) > 45 else "")
            caption = f"{date_prefix}{clean_msg}" if clean_msg else (f"[{post_date}] Post update" if post_date else "Post update")
            pdf.cell(col_w[2], 10, caption, border=0, fill=fill)

            # Impressions
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(col_w[3], 10, f"{post.impressions:,}  ", border=0, fill=fill, align="R")

            # Interactions breakdown
            pdf.set_font("Helvetica", "", 7.5)
            interaction_txt = f"{post.engaged_users:,} (rx:{post.reactions})"
            pdf.cell(col_w[4], 10, f"{interaction_txt}  ", border=0, fill=fill, align="R")
            pdf.ln(10)

    pdf.ln(8)

    # --- Strategic Recommendations (Tips) ---
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path
