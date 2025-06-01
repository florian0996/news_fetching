@@ -0,0 +1,547 @@
#!/usr/bin/env python
# coding: utf-8

# In[2]:


pip install beautifulsoup4 lxml


# In[3]:


pip install yake


# In[4]:


import os
import json
import requests
import feedparser
from datetime import datetime
from pathlib import Path


# In[5]:


import yake
kw_extractor = yake.KeywordExtractor(lan="en", n=1, top=10)

def extract_keywords(text):
    if not text:
        return []
    keywords = kw_extractor.extract_keywords(text)
    return [kw for kw, score in keywords]


# In[1]:


def matches_query(text, query):
    query_terms = [term.strip().lower() for term in query.split("OR")]
    text_lower = text.lower()
    return any(term in text_lower for term in query_terms)


# In[83]:


# ========== CONFIG ==========
NEWSAPI_KEY = "186dd4ccd2234f6a89f850bf16effb06"

QUERY = (
    "credit OR loan OR Exaloan OR lending OR fintech startup OR digital lending OR credit platform OR loan service"
    "OR peer-to-peer lending OR online loan platform OR investment platform"
    "OR digital wealth management OR fractional investing OR seed funding OR fintech VC OR risk assessment"
)

QUERY_short = (
    "credit OR loan OR Exaloan OR lending"
)

LANGUAGE = "en"
PAGE_SIZE = 100

# Switch to enable/disable article filtering
ENABLE_FILTERING = False  # Set to False to bypass QUERY-based filtering

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


# In[7]:


RSS_FEEDS = {
    "Markets":   "https://feeds.bloomberg.com/markets/news.rss",
    "Politics":  "https://feeds.bloomberg.com/politics/news.rss",
    "Business":  "https://feeds.bloomberg.com/business/news.rss",
    "Technology":"https://feeds.bloomberg.com/technology/news.rss",
    "Economics": "https://feeds.bloomberg.com/economics/news.rss",
    "Industries":"https://feeds.bloomberg.com/industries/news.rss"
}


# In[8]:


# ========== BLOOMBERG RSS FETCH ==========
def fetch_bloomberg_rss():
    print("Fetching Bloomberg RSS feeds...")
    all_articles = []
    for name, feed_url in RSS_FEEDS.items():
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            content = getattr(entry, 'summary', entry.get('description', ''))
            all_articles.append({
                "source":         f"Bloomberg – {name} [RSS]",
                "url":            entry.link,
                "title":          entry.title,
                "published_at":   entry.published if "published" in entry else "",
                "content":        content,
                "platforms_mentioned": [],
            })
    print(f"→ Bloomberg RSS: {len(all_articles)} articles fetched.")

    # ——— apply QUERY-based filtering if ENABLE_FILTERING is True ———
    return apply_query_filter(all_articles)


# In[9]:


# ========== NEWSAPI FETCH ==========
def fetch_newsapi():
    print("Fetching from NewsAPI...")
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
            "published_at":      a["publishedAt"],
            "content":           a.get("content") or a.get("description", ""),
            "platforms_mentioned": [],
        }
        for a in raw
    ]

    # apply QUERY-based filtering if ENABLE_FILTERING is True
    return apply_query_filter(all_articles)


# In[10]:


# ========== SEC FETCH ==========
def fetch_sec_press_releases():
    RSS_URL = "https://www.sec.gov/news/pressreleases.rss"
    feed = feedparser.parse(RSS_URL)

    entries = []
    for e in feed.entries:
        entries.append({
            "source":            "SEC Press Releases [RSS]",
            "url":               e.link,
            "title":             e.title,
            "published_at":      getattr(e, "published", ""),
            "content":           e.get("summary", ""),
            "platforms_mentioned": [],
        })

    print(f"→ SEC Press Releases: {len(entries)} fetched.")
    # apply QUERY-based filtering if ENABLE_FILTERING is True
    return apply_query_filter(entries)


# In[50]:


