#!/usr/bin/env python3
"""
build_daily_company_digest.py
Create data/news_filtered_for_companies_of_interest.json

Scans quarterly aggregates: data/news_*_Q*.json
Parses day from timestamps (ISO or RFC) and groups articles by day when
platform/company tags are present. Emits a day-wise digest where days with
no hits get: {"status": "no company in the news"}.

The script prints a scan summary and exits non-zero if:
- data/ cannot be found
- no input files matched
- timestamps yielded zero days
This makes CI fail loudly instead of silently producing no changes.
"""

from pathlib import Path
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime

# ---------- locate data dir robustly ----------
HERE = Path(__file__).resolve()
CANDIDATE_DATA_DIRS = [
    HERE.parent / "data",            # repo_root/data if script sits in repo_root
    HERE.parent.parent / "data",     # repo_root/data if script sits in repo_root/scripts
    Path.cwd() / "data",             # CI: run from repo root
]
DATA_DIR = next((p for p in CANDIDATE_DATA_DIRS if p.is_dir()), None)
if DATA_DIR is None:
    sys.stderr.write(
        "ERROR: Could not locate the data/ directory. Tried:\n  - "
        + "\n  - ".join(str(p) for p in CANDIDATE_DATA_DIRS)
        + "\n"
    )
    sys.exit(2)

OUTFILE = DATA_DIR / "news_filtered_for_companies_of_interest.json"

# Current-quarter aggregates (fetcher keeps appending here)
NEWS_FILES = sorted(DATA_DIR.glob("news_*_Q*.json"))
if not NEWS_FILES:
    sys.stderr.write(f"ERROR: No input files matched: {DATA_DIR}/news_*_Q*.json\n")
    sys.exit(3)

# ---------- timestamp handling ----------
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")
TS_KEYS = (
    "published_at", "publishedAt", "pubDate",
    "published", "date", "published_time", "time", "created_at"
)

def get_timestamp(art: dict) -> str:
    # flat keys
    for k in TS_KEYS:
        v = art.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # common nesting (defensive)
    for container in ("metadata", "source"):
        c = art.get(container)
        if isinstance(c, dict):
            for k in TS_KEYS:
                v = c.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
    return ""

def extract_day(ts: str) -> str | None:
    if not ts:
        return None
    m = DATE_RX.search(ts)
    if m:
        return m.group(0)
    # ISO 8601
    try:
        return str(datetime.fromisoformat(ts).date())
    except Exception:
        pass
    # RFC 2822/5322 (e.g., "Tue, 01 Jul 2025 05:43:55 GMT")
    try:
        return str(parsedate_to_datetime(ts).date())
    except Exception:
        return None

# ---------- pass 1: scan & collect ----------
all_days: set[str] = set()
hits: dict[str, list] = defaultdict(list)
total_articles = 0
scanned_files = []

for jf in NEWS_FILES:
    scanned_files.append(jf.name)
    with jf.open(encoding="utf-8") as f:
        payload = json.load(f)
        if isinstance(payload, list):
            articles = payload
        elif isinstance(payload, dict):
            articles = payload.get("articles") or payload.get("items") or []
        else:
            articles = []

    total_articles += len(articles)

    for art in articles:
        day = extract_day(get_timestamp(art))
        if not day:
            continue
        all_days.add(day)

        # accept several keys for the tagger output
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
        "ERROR: Scanned inputs but extracted zero days. Likely timestamp key or format mismatch.\n"
        f"Files scanned: {', '.join(scanned_files) or '—'}\n"
    )
    sys.exit(4)

# ---------- build digest ----------
digest: dict[str, dict] = {}
for day in sorted(all_days):
    digest[day] = {"articles": hits[day]} if hits.get(day) else {"status": "no company in the news"}

# ---------- write output ----------
OUTFILE.parent.mkdir(parents=True, exist_ok=True)
with OUTFILE.open("w", encoding="utf-8") as f:
    json.dump(digest, f, ensure_ascii=False, indent=2)

# ---------- summary ----------
latest_day = max(all_days)
print(
    "✅ Company digest updated\n"
    f"  data dir:      {DATA_DIR}\n"
    f"  inputs:        {len(NEWS_FILES)} file(s) → {', '.join(scanned_files)}\n"
    f"  articles read: {total_articles}\n"
    f"  days covered:  {len(digest)} (latest: {latest_day})\n"
    f"  hits (days):   {sum(1 for d in hits if hits[d])}\n"
    f"  output:        {OUTFILE}\n"
)
