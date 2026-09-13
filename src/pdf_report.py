"""Renders a PageReport into an executive 2-page monthly performance PDF."""
from __future__ import annotations

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
    # Normalize common symbols
    clean = text.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return clean.encode("latin-1", errors="ignore").decode("latin-1")


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
    # PAGE 1: EXECUTIVE KPI SCORECARD & CONTENT PUBLISHING MIX
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
    prev_txt = f" (Comparison: {report.previous_period.period_since} to {report.previous_period.period_until})" if report.previous_period else ""
    pdf.cell(0, 5, f"Reporting Period: {report.period_since} to {report.period_until}{prev_txt}", ln=True)
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

    # --- 3. Content Publishing Breakdown ---
    cb = report.content_breakdown
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, f"Content Publishing Record (Total: {cb.total_posts} Posts)", ln=True)

    box_y = pdf.get_y()
    cat_w = 57.0
    cat_gap = 4.5

    # Category 1: Reels
    pdf.set_xy(15, box_y)
    pdf.set_fill_color(*LIGHT_BG)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.rect(15, box_y, cat_w, 32, style="FD")
    pdf.set_xy(17, box_y + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*REEL_COLOR)
    pdf.cell(cat_w - 4, 5, "REELS (Short Video)", ln=True)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*NAVY)
    pdf.set_x(17)
    pdf.cell(cat_w - 4, 5, f"Posts: {cb.reels_count}  ({round((cb.reels_count/cb.total_posts*100) if cb.total_posts else 0)}% of content)", ln=True)
    pdf.set_x(17)
    pdf.cell(cat_w - 4, 5, f"Total Views: {cb.reels_views:,}", ln=True)
    pdf.set_x(17)
    pdf.cell(cat_w - 4, 5, f"Avg Views / Reel: {cb.reels_avg_views:,}", ln=True)

    # Category 2: Long / Regular Video
    x_vid = 15 + cat_w + cat_gap
    pdf.set_xy(x_vid, box_y)
    pdf.rect(x_vid, box_y, cat_w, 32, style="FD")
    pdf.set_xy(x_vid + 2, box_y + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*VIDEO_COLOR)
    pdf.cell(cat_w - 4, 5, "LONG VIDEO", ln=True)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*NAVY)
    pdf.set_x(x_vid + 2)
    pdf.cell(cat_w - 4, 5, f"Posts: {cb.videos_count}  ({round((cb.videos_count/cb.total_posts*100) if cb.total_posts else 0)}% of content)", ln=True)
    pdf.set_x(x_vid + 2)
    pdf.cell(cat_w - 4, 5, f"Total Views: {cb.videos_views:,}", ln=True)
    pdf.set_x(x_vid + 2)
    pdf.cell(cat_w - 4, 5, f"Avg Views / Video: {cb.videos_avg_views:,}", ln=True)

    # Category 3: Graphics / Photos
    x_gra = 15 + 2 * (cat_w + cat_gap)
    pdf.set_xy(x_gra, box_y)
    pdf.rect(x_gra, box_y, cat_w, 32, style="FD")
    pdf.set_xy(x_gra + 2, box_y + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*GRAPHIC_COLOR)
    pdf.cell(cat_w - 4, 5, "GRAPHICS & PHOTOS", ln=True)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*NAVY)
    pdf.set_x(x_gra + 2)
    pdf.cell(cat_w - 4, 5, f"Posts: {cb.graphics_count}  ({round((cb.graphics_count/cb.total_posts*100) if cb.total_posts else 0)}% of content)", ln=True)
    pdf.set_x(x_gra + 2)
    pdf.cell(cat_w - 4, 5, f"Total Views: {cb.graphics_views:,}", ln=True)
    pdf.set_x(x_gra + 2)
    pdf.cell(cat_w - 4, 5, f"Avg Views / Post: {cb.graphics_avg_views:,}", ln=True)

    pdf.set_y(box_y + 38)

    # Content Distribution Bar
    if cb.total_posts > 0:
        bar_w = 180.0
        bar_h = 6.0
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 5, "CONTENT DISTRIBUTION MIX:", ln=True)

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

        pdf.set_y(bar_y + 8)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 4, f"Reels: {cb.reels_count} | Long Videos: {cb.videos_count} | Graphics/Photos: {cb.graphics_count}", ln=True)

    # Optional Ad Account Summary on Page 1 if present
    if ad_report:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 6, "Meta Ads Summary (Optional Campaign Performance)", ln=True)
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
    col_w = [8, 25, 77, 35, 35]
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
            pdf.cell(col_w[0], 10, str(idx + 1), border=0, fill=fill, align="C")

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

            # Caption (truncated)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*NAVY)
            caption = _sanitize(post.message[:50]) + ("..." if len(post.message) > 50 else "")
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

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(40, 40, 40)

    tips = generate_tips(report)
    for tip in tips:
        card_y = pdf.get_y()
        pdf.set_fill_color(*LIGHT_BG)
        pdf.set_draw_color(*BORDER_COLOR)

        # Estimate height
        tip_text = _sanitize(tip)
        pdf.set_xy(15, card_y)
        # Bullet marker
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