# ========== GNEWS FETCH ==========
def fetch_gnews_financial_times():
    # show the actual short query you’re using
    print(f"Fetching from GNews (query: '{QUERY_short}')…")
    
    api_key = "c4f8fe7bbdaea71cd2ec22279906c40f"
    url     = "https://gnews.io/api/v4/search"
    params  = {
        "q":       QUERY_short,
        "in":      "title,description",
        "lang":    LANGUAGE,
        "country": "us",
        "max":     PAGE_SIZE,
        "token":   api_key,
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"GNews error: {response.status_code} – {response.text}")
        return []

    raw = response.json().get("articles", [])
    print(f"→ GNews: {len(raw)} articles fetched'.")

    all_articles = []
    for a in raw:
        source_name = a.get("source", {}).get("name", "N/A")
        all_articles.append({
            "source":            f"{source_name} [GNews]",
            "url":               a.get("url", ""),
            "title":             a.get("title", ""),
            "published_at":      a.get("publishedAt", ""),
            "content":           a.get("description", ""),
            "platforms_mentioned": [],
        })

    return apply_query_filter(all_articles)


# In[12]:


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
            articles.append({
                "source":             label,
                "url":                entry.link,
                "title":              entry.title,
                "published_at":       entry.published if "published" in entry else "",
                "content":            entry.get("summary", ""),
                "platforms_mentioned": [],
            })

    print(f"→ Investing.com RSS: {len(articles)} articles fetched.")

    # apply QUERY-based filtering if ENABLE_FILTERING is True
    return apply_query_filter(articles)


# In[13]:


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

            articles.append({
                "source":    sec["label"],
                "url":       url,
                "title":     title,
                "published_at": published_iso,
                "content":     content_snip,
                "platforms_mentioned": [],
            })

    print(f"→ Crunchbase News (all sections): {len(articles)} fetched.")
    # apply QUERY-based filtering if ENABLE_FILTERING is True
    return apply_query_filter(articles)


# In[71]:


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

            articles.append({
                "source":       f"{label} [RSS]",
                "url":          entry.get("link", ""),
                "title":        entry.get("title", "").strip(),
                "published_at": published,
                "content":      summary.strip(),
                "platforms_mentioned": [],
            })

    print(f"→ CNBC RSS: {len(articles)} articles fetched.")
    return apply_query_filter(articles)


# In[73]:


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

            articles.append({
                "source":       f"{label} [RSS]",
                "url":          entry.get("link", ""),
                "title":        entry.get("title", "").strip(),
                "published_at": published,
                "content":      summary.strip(),
                "platforms_mentioned": [],
            })

    print(f"→ Yahoo Finance: {len(articles)} articles fetched.")
    return apply_query_filter(articles)


# In[75]:


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
            articles.append({
                "source":            f"Sifted — {label} [RSS]",
                "url":               entry.link,
                "title":             entry.title,
                "published_at":      entry.get("published", ""),
                "content":           content,
                "platforms_mentioned": [],
            })

    print(f"→ Sifted RSS: {len(articles)} articles fetched.")
    return apply_query_filter(articles)


# In[77]:


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


# In[79]:


# ========== RUN ==========
newsapi_articles     = fetch_newsapi()
rss_articles         = fetch_bloomberg_rss()
gnews_articles       = fetch_gnews_financial_times()
investing_articles   = fetch_investing_rss()
sec_articles         = fetch_sec_press_releases()
crunchbase_articles  = fetch_crunchbase_sections()
cnbc_articles        = fetch_cnbc_rss()
yahoo_articles       = fetch_yahoo_rss()
sifted_articles      = fetch_sifted_rss()

all_articles = (
    rss_articles
  + newsapi_articles
  + gnews_articles
  + investing_articles
  + sec_articles
  + crunchbase_articles
  + cnbc_articles
  + yahoo_articles
  + sifted_articles
)

# Add keywords to each article
for article in all_articles:
    full_text = f"{article.get('title', '')} {article.get('content', '')}"
    article["keywords"] = extract_keywords(full_text)

# Save to daily file with keywords included
if all_articles:
    save_articles(all_articles)


# In[ ]:



