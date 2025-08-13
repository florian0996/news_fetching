#!/usr/bin/env python3
"""
build_daily_company_digest.py
Create data/news_filtered_for_companies_of_interest.json

What this script does
- Scans quarterly aggregate files: data/news_*_Q*.json
- Derives each article’s day from its timestamp (robust to ISO and RFC dates)
- Groups articles by day when platforms/companies of interest are mentioned
- Emits a day-wise digest JSON:
    {
      "YYYY-MM-DD": {
        "articles": [
          {"title": "...", "url": "...", "platforms_mentioned": ["..."]}
        ]
      },
      ...
    }
  For days without hits:
    { "YYYY-MM-DD": { "status": "no company in the news" } }
"""

from pathlib import Path
import json
import re
from collections import defaultdict
from datetime import date, datetime
from email.utils import parsedate_to_datetime

# ───────────────────────── paths ─────────────────────────
# repo root assumed as parent of the scripts/ directory
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# process the current quarter aggregates only (as produced by the fetcher)
NEWS_FILES = sorted(DATA_DIR.glob("news_*_Q*.json"))

OUTFILE = DATA_DIR / "news_filtered_for_companies_of_interest.json"

# recognise YYYY-MM-DD inside timestamp strings
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")

# Accept common timestamp keys (flat or nested)
TS_KEYS = (
    "published_at", "publishedAt", "pubDate",
    "published", "date", "published_time", "time", "created_at"
)

def get_timestamp(art: dict) -> str:
    """
    Return the timestamp string from an article dict by checking a set of
    common keys, both at the top level and under common containers.
    """
    # flat keys
    for k in TS_KEYS:
        v = art.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # common nesting
    for container in ("metadata", "source"):
        c = art.get(container)
        if isinstance(c, dict):
            for k in TS_KEYS:
                v = c.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
    return ""

def extract_day(ts: str) -> str | None:
    """
    Return YYYY-MM-DD from a timestamp string.
    Accepts variants like '2025-04-28 16:55:44', '2025-04-28',
    or RFC strings like 'Tue, 01 Jul 2025 05:43:55 GMT'.
    """
    if not ts:
        return None
    m = DATE_RX.search(ts)
    if m:
        return m.group(0)
    # try ISO 8601 (e.g. "2025-07-01T05:43:55")
    try:
        return str(datetime.fromisoformat(ts).date())
    except Exception:
        pass
    # try RFC 2822/5322 (e.g. "Tue, 01 Jul 2025 05:43:55 GMT")
    try:
        return str(parsedate_to_datetime(ts).date())
    except Exception:
        return None

# ───────────────────────── pass 1: gather dates & matches ────────────
all_days: set[str] = set()
hits: dict[str, list] = defaultdict(list)  # day → list[article]

for jf in NEWS_FILES:
    with jf.open(encoding="utf-8") as f:
        payload = json.load(f)
        if isinstance(payload, list):
            articles = payload
        elif isinstance(payload, dict):
            # prefer common container keys; fall back to empty list
            articles = payload.get("articles") or payload.get("items") or []
        else:
            articles = []

    for art in articles:
        day = extract_day(get_timestamp(art))
        if not day:
            continue
        all_days.add(day)

        # Accept alternate platform/company keys to avoid missing hits
        plats = (
            art.get("platforms_mentioned")
            or art.get("companies_mentioned")
            or art.get("companies_of_interest")
            or []
        )

        if plats:
            hits[day].append({
                "title": art.get("title", "").strip() if isinstance(art.get("title"), str) else "",
                "url": art.get("url"),
                "platforms_mentioned": plats
            })

# ───────────────────────── build digest object ───────────────────────
digest: dict[str, dict] = {}
for day in sorted(all_days):
    digest[day] = (
        {"articles": hits[day]}
        if hits.get(day)
        else {"status": "no company in the news"}
    )

# ───────────────────────── write file ────────────────────────────────
OUTFILE.parent.mkdir(parents=True, exist_ok=True)
with OUTFILE.open("w", encoding="utf-8") as f:
    json.dump(digest, f, ensure_ascii=False, indent=2)

print(
    f"✅ Digest created from {len(NEWS_FILES)} quarterly file(s) "
    f"covering {len(digest)} day(s) → {OUTFILE.relative_to(REPO_ROOT)}"
)
