#!/usr/bin/env python3
"""
build_daily_company_digest.py – Create data/company_digest.json

 Assumes tag_platforms.py has already populated `platforms_mentioned`
 in every news_*.json file.

Output structure
================
{
  "2025-06-15": {
    "status": "no company in the news"
  },
  "2025-06-16": {
    "articles": [
      {
        "title": "Funding round for X-Platform …",
        "url":   "https://example.com/article123",   # optional if present
        "platforms_mentioned": ["X-Platform"]
      },
      …
    ]
  },
  …
}
"""

from pathlib import Path
import json
import re
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
NEWS_GLOB = DATA_DIR.glob("news_*.json")
DIGEST    = DATA_DIR / "company_digest.json"

date_re = re.compile(r"(\d{4}-\d{2}-\d{2})")          # extract YYYY-MM-DD

daily = defaultdict(list)     # date → [article dicts]

for news_file in NEWS_GLOB:
    # infer date from filename, e.g. news_2025-06-16.json  →  2025-06-16
    m = date_re.search(news_file.stem)
    if not m:
        continue
    day = m.group(1)

    with news_file.open(encoding="utf-8") as f:
        articles = json.load(f)

    for art in articles:
        platforms = art.get("platforms_mentioned", [])
        if platforms:                        # keep only interesting articles
            daily[day].append({
                "title": art.get("title", "").strip(),
                "url":   art.get("url"),     # may be None / absent
                "platforms_mentioned": platforms
            })

# build the digest object
digest = {}
for day in sorted(daily):
    if not daily[day]:
        digest[day] = {"status": "no company in the news"}
    else:
        digest[day] = {"articles": daily[day]}

# write
with DIGEST.open("w", encoding="utf-8") as f:
    json.dump(digest, f, ensure_ascii=False, indent=2)

print(f"✅  Wrote digest for {len(digest)} day(s) → {DIGEST}")
