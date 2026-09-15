"""Turns raw Graph API responses into the numbers/structures the PDF needs."""
from __future__ import annotations

from dataclasses import dataclass, field


def _sum_metric(insights_payload: dict, metric_name: str) -> int:
    for entry in insights_payload.get("data", []):
        if entry.get("name") == metric_name:
            return sum(v.get("value", 0) or 0 for v in entry.get("values", []))
    return 0


def _delta_metric(insights_payload: dict, metric_name: str) -> int:
    """For cumulative-snapshot metrics like page_follows: last value minus first."""
    for entry in insights_payload.get("data", []):
        if entry.get("name") == metric_name:
            values = entry.get("values", [])
            if len(values) >= 2:
                return (values[-1].get("value", 0) or 0) - (values[0].get("value", 0) or 0)
    return 0


def _last_snapshot_metric(insights_payload: dict, metric_name: str) -> int | None:
    """For cumulative-snapshot metrics: returns the value at the end of the reporting period."""
    for entry in insights_payload.get("data", []):
        if entry.get("name") == metric_name:
            values = entry.get("values", [])
            if values:
                return values[-1].get("value")
    return None


def _post_metric(post: dict, metric_name: str) -> int:
    for entry in post.get("insights", {}).get("data", []):
        if entry.get("name") == metric_name:
            values = entry.get("values", [])
            if values:
                return values[0].get("value", 0) or 0
    return 0


def _post_interactions(post: dict) -> tuple[int, int, int]:
    """Returns (reactions, comments, shares)."""
    reactions = post.get("reactions", {}).get("summary", {}).get("total_count", 0) or 0
    comments = post.get("comments", {}).get("summary", {}).get("total_count", 0) or 0
    shares = post.get("shares", {}).get("count", 0) or 0
    return reactions, comments, shares


def classify_post(post: dict) -> str:
    """Classifies a Facebook post into 'REEL', 'LONG_VIDEO', or 'GRAPHIC'."""
    permalink = (post.get("permalink_url") or "").lower()
    status_type = (post.get("status_type") or "").lower()
    attachments = post.get("attachments", {}).get("data", [])
    first_att = attachments[0] if attachments else {}
    att_url = (first_att.get("url") or "").lower()
    media_type = (first_att.get("media_type") or "").lower()
    type_ = (first_att.get("type") or "").lower()

    # Reel detection: URL structure or explicit reel type
    if "/reel/" in permalink or "/reel/" in att_url or media_type == "reel" or type_ == "reel":
        return "REEL"

    # Video detection: video attachment or added_video status
    if media_type == "video" or type_ in ("video", "video_inline", "video_autoplay") or status_type == "added_video":
        return "LONG_VIDEO"

    # Default to static graphics/photos/albums
    return "GRAPHIC"


@dataclass
class PostSummary:
    id: str
    message: str
    created_time: str
    permalink_url: str
    content_type: str
    impressions: int
    engaged_users: int
    reactions: int = 0
    comments: int = 0
    shares: int = 0


@dataclass
class ContentBreakdown:
    total_posts: int = 0
    reels_count: int = 0
    reels_views: int = 0
    videos_count: int = 0
    videos_views: int = 0
    graphics_count: int = 0
    graphics_views: int = 0

    @property
    def reels_avg_views(self) -> int:
        return round(self.reels_views / self.reels_count) if self.reels_count else 0

    @property
    def videos_avg_views(self) -> int:
        return round(self.videos_views / self.videos_count) if self.videos_count else 0

    @property
    def graphics_avg_views(self) -> int:
        return round(self.graphics_views / self.graphics_count) if self.graphics_count else 0


@dataclass
class MetricComparison:
    current: float | int
    previous: float | int
    delta: float | int
    pct_change: float | None

    @property
    def formatted_pct(self) -> str:
        if self.pct_change is None:
            return "N/A"
        sign = "+" if self.pct_change > 0 else ""
        return f"{sign}{self.pct_change:.1f}%"


def _compare_metric(current: float | int, previous: float | int | None) -> MetricComparison:
    if previous is None:
        return MetricComparison(current=current, previous=0, delta=0, pct_change=None)
    delta = current - previous
    if previous == 0:
        pct = 100.0 if current > 0 else (0.0 if current == 0 else -100.0)
    else:
        pct = (delta / abs(previous)) * 100.0
    return MetricComparison(current=current, previous=previous, delta=delta, pct_change=pct)


