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


def _post_metric(post: dict, metric_name: str) -> int:
    for entry in post.get("insights", {}).get("data", []):
        if entry.get("name") == metric_name:
            values = entry.get("values", [])
            if values:
                return values[0].get("value", 0) or 0
    return 0


def _post_engagement(post: dict) -> int:
    """Reactions + comments + shares, read from their own edges (not insights)."""
    reactions = post.get("reactions", {}).get("summary", {}).get("total_count", 0) or 0
    comments = post.get("comments", {}).get("summary", {}).get("total_count", 0) or 0
    shares = post.get("shares", {}).get("count", 0) or 0
    return reactions + comments + shares


@dataclass
class PostSummary:
    id: str
    message: str
    created_time: str
    permalink_url: str
    impressions: int
    engaged_users: int


@dataclass
class PageReport:
    page_id: str
    page_name: str
    followers: int
    period_since: str
    period_until: str
    impressions: int = 0
    engagement: int = 0
    follower_delta: int = 0
    top_posts: list[PostSummary] = field(default_factory=list)

    @property
    def net_growth(self) -> int:
        return self.follower_delta

    @property
    def engagement_rate(self) -> float:
        if not self.impressions:
            return 0.0
        return round((self.engagement / self.impressions) * 100, 2)


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
                       since: str, until: str, top_n: int = 5) -> PageReport:
    report = PageReport(
        page_id=page_id,
        page_name=page_name,
        followers=page_info.get("followers_count") or page_info.get("fan_count") or 0,
        period_since=since,
        period_until=until,
        impressions=_sum_metric(insights_payload, "page_total_media_view_unique"),
        follower_delta=_delta_metric(insights_payload, "page_follows"),
    )

    summarized = []
    for post in posts:
        summarized.append(PostSummary(
            id=post.get("id", ""),
            message=(post.get("message") or "(no caption)")[:120],
            created_time=post.get("created_time", ""),
            permalink_url=post.get("permalink_url", ""),
            impressions=_post_metric(post, "post_media_view"),
            engaged_users=_post_engagement(post),
        ))
    report.engagement = sum(p.engaged_users for p in summarized)

    summarized.sort(key=lambda p: p.impressions, reverse=True)
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

    if report.net_growth < 0:
        tips.append(
            "Follower count declined this period. Review recent posts for tone/relevance, "
            "and consider a small boosted-post budget to recover momentum."
        )
    elif report.net_growth == 0:
        tips.append(
            "Follower growth was flat. Try posting at more consistent times and experiment "
            "with Reels/short video, which typically reach non-followers more than static posts."
        )
    else:
        tips.append(
            f"Gained {report.net_growth} net followers this period — keep the posting "
            "cadence that drove it and double down on your best-performing format below."
        )

    if report.engagement_rate < 1.0:
        tips.append(
            "Engagement rate is under 1%, which is low for this follower size. Ask questions "
            "in captions, reply to comments quickly, and post when your audience is most active."
        )
    elif report.engagement_rate < 3.0:
        tips.append(
            "Engagement rate is decent but has room to grow — try more carousel posts or "
            "behind-the-scenes content, which tends to outperform pure promotional posts."
        )
    else:
        tips.append("Engagement rate is strong this period — this audience is responsive, worth testing paid boosts on top posts.")

    if report.top_posts:
        best = report.top_posts[0]
        tips.append(
            f"Your top post this period got {best.impressions:,} impressions — "
            "look at what made it work (format, timing, topic) and repeat that pattern."
        )

    return tips
