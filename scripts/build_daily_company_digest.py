#!/usr/bin/env python3
"""
build_daily_company_digest.py
Create data/news_filtered_for_companies_of_interest.json

For every news_*.json file (already tagged by tag_platforms.py) we emit
either
  {"status": "no company in the news"}
or
  {"articles": [ {title, url?, platforms_mentioned}, ... ]}

The top-level keys are calendar dates (YYYY-MM-DD).
"""

from pathlib import Path
import json, re
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
NEWS_GLOB = DATA_DIR.glob("news_*.json")

DIGEST = DATA_DIR / "news_filtered_for_companies_of_interest.json"

date_re = re.compile(r"(\d{4}-\d{2}-\d{2})")      # pull date from filename

daily: dict[str, list] = defaultdict(list)

for news_file in NEWS_GLOB:
    m = date_re.search(news_file.stem)
    if not m:
        continue
    day = m.group(1)

    with news_file.open(encoding="utf-8") as f:
        articles = json.load(f)

    for art in articles:
        platforms = art.get("platforms_mentioned", [])
        if platforms:                                # keep only relevant pieces
            daily[day].append({
                "title": art.get("title", "").strip(),
                "url":   art.get("url"),             # may be None / absent
                "platforms_mentioned": platforms
            })

# ------------------------------------------------------ build final object
digest: dict[str, dict] = {}
for day in sorted(daily):
    if daily[day]:
        digest[day] = {"articles": daily[day]}
    else:
        digest[day] = {"status": "no company in the news"}

with DIGEST.open("w", encoding="utf-8") as f:
    json.dump(digest, f, ensure_ascii=False, indent=2)

print(f"✅  Wrote digest for {len(digest)} day(s) → {DIGEST.relative_to(REPO_ROOT)}")