@dataclass
class InstagramAccountSummary:
    id: str
    username: str
    name: str = ""
    followers: int = 0
    media_count: int = 0
    biography: str = ""


@dataclass
class PageReport:
    page_id: str
    page_name: str
    followers: int
    period_since: str
    period_until: str
    impressions: int = 0
    engagement: int = 0
    post_interactions: int = 0
    follower_delta: int = 0
    top_posts: list[PostSummary] = field(default_factory=list)
    content_breakdown: ContentBreakdown = field(default_factory=ContentBreakdown)
    previous_period: PageReport | None = None
    instagram: InstagramAccountSummary | None = None

    @property
    def net_growth(self) -> int:
        return self.follower_delta

    @property
    def engagement_rate(self) -> float:
        if not self.impressions:
            return 0.0
        return round((self.engagement / self.impressions) * 100, 2)

    @property
    def mom_followers(self) -> MetricComparison:
        prev = self.previous_period.followers if self.previous_period else None
        return _compare_metric(self.followers, prev)

    @property
    def mom_growth(self) -> MetricComparison:
        prev = self.previous_period.net_growth if self.previous_period else None
        return _compare_metric(self.net_growth, prev)

    @property
    def mom_impressions(self) -> MetricComparison:
        prev = self.previous_period.impressions if self.previous_period else None
        return _compare_metric(self.impressions, prev)

    @property
    def mom_engagement(self) -> MetricComparison:
        prev = self.previous_period.engagement if self.previous_period else None
        return _compare_metric(self.engagement, prev)

    @property
    def mom_engagement_rate(self) -> MetricComparison:
        prev = self.previous_period.engagement_rate if self.previous_period else None
        return _compare_metric(self.engagement_rate, prev)

    @property
    def mom_posts(self) -> MetricComparison:
        prev = self.previous_period.content_breakdown.total_posts if self.previous_period else None
        return _compare_metric(self.content_breakdown.total_posts, prev)


@dataclass
class AdAccountReport:
    account_id: str
    account_name: str
    impressions: int
    reach: int
    spend: float
    clicks: int
    ctr: float
    cpc: float


def build_page_report(page_id: str, page_name: str, page_info: dict,
                       insights_payload: dict, posts: list[dict],
                       since: str, until: str, top_n: int = 5,
                       instagram_data: dict | None = None) -> PageReport:
    # 1. Followers: Use the exact snapshot at month-end from page_follows if present,
    # otherwise fallback to live page_info
    month_end_followers = _last_snapshot_metric(insights_payload, "page_follows")
    if month_end_followers is None:
        month_end_followers = page_info.get("followers_count") or page_info.get("fan_count") or 0

    ig_raw = instagram_data or page_info.get("instagram_business_account")
    ig_summary = None
    if ig_raw and isinstance(ig_raw, dict) and ig_raw.get("id"):
        ig_summary = InstagramAccountSummary(
            id=str(ig_raw.get("id", "")),
            username=str(ig_raw.get("username", "")),
            name=str(ig_raw.get("name", "") or ig_raw.get("username", "")),
            followers=int(ig_raw.get("followers_count", 0) or 0),
            media_count=int(ig_raw.get("media_count", 0) or 0),
            biography=str(ig_raw.get("biography", "") or ""),
        )

    report = PageReport(
        page_id=page_id,
        page_name=page_name,
        followers=month_end_followers,
        period_since=since,
        period_until=until,
        impressions=_sum_metric(insights_payload, "page_total_media_view_unique"),
        follower_delta=_delta_metric(insights_payload, "page_follows"),
        instagram=ig_summary,
    )

    summarized: list[PostSummary] = []
    breakdown = ContentBreakdown()

    for post in posts:
        ctype = classify_post(post)
        views = _post_metric(post, "post_media_view")
        rx, cm, sh = _post_interactions(post)
        engaged = rx + cm + sh

        breakdown.total_posts += 1
        if ctype == "REEL":
            breakdown.reels_count += 1
            breakdown.reels_views += views
        elif ctype == "LONG_VIDEO":
            breakdown.videos_count += 1
            breakdown.videos_views += views
        else:
            breakdown.graphics_count += 1
            breakdown.graphics_views += views

        summarized.append(PostSummary(
            id=post.get("id", ""),
            message=(post.get("message") or "(no caption)")[:140],
            created_time=post.get("created_time", ""),
            permalink_url=post.get("permalink_url", ""),
            content_type=ctype,
            impressions=views,
            engaged_users=engaged,
            reactions=rx,
            comments=cm,
            shares=sh,
        ))

    report.content_breakdown = breakdown
    report.post_interactions = sum(p.engaged_users for p in summarized)

    # Official Page Engagement from Meta Business Suite dashboard (page_post_engagements)
    page_level_engagements = _sum_metric(insights_payload, "page_post_engagements")
    if page_level_engagements > 0:
        report.engagement = page_level_engagements
    else:
        report.engagement = report.post_interactions

    summarized.sort(key=lambda p: (p.impressions, p.engaged_users), reverse=True)
    report.top_posts = summarized[:top_n]
    return report


