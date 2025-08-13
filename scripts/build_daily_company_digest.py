#!/usr/bin/env python3
"""
build_daily_company_digest.py
Create data/news_filtered_for_companies_of_interest.json

What this script does
- Scans quarterly aggregate files: data/news_*_Q*.json
- Derives each article’s day from its timestamp (handles ISO and RFC dates)
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

It also prints a short summary and fails loudly (non-zero exit) if no inputs or no days are found,
so CI doesn’t “succeed” with a no-op.
"""

from pathlib import Path
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime

# ───────────────────────── locate data dir robustly ─────────────────────────
HERE = Path(__file__).resolve()
CANDIDATE_DATA_DIRS = [
    HERE.parent / "data",              # repo_root/data if script in repo_root
    HERE.parent.parent / "data",       # repo_root/data if script in repo_root/scripts
    Path.cwd() / "data",               # data under current working directory (CI)
]

DATA_DIR = None
for p in CANDIDATE_DATA_DIRS:
    if p.is_dir():
        DATA_DIR = p
        break
if DATA_DIR is None:
    sys.stderr.write(
        "ERROR: Could not locate the data/ directory. Tried:\n  - "
        + "\n  - ".join(str(p) for p in CANDIDATE_DATA_DIRS)
        + "\n"
    )
    sys.exit(2)

# Output file path
OUTFILE = DATA_DIR / "news_filtered_for_companies_of_interest.json"

# Input aggregates: keep quarterly files (fetcher appends to the current quarter)
NEWS_FILES = sorted(DATA_DIR.glob("news_*_Q*.json"))

# Recognise YYYY-MM-DD inside timestamp strings
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
    Accepts '2025-04-28 16:55:44', '2025-04-28',
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
if not NEWS_FILES:
    sys.stderr.write(f"ERROR: No input aggregate files matched: {DATA_DIR}/news_*_Q*.json\n")
    sys.exit(3)

all_days: set[str] = set()
hits: dict[str, list] = defaultdict(list)  # day → list[article]
total_articles = 0

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

    total_articles += len(articles)

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
            title_val = art.get("title")
            title = title_val.strip() if isinstance(title_val, str) else ""
            hits[day].append({
                "title": title,
                "url": art.get("url"),
                "platforms_mentioned": plats
            })

if not all_days:
    sys.stderr.write(
        "ERROR: Scanned files but extracted zero days. Likely timestamp key mismatch "
        "or parsing failure. Enable debug logs or inspect a sample article.\n"
    )
    sys.exit(4)

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

# ───────────────────────── summary ───────────────────────────────────
latest_day = max(all_days) if all_days else "—"
print(
    "✅ Company digest updated\n"
    f"  data dir:      {DATA_DIR}\n"
    f"  inputs:        {len(NEWS_FILES)} file(s)\n"
    f"  articles read: {total_articles}\n"
    f"  days covered:  {len(digest)} (latest: {latest_day})\n"
    f"  output:        {OUTFILE}\n"
)
