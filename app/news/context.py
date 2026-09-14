from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import feedparser


def google_news(query: str, limit: int = 10, max_age_days: int = 7) -> list[dict]:
    url = "https://news.google.com/rss/search?q=" + quote(query) + "&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    out = []
    for e in feed.entries:
        title = e.get("title", "")
        published = e.get("published", "")
        dt = None
        try:
            dt = parsedate_to_datetime(published).astimezone(timezone.utc)
        except Exception:
            pass
        if dt is not None and dt < cutoff:
            continue
        out.append({
            "title": title,
            "link": e.get("link", ""),
            "published": published,
            "summary": e.get("summary", ""),
        })
        if len(out) >= limit:
            break
    return out


def classify_headline(title: str) -> str:
    t = title.lower()
    positive = ["beats", "profit rises", "order win", "upgrade", "buyback", "approval", "growth", "record", "strong demand"]
    negative = ["falls", "misses", "downgrade", "fraud", "penalty", "probe", "loss", "cut", "default", "warning", "weak demand"]
    if any(k in t for k in positive):
        return "POSITIVE"
    if any(k in t for k in negative):
        return "NEGATIVE"
    return "NEUTRAL"
