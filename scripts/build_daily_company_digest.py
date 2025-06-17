#!/usr/bin/env python3
"""
build_daily_company_digest.py
Create data/news_filtered_for_companies_of_interest.json

For each day represented by at least one news_*.json file we output either

  {
    "status": "no company in the news"
  }

or

  {
    "articles": [
       { "title": "...", "url": "...", "platforms_mentioned": [...] },
       …
    ]
  }
"""

from pathlib import Path
import json, re
from collections import defaultdict

# ───────────────────────── paths ─────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
NEWS_GLOB = DATA_DIR.glob("news_*.json")

OUTFILE   = DATA_DIR / "news_filtered_for_companies_of_interest.json"

date_rx   = re.compile(r"\d{4}-\d{2}-\d{2}")      # YYYY-MM-DD

# ───────────────────────── pass 1: gather dates & matches ────────────────────
all_days: set[str]          = set()
hits:     dict[str, list]   = defaultdict(list)   # day → list[article]

for jf in NEWS_GLOB:
    # Extract the date from filename.
    m = date_rx.search(jf.stem)
    if not m:
        continue
    day = m.group(0)
    all_days.add(day)

    with jf.open(encoding="utf-8") as f:
        articles = json.load(f)

    for art in articles:
        plats = art.get("platforms_mentioned", [])
        if plats:                                   # keep only relevant stories
            hits[day].append({
                "title": art.get("title", "").strip(),
                "url":   art.get("url"),             # may be None / missing
                "platforms_mentioned": plats
            })

# ───────────────────────── build digest object ───────────────────────────────
digest: dict[str, dict] = {}
for day in sorted(all_days):
    if hits.get(day):
        digest[day] = {"articles": hits[day]}
    else:
        digest[day] = {"status": "no company in the news"}

# ───────────────────────── write file ────────────────────────────────────────
with OUTFILE.open("w", encoding="utf-8") as f:
    json.dump(digest, f, ensure_ascii=False, indent=2)

print(f"✅ Digest created with {len(digest)} day(s) → {OUTFILE.relative_to(REPO_ROOT)}")
