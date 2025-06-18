#!/usr/bin/env python3
"""
tag_platforms.py – Populate `platforms_mentioned` in every news_*.json
stored in the repo’s data/ folder.

Folder layout
.
├─ data/
│  ├─ Master_Entities_Table - Originator_Platforms_Funds_and_Competitors.csv
│  ├─ news_2025-06-15.json
│  ├─ news_2025-06-16.json
│  └─ … (rolling daily files)
└─ scripts/
   └─ tag_platforms.py   ← this file

Run from anywhere; paths are derived from this file’s location.
Requires: pandas ≥1.0
"""

from pathlib import Path
import json
import re
import sys
import pandas as pd

# ────────────────────────────────────────────────────────────────
# PATHS
# ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"

MASTER_CSV = DATA_DIR / "Master_Entities_Table - Originator_Platforms_Funds_and_Competitors.csv"
NEWS_GLOB  = DATA_DIR.glob("news_*.json")

# ────────────────────────────────────────────────────────────────
# 1. Build  alias → canonical-name  map
# ────────────────────────────────────────────────────────────────
df = pd.read_csv(MASTER_CSV)

canon_col  = next(c for c in df.columns if not c.lower().startswith("alias"))
alias_cols = [c for c in df.columns if c.lower().startswith("alias")]

alias_to_name = {
    str(row[col]).strip().lower(): str(row[canon_col]).strip()
    for _, row in df.iterrows()
    for col in alias_cols
    if str(row[col]).strip()
}

alias_regex = {
    alias: re.compile(rf"\b{re.escape(alias)}\b", re.I)  # whole-word, case-insensitive
    for alias in alias_to_name
}

# ────────────────────────────────────────────────────────────────
# 2. Helper – validate / normalise one raw item
# ────────────────────────────────────────────────────────────────
def ensure_article_dict(item, file_name: str, idx: int) -> dict:
    """
    Guarantee a dict with non-empty 'title' and 'content'.
    Raises ValueError if the requirement isn't met.
    """
    if isinstance(item, dict):
        title   = item.get("title")   or item.get("headline")
        content = item.get("content") or item.get("text")
        if title and content:
            item["title"], item["content"] = title, content
            return item
        raise ValueError(f"{file_name}[{idx}] missing title/content")

    # Some crawlers have produced plain strings; treat them as invalid here
    raise ValueError(f"{file_name}[{idx}] expected object, got {type(item).__name__}")

# ────────────────────────────────────────────────────────────────
# 3. Tag every news_*.json file (in-place, no backups)
# ────────────────────────────────────────────────────────────────
files_processed = 0
articles_tagged = 0

try:
    for news_file in sorted(NEWS_GLOB):
        with news_file.open(encoding="utf-8") as f:
            raw_items = json.load(f)

        articles = []
        for idx, raw in enumerate(raw_items):
            art = ensure_article_dict(raw, news_file.name, idx)   # ← strict check

            haystack = f"{art['title']} {art['content']}".lower()
            matches  = {
                alias_to_name[a]
                for a, rgx in alias_regex.items()
                if rgx.search(haystack)
            }
            art["platforms_mentioned"] = sorted(matches)
            articles.append(art)

        # overwrite file with validated & tagged content
        with news_file.open("w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        files_processed += 1
        articles_tagged += len(articles)
        print(f"✅  {news_file.name}: {len(articles)} articles tagged")

except ValueError as err:
    # Abort the run with a clear error for GitHub Actions
    sys.exit(f"✋  Data validation failed – {err}")

if not files_processed:
    print("⚠️  No news_*.json files found in data/. Nothing to do.", file=sys.stderr)
else:
    print(f"\n✔️  Completed: {files_processed} file(s), {articles_tagged} articles total.")
