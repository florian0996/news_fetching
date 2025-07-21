#!/usr/bin/env python
# coding: utf-8

import os
import json
import requests
import feedparser
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path


import yake
kw_extractor = yake.KeywordExtractor(lan="en", n=1, top=10)
def extract_keywords(text):
    if not text:
        return []
    keywords = kw_extractor.extract_keywords(text)
    return [kw for kw, score in keywords]

def matches_query(text, query):
    query_terms = [term.strip().lower() for term in query.split("OR")]
    text_lower = text.lower()
    return any(term in text_lower for term in query_terms)


# ========== CONFIG ==========
NEWSAPI_KEY = "186dd4ccd2234f6a89f850bf16effb06"
LANGUAGE = "en"
PAGE_SIZE = 100
ENABLE_FILTERING = False  # Set to False to bypass QUERY-based filtering

TERMS = [
    "credit", "loan", "Exaloan", "lending", "fintech startup",
    "digital lending", "credit platform", "loan service",
    "peer-to-peer lending", "online loan platform", "investment platform",
    "digital wealth management", "fractional investing", "seed funding",
    "fintech VC", "risk assessment"
]

# the OR-joined string you use in apply_query_filter():
QUERY = " OR ".join(TERMS)

RUN_DATE = datetime.now().strftime("%Y-%m-%d")

def apply_query_filter(articles):
    """
    Filters a list of article dicts based on the global QUERY if ENABLE_FILTERING is True.
    """
    # if the switch is off, skip all filtering
    if not ENABLE_FILTERING:
        return articles

    # otherwise, only keep articles whose title+content match at least one OR-term
    filtered = [
        a for a in articles
        if matches_query(
            a.get("title", "") + " " + a.get("content", ""),
            QUERY
        )
    ]
    print(f"→ {len(filtered)} articles after filtering.")
    return filtered

RSS_FEEDS = {
    "Markets":   "https://feeds.bloomberg.com/markets/news.rss",
    "Politics":  "https://feeds.bloomberg.com/politics/news.rss",
    "Business":  "https://feeds.bloomberg.com/business/news.rss",
    "Technology":"https://feeds.bloomberg.com/technology/news.rss",
    "Economics": "https://feeds.bloomberg.com/economics/news.rss",
    "Industries":"https://feeds.bloomberg.com/industries/news.rss"
}

# ========== FINANZEN.NET FETCH ==========
FINANZEN_FEED_URL = "https://www.finanzen.net/rss/news"

def fetch_finanzen_net():
    print("→ Fetching Finanzen.net RSS feed…")
    feed = feedparser.parse(FINANZEN_FEED_URL)
    articles = []
    for e in feed.entries:
        title = e.title
        content = getattr(e, 'summary', '')
        now = datetime.now(timezone.utc).isoformat()
        articles.append({
            "source": "Finanzen.net [RSS]",
            "url": e.link,
            "title": title,
            "fetched_on": now,
            "content": content,
            "platforms_mentioned": []
        })
    print(f"→ Finanzen.net: {len(articles)} articles fetched.")
    return apply_query_filter(articles)


# ========== BLOOMBERG RSS FETCH ==========
def fetch_bloomberg_rss():
    print("Fetching Bloomberg RSS feeds...")
    all_articles = []
    for name, feed_url in RSS_FEEDS.items():
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            content = getattr(entry, 'summary', entry.get('description', ''))
            now = datetime.now(timezone.utc).isoformat()
            all_articles.append({
                "source":         f"Bloomberg – {name} [RSS]",
                "url":            entry.link,
                "title":          entry.title,
                "fetched_on":     now,
                "content":        content,
                "platforms_mentioned": [],
            })
    print(f"→ Bloomberg RSS: {len(all_articles)} articles fetched.")

    # ——— apply QUERY-based filtering if ENABLE_FILTERING is True ———
    return apply_query_filter(all_articles)


# ========== NEWSAPI FETCH ==========
def fetch_newsapi():
    print("Fetching from NewsAPI...")
    now = datetime.now(timezone.utc).isoformat()
    url = "https://newsapi.org/v2/everything"
    params = {
        "q":        "lending OR credit",
        "language": LANGUAGE,
        "pageSize": PAGE_SIZE,
        "sortBy":   "publishedAt",
        "apiKey":   NEWSAPI_KEY,
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"NewsAPI error: {response.status_code} – {response.text}")
        return []

    raw = response.json().get("articles", [])
    print(f"→ NewsAPI: {len(raw)} articles fetched.")

    # build our uniform article dicts
    all_articles = [
        {
            "source":            f"{a['source']['name']} [NewsAPI]",
            "url":               a["url"],
            "title":             a["title"],
            "fetched_on":        now,
            "content":           a.get("content") or a.get("description", ""),
            "platforms_mentioned": [],
        }
        for a in raw
    ]

    # apply QUERY-based filtering if ENABLE_FILTERING is True
    return apply_query_filter(all_articles)


