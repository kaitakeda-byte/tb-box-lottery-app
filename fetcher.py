"""SocialData API でハッシュタグ投稿取得"""
from __future__ import annotations

import os
import time
from datetime import date, timedelta
from typing import Iterator

import httpx

HASHTAG = "#トレカバンク郵送買取"
SELF_MENTIONS = "-@torecabank -@torecabank2 -@torecabank_yuso -@torecabank3"
SELF_FROM = "-from:torecabank -from:torecabank2 -from:torecabank_yuso -from:torecabank3"
SD_FILTERS = f"-filter:retweets {SELF_MENTIONS} {SELF_FROM}"


def _fetch_day(client: httpx.Client, d: date, api_key: str, progress=print) -> list[dict]:
    next_d = d + timedelta(days=1)
    query = f"{HASHTAG} {SD_FILTERS} since:{d.isoformat()} until:{next_d.isoformat()}"
    headers = {"Authorization": f"Bearer {api_key}"}
    seen_ids = set()
    out: list[dict] = []
    cursor = None
    page = 0
    consecutive_no_new = 0
    MAX_PAGES = 50
    while page < MAX_PAGES:
        page += 1
        params = {"query": query}
        if cursor:
            params["cursor"] = cursor
        r = client.get(
            "https://api.socialdata.tools/twitter/search",
            headers=headers, params=params,
        )
        if r.status_code == 402:
            raise RuntimeError("SocialData balance low")
        r.raise_for_status()
        data = r.json()
        batch = data.get("tweets", [])
        new_in_batch = 0
        for t in batch:
            tid = t.get("id_str") or str(t.get("id", ""))
            if tid and tid not in seen_ids:
                seen_ids.add(tid)
                out.append(t)
                new_in_batch += 1
        if not batch:
            break
        if new_in_batch == 0:
            consecutive_no_new += 1
            if consecutive_no_new >= 2:
                break
        else:
            consecutive_no_new = 0
        cursor = data.get("next_cursor")
        if not cursor:
            break
        time.sleep(0.4)
    progress(f"  {d.isoformat()}: {len(out)}件取得")
    return out


def fetch_range(start: date, end_inclusive: date, progress=print) -> list[dict]:
    api_key = os.environ["SOCIALDATA_API_KEY"]
    seen: dict[str, dict] = {}
    progress(f"取得期間: {start} 〜 {end_inclusive}")
    with httpx.Client(timeout=30) as client:
        d = start
        while d <= end_inclusive:
            tweets = _fetch_day(client, d, api_key, progress)
            for t in tweets:
                tid = t.get("id_str") or str(t.get("id", ""))
                if tid:
                    seen[tid] = t
            d += timedelta(days=1)
            time.sleep(0.3)

    rows = []
    for tid, t in seen.items():
        u = t.get("user", {}) or {}
        sn = u.get("screen_name", "")
        rows.append({
            "id": tid,
            "created_at": t.get("tweet_created_at") or t.get("created_at", ""),
            "screen_name": sn,
            "user_name": u.get("name", ""),
            "user_followers": u.get("followers_count", 0),
            "url": f"https://x.com/{sn}/status/{tid}" if sn else "",
            "text": (t.get("full_text") or t.get("text", "")).replace("\n", " / "),
        })
    rows.sort(key=lambda r: r["created_at"])
    progress(f"合計: {len(rows)}件 (ユニーク)")
    return rows
