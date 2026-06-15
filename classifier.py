"""投稿分類: HARD_NEG / SOFT_NEG / EMPTY / CLEAN"""
from __future__ import annotations

import re

HARD_NEG = ["返却", "返品", "成立にはなりません", "基準外", "凹み", "ダウン", "買取不可", "謎の", "嫌な"]
SOFT_NEG = [
    "減額あり", "減額され", "減額ありました", "減額ですが", "減額少なく",
    "ほぼ満額", "9割満額", "基本満額",
    "残念でしたが", "再開してくれない", "下がってた",
]


def is_empty_post(text: str) -> bool:
    t = re.sub(r"https?://\S+", "", text)
    t = t.replace("#トレカバンク郵送買取", "")
    t = t.replace("「", "").replace("」", "").replace("/", "").strip()
    return len(t) < 10


def classify(text: str) -> str:
    if any(k in text for k in HARD_NEG):
        return "HARD_NEG"
    if any(k in text for k in SOFT_NEG):
        return "SOFT_NEG"
    if is_empty_post(text):
        return "EMPTY"
    return "CLEAN"


def split_pool(rows: list[dict], past_winners: set[str]) -> dict:
    """投稿リストを既当選者/除外/グレー/クリーンに分類"""
    clean_users: dict[str, list[dict]] = {}
    excluded: list[tuple[str, dict]] = []
    gray: list[dict] = []
    past_winner_posts: list[dict] = []

    for r in rows:
        sn = (r.get("screen_name") or "").strip()
        if not sn:
            continue
        c = classify(r.get("text", ""))
        if sn in past_winners:
            past_winner_posts.append(r)
            continue
        if c in ("HARD_NEG", "EMPTY"):
            excluded.append((c, r))
            continue
        if c == "SOFT_NEG":
            gray.append(r)
            continue
        clean_users.setdefault(sn, []).append(r)

    return {
        "clean_users": clean_users,
        "excluded": excluded,
        "gray": gray,
        "past_winner_posts": past_winner_posts,
    }