# ========== SEC FETCH ==========
def fetch_sec_press_releases():
    RSS_URL = "https://www.sec.gov/news/pressreleases.rss"
    feed = feedparser.parse(RSS_URL)

    entries = []
    for e in feed.entries:
        now = datetime.now(timezone.utc).isoformat()
        entries.append({
            "source":            "SEC Press Releases [RSS]",
            "url":               e.link,
            "title":             e.title,
            "fetched_on":        now,
            "content":           e.get("summary", ""),
            "platforms_mentioned": [],
        })

    print(f"→ SEC Press Releases: {len(entries)} fetched.")
    # apply QUERY-based filtering if ENABLE_FILTERING is True
    return apply_query_filter(entries)


# ========== GNEWS FETCH ==========
#  GNews configuration
# ---------------------------------------------------------------------------
def chunk_queries(terms: list[str], max_len: int = 180) -> list[str]:
    """
    Build OR-joined query strings under max_len chars each.
    """
    chunks: list[list[str]] = []
    current: list[str] = []

    for term in terms:
        candidate = " OR ".join(current + [term])
        if len(candidate) <= max_len:
            current.append(term)
        else:
            chunks.append(current)
            current = [term]

    if current:
        chunks.append(current)

    # return list of joined strings
    return [" OR ".join(chunk) for chunk in chunks]

GNEWS_QUERIES = chunk_queries(TERMS, max_len=180)

GNEWS_API_KEY = os.getenv(
    "GNEWS_API_KEY", "c4f8fe7bbdaea71cd2ec22279906c40f")

def fetch_gnews(QUERY: str, *, max_results: int = PAGE_SIZE) -> list[dict]:
    print(f"Fetching from GNews (q={QUERY[:50]}…)")
    url = "https://gnews.io/api/v4/search"
    params = {"q": QUERY, "in": "title,description", "lang": LANGUAGE,
              "country": "us", "max": max_results, "token": GNEWS_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=10)
    except Exception as e:
        print(f"GNews request error: {e}")
        return []
    if resp.status_code != 200:
        print(f"GNews error {resp.status_code}: {resp.text[:200]} …")
        return []
    raw = resp.json().get("articles", [])
    print(f"→ GNews: {len(raw)} articles fetched.")
    out = []
    for a in raw:
        src = a.get("source",{}).get("name","Unknown")
        now = datetime.now(timezone.utc).isoformat()
        out.append({
            "source":         f"{src} [GNews]",
            "url":            a.get("url",""),
            "title":          a.get("title",""),
            "fetched_on":     now,
            "content":        a.get("description","") or a.get("content",""),
            "platforms_mentioned": [],
        })
    return apply_query_filter(out)                              

def run_gnews_for_all_entities():
    """
    Read Master_Entities_Table - Originator_Platforms_Funds_and_Competitors.csv
    and pull GNews for each entity based on their aliases.
    """
    ENTITIES_CSV = Path("data/Master_Entities_Table - Originator_Platforms_Funds_and_Competitors.csv")
    if not ENTITIES_CSV.exists():
        raise FileNotFoundError(
            f"{ENTITIES_CSV} not found.  Make sure the path is correct."
        )

    # Read all entities
    df = pd.read_csv(ENTITIES_CSV, dtype=str).fillna("")

    # (Optional) Only include platforms, funds, etc.
    # df = df[df["category"] == "Platform"]

    print(f"▶ GNews: fetching {len(df)} entities …")
    gnews_articles = []

    for _, row in df.iterrows():
        entity = row["entity_name"].strip()
        # build a query out of all aliases
        aliases = [a.strip() for a in row["aliases"].split(";") if a.strip()]
        if not aliases:
            continue
        query_str = " OR ".join(aliases)

        # fetch and tag
        arts = fetch_gnews(query_str)
        for art in arts:
            art["entity"] = entity
        gnews_articles.extend(arts)

    print(f"→ GNews total: {len(gnews_articles)} articles across {len(df)} entities.")
    return gnews_articles


# ========== INVESTING.COM RSS FETCH ==========
def fetch_investing_rss():
    print("Fetching Investing.com RSS feeds...")
    feeds = {
        "Investing.com (English) [RSS]": "https://www.investing.com/rss/news_25.rss?limit=20",
        "Investing.com (German)  [RSS]": "https://de.investing.com/rss/news_95.rss"
    }

    articles = []
    for label, feed_url in feeds.items():
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            now = datetime.now(timezone.utc).isoformat()
            articles.append({
                "source":             label,
                "url":                entry.link,
                "title":              entry.title,
                "fetched_on":         now,
                "content":            entry.get("summary", ""),
                "platforms_mentioned": [],
            })

    print(f"→ Investing.com RSS: {len(articles)} articles fetched.")

    # apply QUERY-based filtering if ENABLE_FILTERING is True
    return apply_query_filter(articles)


