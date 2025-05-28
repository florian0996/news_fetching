#!/usr/bin/env python3
# coding: utf-8

import os
import json
import requests
import feedparser
from datetime import datetime
from pathlib import Path

import yake
from bs4 import BeautifulSoup
from dateutil import parser

# ── CONFIG ────────────────────────────────────────────────────────────────
NEWSAPI_KEY     = "186dd4ccd2234f6a89f850bf16effb06"
QUERY           = (
    "credit OR loan OR Exaloan OR lending OR fintech startup OR digital lending OR credit platform "
    "OR loan service OR peer-to-peer lending OR online loan platform OR investment platform "
    "OR digital wealth management OR fractional investing OR seed funding OR fintech VC OR risk assessment"
)
QUERY_short     = "credit OR loan OR Exaloan OR lending"
LANGUAGE        = "en"
PAGE_SIZE       = 100
ENABLE_FILTERING = False  # toggle to True if you want QUERY-based filtering
# ──────────────────────────────────────────────────────────────────────────

kw_extractor = yake.KeywordExtractor(lan="en", n=1, top=10)

def extract_keywords(text: str) -> list[str]:
    if not text:
        return []
    keywords = kw_extractor.extract_keywords(text)
    return [kw for kw, score in keywords]

def matches_query(text: str, query: str) -> bool:
    terms = [t.strip().lower() for t in query.split("OR")]
    text_lower = text.lower()
    return any(term in text_lower for term in terms)

def apply_query_filter(articles: list[dict]) -> list[dict]:
    if not ENABLE_FILTERING:
        return articles
    filtered = [
        a for a in articles
        if matches_query(a.get("title", "") + " " + a.get("content", ""), QUERY)
    ]
    print(f"→ {len(filtered)} articles after filtering.")
    return filtered

# ── FETCH FUNCTIONS ───────────────────────────────────────────────────────

def fetch_bloomberg_rss() -> list[dict]:
    RSS_FEEDS = {
        "Markets":   "https://feeds.bloomberg.com/markets/news.rss",
        "Politics":  "https://feeds.bloomberg.com/politics/news.rss",
        "Business":  "https://feeds.bloomberg.com/business/news.rss",
        "Technology":"https://feeds.bloomberg.com/technology/news.rss",
        "Economics": "https://feeds.bloomberg.com/economics/news.rss",
        "Industries":"https://feeds.bloomberg.com/industries/news.rss"
    }
    print("Fetching Bloomberg RSS feeds…")
    articles = []
    for name, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for e in feed.entries:
            content = getattr(e, "summary", e.get("description", ""))
            articles.append({
                "source": f"Bloomberg – {name} [RSS]",
                "url": e.link,
                "title": e.title,
                "published_at": getattr(e, "published", ""),
                "content": content,
                "platforms_mentioned": [],
            })
    print(f"→ Bloomberg RSS: {len(articles)} fetched.")
    return apply_query_filter(articles)

def fetch_newsapi() -> list[dict]:
    print("Fetching from NewsAPI…")
    resp = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q":        "lending OR credit",
            "language": LANGUAGE,
            "pageSize": PAGE_SIZE,
            "sortBy":   "publishedAt",
            "apiKey":   NEWSAPI_KEY,
        }
    )
    if resp.status_code != 200:
        print(f"NewsAPI error: {resp.status_code} – {resp.text}")
        return []
    raw = resp.json().get("articles", [])
    print(f"→ NewsAPI: {len(raw)} fetched.")
    articles = [
        {
            "source":            f"{a['source']['name']} [NewsAPI]",
            "url":               a["url"],
            "title":             a["title"],
        }]
