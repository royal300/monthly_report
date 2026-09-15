"""Thin wrapper around the Meta Graph API used by the reporting scripts."""
from __future__ import annotations

import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from typing import Any

import requests

from config import GRAPH_API_BASE, require_token


class GraphAPIError(RuntimeError):
    def __init__(self, message: str, payload: dict | None = None):
        super().__init__(message)
        self.payload = payload or {}


class GraphAPIClient:
    def __init__(self, token: str | None = None, max_retries: int = 3):
        self.token = token or require_token()
        self.max_retries = max_retries
        self.session = requests.Session()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{GRAPH_API_BASE}/{path.lstrip('/')}"
        params = dict(params or {})
        params["access_token"] = self.token

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()

            try:
                err_body = resp.json()
            except ValueError:
                err_body = {"raw": resp.text}

            # Rate limiting (code 4/17/32) -> backoff and retry
            err_code = err_body.get("error", {}).get("code")
            if err_code in (4, 17, 32) and attempt < self.max_retries:
                time.sleep(2 ** attempt)
                last_err = err_body
                continue

            raise GraphAPIError(
                f"Graph API error on {path}: {err_body.get('error', {}).get('message', resp.text)}",
                payload=err_body,
            )

        raise GraphAPIError(f"Graph API failed after retries on {path}", payload=last_err or {})

    # ---- Discovery -------------------------------------------------

    def list_assigned_pages(self) -> list[dict]:
        """Pages this system user has a role on (GET /me/accounts) along with connected Instagram Business Accounts."""
        data = self._get(
            "me/accounts",
            {
                "fields": (
                    "id,name,category,fan_count,"
                    "instagram_business_account{id,username,name,followers_count,media_count,profile_picture_url}"
                )
            },
        )
        return data.get("data", [])

    def get_page_access_token(self, page_id: str) -> str:
        """Page-level insights/content calls require a Page token, not the raw
        system-user token (Graph API error #190 otherwise)."""
        data = self._get("me/accounts", {"fields": "id,access_token"})
        for p in data.get("data", []):
            if p.get("id") == page_id:
                token = p.get("access_token")
                if token:
                    return token
        raise GraphAPIError(
            f"No page access token found for page {page_id} - "
            "check the system user is assigned to this page."
        )

    # ---- Page & Instagram metrics ------------------------------------

    def get_page_info(self, page_id: str) -> dict:
        return self._get(
            page_id,
            {
                "fields": (
                    "id,name,fan_count,followers_count,"
                    "instagram_business_account{id,username,name,followers_count,follows_count,media_count,biography,profile_picture_url}"
                )
            },
        )

    def get_instagram_account_info(self, ig_id: str) -> dict | None:
        """Safely fetch Instagram business profile details."""
        try:
            return self._get(
                ig_id,
                {
                    "fields": "id,username,name,followers_count,follows_count,media_count,biography,profile_picture_url"
                },
            )
        except Exception:
            return None

    def get_instagram_insights(self, ig_id: str, since: str, until: str) -> dict:
        """Fetches total reach, views, interactions, and accounts_engaged for [since, until].
        Splits queries into <=15 day chunks to adhere to Meta's strict 30-day window limit.
        """
        metrics = "reach,views,total_interactions,accounts_engaged"
        combined = {"reach": 0, "views": 0, "total_interactions": 0, "accounts_engaged": 0}

        try:
            start_d = date.fromisoformat(since)
            end_d = date.fromisoformat(until)
        except Exception:
            return combined

        cur = start_d
        while cur <= end_d:
            nxt = min(cur + timedelta(days=14), end_d)
            ts_start = int(datetime.combine(cur, dt_time.min).replace(tzinfo=timezone.utc).timestamp())
            ts_end = int(datetime.combine(nxt, dt_time.max).replace(tzinfo=timezone.utc).timestamp())
            try:
                data = self._get(
                    f"{ig_id}/insights",
                    {
                        "metric": metrics,
                        "metric_type": "total_value",
                        "period": "day",
                        "since": str(ts_start),
                        "until": str(ts_end),
                    },
                )
                for item in data.get("data", []):
                    name = item.get("name")
                    val = item.get("total_value", {}).get("value", 0) or 0
                    if name in combined:
                        combined[name] += val
            except Exception as e:
                print(f"Notice: IG insights chunk query ({cur} to {nxt}) failed: {e}")
            cur = nxt + timedelta(days=1)

        return combined

    def get_instagram_media_with_insights(self, ig_id: str, since: str, until: str, limit: int = 50) -> list[dict]:
        """Fetches Instagram media in [since, until] with view and interaction metrics."""
        try:
            data = self._get(
                f"{ig_id}/media",
                {
                    "fields": (
                        "id,caption,media_type,media_product_type,permalink,timestamp,"
                        "like_count,comments_count"
                    ),
                    "limit": limit,
                },
            )
        except Exception as e:
            print(f"Notice: Instagram media query failed for {ig_id}: {e}")
            return []

        all_media = data.get("data", [])
        filtered = []
        for m in all_media:
            ts = m.get("timestamp", "")
            if ts and len(ts) >= 10:
                pdate = ts[:10]
                if since <= pdate <= until:
                    try:
                        m_ins = self._get(f"{m['id']}/insights", {"metric": "reach,views,saved,shares"})
                        for item in m_ins.get("data", []):
                            m[f"ins_{item.get('name')}"] = item.get("values", [{}])[0].get("value", 0) or 0
                    except Exception:
                        pass
                    filtered.append(m)
        return filtered

    def get_page_insights(self, page_id: str, since: str, until: str) -> dict:
        """since/until are YYYY-MM-DD. Returns raw insights payload.

        Note: page_follows is a cumulative daily snapshot (not a per-day delta) -
        use first/last value to compute growth, don't sum it. page_total_media_view_unique
        is a genuine per-day count and safe to sum. (page_impressions_unique,
        page_post_engagements, page_fan_adds/removes were deprecated by Meta
        on 2026-06-15 - see royal300-meta-reporting-system memory notes.)
        """
        metrics = ",".join([
            "page_follows",
            "page_total_media_view_unique",
            "page_post_engagements",
        ])
        return self._get(
            f"{page_id}/insights",
            {
                "metric": metrics,
                "period": "day",
                "since": since,
                "until": until,
            },
        )

    def get_page_posts_with_insights(self, page_id: str, since: str, until: str, limit: int = 20) -> list[dict]:
        """Returns posts in [since, until] with views/reactions/comments/shares attached.
        Uses adaptive batching (default limit=20) to prevent Meta Graph API complexity limits.
        """
        params = {
            "fields": (
                "id,message,created_time,permalink_url,status_type,"
                "attachments{media_type,type,url},"
                "insights.metric(post_media_view),"
                "reactions.summary(true).limit(0),"
                "comments.summary(true).limit(0),"
                "shares"
            ),
            "since": since,
            "until": until,
            "limit": limit,
        }

        try:
            data = self._get(f"{page_id}/posts", params)
        except GraphAPIError:
            # If Meta asks to reduce the amount of data or hits unexpected error, retry with limit=10
            try:
                params["limit"] = 10
                data = self._get(f"{page_id}/posts", params)
            except GraphAPIError:
                # If nested insights metric is failing on this page, fetch without it as fallback
                params["fields"] = (
                    "id,message,created_time,permalink_url,status_type,"
                    "attachments{media_type,type,url},"
                    "reactions.summary(true).limit(0),"
                    "comments.summary(true).limit(0),"
                    "shares"
                )
                data = self._get(f"{page_id}/posts", params)

        posts = data.get("data", [])

        # Follow pagination if present, capped to avoid runaway calls (up to 10 pages)
        next_url = data.get("paging", {}).get("next")
        pages_fetched = 1
        while next_url and pages_fetched < 10:
            try:
                resp = self.session.get(next_url, timeout=30)
                if resp.status_code == 200:
                    page_data = resp.json()
                    new_posts = page_data.get("data", [])
                    if not new_posts:
                        break
                    posts.extend(new_posts)
                    next_url = page_data.get("paging", {}).get("next")
                    pages_fetched += 1
                else:
                    break
            except Exception:
                break

        return posts

    # ---- Ad account metrics -------------------------------------------

    def get_ad_account_insights(self, ad_account_id: str, since: str, until: str) -> list[dict]:
        """ad_account_id should include the 'act_' prefix."""
        data = self._get(
            f"{ad_account_id}/insights",
            {
                "fields": "impressions,reach,spend,clicks,ctr,cpc",
                "time_range": f'{{"since":"{since}","until":"{until}"}}',
            },
        )
        return data.get("data", [])