# ========== CRUNCHBASE FETCH ==========
import requests, json
from bs4 import BeautifulSoup
from dateutil import parser

def fetch_crunchbase_sections():
    """
    Scrape three Crunchbase News sections and deep‑fetch each
    article’s JSON‑LD to extract a proper published_at and content.
    """
    BASE_URL = "https://news.crunchbase.com"
    sections = [
        {
            "label": "Crunchbase News – Fintech [Scrape]",
            "url": f"{BASE_URL}/sections/fintech-ecommerce/",
            "keywords": {"lending", "credit", "finance", "regulation", "regulations"},
        },
        {
            "label": "Crunchbase News – IPO [Scrape]",
            "url": f"{BASE_URL}/sections/public/ipo/",
            "keywords": None,
        },
        {
            "label": "Crunchbase News – Seed Funding [Scrape]",
            "url": f"{BASE_URL}/sections/seed/",
            "keywords": None,
        },
    ]

    headers = {"User-Agent": "Mozilla/5.0"}
    articles = []

    for sec in sections:
        section_resp = requests.get(sec["url"], headers=headers)
        section_resp.raise_for_status()
        soup = BeautifulSoup(section_resp.text, "lxml")

        # each H2 with a link is one article teaser on the section page
        for h2 in soup.find_all("h2"):
            link_tag = h2.find("a", href=True)
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            href  = link_tag["href"]
            url   = href if href.startswith("http") else (BASE_URL + href)

            # now deep‑fetch the article page
            art = requests.get(url, headers=headers)
            art.raise_for_status()
            art_soup = BeautifulSoup(art.text, "lxml")

            # find the JSON‑LD with "@type": "NewsArticle"
            published_iso = ""
            content_snip = ""
            for script in art_soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                except Exception:
                    continue

                # handle list or single object
                if isinstance(data, list):
                    # find the NewsArticle entry
                    for entry in data:
                        if entry.get("@type") == "NewsArticle":
                            data = entry
                            break
                if data.get("@type") != "NewsArticle":
                    continue

                # extract publish date
                dp = data.get("datePublished") or data.get("uploadDate")
                if dp:
                    try:
                        # normalize to ISO 8601 UTC
                        dt = parser.isoparse(dp)
                        published_iso = dt.date().isoformat() 
                    except Exception:
                        ppublished_iso = dp.split("T")[0] if "T" in dp else dp
                # extract a snippet: articleBody is full text, description is summary
                content_snip = data.get("description") or data.get("articleBody","")
                break  # stop after first NewsArticle

            # if JSON-LD failed, you could fallback to section‑page teaser
            if not content_snip:
                p = h2.find_next_sibling("p")
                content_snip = p.get_text(strip=True) if p else ""

            # apply your keyword filter only on Fintech section
            if sec["keywords"]:
                txt = (title + " " + content_snip).lower()
                if not any(k in txt for k in sec["keywords"]):
                    continue

            now = datetime.now(timezone.utc).isoformat()
            articles.append({
                "source":        sec["label"],
                "url":           url,
                "title":         title,
                "fetched_on":    now,
                "content":       content_snip,
                "platforms_mentioned": [],
            })

    print(f"→ Crunchbase News (all sections): {len(articles)} fetched.")
    # apply QUERY-based filtering if ENABLE_FILTERING is True
    return apply_query_filter(articles)


CNBC_RSS_FEEDS = {
    "CNBC Top News":      "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "CNBC Markets":       "https://www.cnbc.com/id/19746125/device/rss/rss.html",
    "CNBC Technology":    "https://www.cnbc.com/id/10000115/device/rss/rss.html",
    "CNBC Finance":       "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "CNBC Personal Fin.": "https://www.cnbc.com/id/21324812/device/rss/rss.html",
}

def fetch_cnbc_rss():
    print("Fetching CNBC RSS feeds…")
    articles = []

    for label, url in CNBC_RSS_FEEDS.items():
        feed = feedparser.parse(url)
        if getattr(feed, "bozo", False):
            print(f"  ⚠️  Failed to parse {label}: {feed.bozo_exception}")
            continue

        for entry in feed.entries:
            # fallback logic for summary/description/published date
            summary = getattr(entry, "summary", "")
            if not summary:
                summary = entry.get("description", "")
            published = getattr(entry, "published", entry.get("pubDate", ""))

            now = datetime.now(timezone.utc).isoformat()
            articles.append({
                "source":           f"{label} [RSS]",
                "url":              entry.get("link", ""),
                "title":            entry.get("title", "").strip(),
                "fetched_on":       now,
                "content":          summary.strip(),
                "platforms_mentioned": [],
            })

    print(f"→ CNBC RSS: {len(articles)} articles fetched.")
    return apply_query_filter(articles)


