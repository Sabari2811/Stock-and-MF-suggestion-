from __future__ import annotations

import feedparser
from urllib.parse import quote


def google_news(query: str, limit: int = 10) -> list[dict]:
    url = "https://news.google.com/rss/search?q=" + quote(query) + "&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)
    return [{"title": e.get("title", ""), "link": e.get("link", ""),
             "published": e.get("published", ""), "summary": e.get("summary", "")} for e in feed.entries[:limit]]


def classify_headline(title: str) -> str:
    t = title.lower()
    positive = ["beats", "profit rises", "order win", "upgrade", "buyback", "approval", "growth", "record"]
    negative = ["falls", "misses", "downgrade", "fraud", "penalty", "probe", "loss", "cut", "default"]
    if any(k in t for k in positive): return "POSITIVE"
    if any(k in t for k in negative): return "NEGATIVE"
    return "NEUTRAL"