def build_ad_account_report(account_id: str, account_name: str, insights_rows: list[dict]) -> AdAccountReport | None:
    if not insights_rows:
        return None
    row = insights_rows[0]
    return AdAccountReport(
        account_id=account_id,
        account_name=account_name,
        impressions=int(row.get("impressions", 0) or 0),
        reach=int(row.get("reach", 0) or 0),
        spend=float(row.get("spend", 0) or 0),
        clicks=int(row.get("clicks", 0) or 0),
        ctr=float(row.get("ctr", 0) or 0),
        cpc=float(row.get("cpc", 0) or 0),
    )


def generate_tips(report: PageReport) -> list[str]:
    tips = []
    cb = report.content_breakdown

    # 1. MoM Trends
    if report.previous_period:
        mom_views = report.mom_impressions
        if mom_views.pct_change is not None:
            if mom_views.pct_change >= 10:
                tips.append(
                    f"Views surged by {mom_views.formatted_pct} MoM ({report.impressions:,} vs "
                    f"{report.previous_period.impressions:,}). Keep following this month's winning publishing cadence."
                )
            elif mom_views.pct_change <= -10:
                tips.append(
                    f"Views decreased by {mom_views.formatted_pct} compared to last month. "
                    "Re-evaluate posting frequency and test posting during peak evening audience hours."
                )

    # 2. Content Type Distribution & Best Format
    avg_reels = cb.reels_avg_views
    avg_graphics = cb.graphics_avg_views
    avg_videos = cb.videos_avg_views

    if cb.reels_count > 0 and (avg_reels >= avg_graphics and avg_reels >= avg_videos):
        tips.append(
            f"Reels were your top-performing format, averaging {avg_reels:,} views/post (vs "
            f"{avg_graphics:,} for graphics). We recommend aiming for at least 3-4 Reels per week."
        )
    elif cb.reels_count == 0 and cb.total_posts > 0:
        tips.append(
            "Zero Reels were published this month. Meta algorithm strongly favors vertical short video "
            "— introducing 2-3 Reels per week can significantly increase discovery beyond existing followers."
        )
    elif cb.graphics_count > 0 and avg_graphics > avg_reels:
        tips.append(
            f"Graphics/Carousels performed well with {avg_graphics:,} average views. "
            "Carousels with informational slides or customer stories tend to retain attention longest."
        )

    # 3. Follower Growth & Engagement
    if report.net_growth < 0:
        tips.append(
            "Follower count had a net decline. Review recent post topics for brand alignment and "
            "engage directly in the comments of industry/local pages to regain visibility."
        )
    elif report.net_growth >= 20:
        tips.append(
            f"Solid follower expansion (+{report.net_growth:,} net new followers). Continue the content theme "
            "that contributed to this momentum."
        )

    if report.engagement_rate < 1.0:
        tips.append(
            f"Engagement rate is {report.engagement_rate}%. Incorporate clear calls-to-action (CTAs), questions, "
            "and prompt discussions in the first two lines of your captions to drive comments."
        )
    elif report.engagement_rate >= 3.0:
        tips.append(
            f"Strong engagement rate of {report.engagement_rate}%. Your audience is highly active — this is an ideal "
            "time to run promotional offers or pin your highest-converting post."
        )

    # 4. Top Post insight
    if report.top_posts:
        best = report.top_posts[0]
        type_label = best.content_type.replace("_", " ").title()
        tips.append(
            f"Top post of the month was a {type_label} with {best.impressions:,} views and {best.engaged_users:,} "
            f"interactions. Analyze its hook and structure to replicate in upcoming content."
        )

    # 5. Connected Instagram Synergy
    if report.instagram:
        tips.append(
            f"Instagram account @{report.instagram.username} is connected ({report.instagram.followers:,} followers). "
            f"Cross-posting top-performing Facebook Reels directly as Instagram Reels with relevant hashtags will maximize total Meta ecosystem reach."
        )

    return tips