YAHOO_FINANCE_RSS_FEEDS = {
    "Top Stories":     "https://finance.yahoo.com/rss/topstories",
    "News Index":      "https://finance.yahoo.com/news/rssindex",
    "All Finance":     "https://finance.yahoo.com/news/rss",
    # …add more (e.g. symbol-specific via 
    #    f"http://finance.yahoo.com/rss/headline?s={symbol}"
    # ) if you need ticker-level feeds
}

def fetch_yahoo_rss():
    print("Fetching Yahoo Finance websites…")
    articles = []

    for label, url in YAHOO_FINANCE_RSS_FEEDS.items():
        feed = feedparser.parse(url)
        if getattr(feed, "bozo", False):
            print(f"  ⚠️  Failed to parse '{label}': {feed.bozo_exception}")
            continue

        for entry in feed.entries:
            # summary/description fallback
            summary = getattr(entry, "summary", "") or entry.get("description", "")
            # published date fallback
            published = getattr(entry, "published", "") or entry.get("pubDate", "")

            now = datetime.now(timezone.utc).isoformat()
            articles.append({
                "source":       f"{label} [RSS]",
                "url":          entry.get("link", ""),
                "title":        entry.get("title", "").strip(),
                "fetched_on":   now,
                "content":      summary.strip(),
                "platforms_mentioned": [],
            })

    print(f"→ Yahoo Finance: {len(articles)} articles fetched.")
    return apply_query_filter(articles)


# ========== Sifted FETCH ==========
def fetch_sifted_rss():
    print("Fetching Sifted RSS feeds…")
    feeds = {"Sifted": "https://sifted.eu/feed/"}
    articles = []

    for label, feed_url in feeds.items():
        resp = requests.get(feed_url, timeout=10, headers={"User-Agent": "MyBot/1.0"})
        feed = feedparser.parse(resp.content)

        for entry in feed.entries:
            content = getattr(entry, "summary", entry.get("description", ""))
            now = datetime.now(timezone.utc).isoformat()
            articles.append({
                "source":            f"Sifted — {label} [RSS]",
                "url":               entry.link,
                "title":             entry.title,
                "fetched_on":        now,
                "content":           content,
                "platforms_mentioned": [],
            })

    print(f"→ Sifted RSS: {len(articles)} articles fetched.")
    return apply_query_filter(articles)


# ========== SAVE ==========
# ── Compute a repo-relative data directory ──────────────────────────────────────
# In Actions, cwd() will be /github/workspace; locally it'll be wherever you launch Jupyter.
BASE_DIR = Path().cwd()
SAVE_DIR = BASE_DIR / "data"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
# ────────────────────────────────────────────────────────────────────────────────

def save_articles(articles):
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = SAVE_DIR / f"news_{today}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2)
    print(f"✅ Saved {len(articles)} articles to {filepath}")



def update_daily_file(articles):
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = SAVE_DIR / f"news_{today}.json"
    
    # Load existing articles
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = []
    
    # Merge and dedupe by URL
    combined = {art.get("url"): art for art in existing}
    for art in articles:
        combined[art.get("url")] = art
    
    merged = list(combined.values())
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    print(f"✅ Updated {len(articles)} new articles, total {len(merged)} saved to {filepath}")
# ========== RUN ==========
newsapi_articles     = fetch_newsapi()
rss_articles         = fetch_bloomberg_rss()
gnews_articles       = run_gnews_for_all_entities()
investing_articles   = fetch_investing_rss()
sec_articles         = fetch_sec_press_releases()
crunchbase_articles  = fetch_crunchbase_sections()
cnbc_articles        = fetch_cnbc_rss()
yahoo_articles       = fetch_yahoo_rss()
sifted_articles      = fetch_sifted_rss()
finanzen_articles      = fetch_finanzen_net()

gnews_keywords = []
for sub_q in GNEWS_QUERIES:
    print(f"→ GNews chunk ({len(sub_q)} chars)…")
    gnews_keywords.extend(fetch_gnews(sub_q))

all_articles = (
    rss_articles
  + newsapi_articles
  + gnews_keywords
  + gnews_articles
  + investing_articles
  + sec_articles
  + crunchbase_articles
  + cnbc_articles
  + yahoo_articles
  + sifted_articles
  + finanzen_articles
)

# Add keywords to each article
for article in all_articles:
    full_text = f"{article.get('title', '')} {article.get('content', '')}"
    article["keywords"] = extract_keywords(full_text)

# Save to daily file with keywords included
if all_articles:
    update_daily_file(all_articles)
