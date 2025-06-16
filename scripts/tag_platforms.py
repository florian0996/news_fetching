#!/usr/bin/env python3
"""
tag_platforms.py – Populate `platforms_mentioned` in every news_*.json
found inside the repo’s data/ folder.

Folder layout
.
├─ data/
│  ├─ Master_Entities_Table - Originator_Platforms_Funds_and_Competitors.csv
│  ├─ news_2025-06-15.json
│  ├─ news_2025-06-16.json
│  └─ … (your rolling 6-7 daily files)
└─ scripts/
   └─ tag_platforms.py   ← this file

Run from anywhere; paths are derived from this file’s location.
Requires: pandas ≥1.0
"""

from pathlib import Path
import json, re
import pandas as pd
import sys

# ──────────────────────────────────────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent      # “…/repo/”
DATA_DIR   = REPO_ROOT / "data"

MASTER_CSV = DATA_DIR / "Master_Entities_Table - Originator_Platforms_Funds_and_Competitors.csv"
NEWS_GLOB  = DATA_DIR.glob("news_*.json")

# ──────────────────────────────────────────────────────────────────────────────
# 1. Build alias → canonical name map
# ──────────────────────────────────────────────────────────────────────────────
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
    alias: re.compile(rf"\b{re.escape(alias)}\b", re.I)
    for alias in alias_to_name
}

# ──────────────────────────────────────────────────────────────────────────────
# 2. Tag every news_*.json file (in-place, no backups)
# ──────────────────────────────────────────────────────────────────────────────
files_processed = 0
articles_tagged = 0

for news_file in sorted(NEWS_GLOB):
    with news_file.open(encoding="utf-8") as f:
        articles = json.load(f)

    for art in articles:
        haystack = f"{art.get('title','')} {art.get('content','')}".lower()
        matches  = {alias_to_name[a] for a, rgx in alias_regex.items() if rgx.search(haystack)}
        art["platforms_mentioned"] = sorted(matches)

    with news_file.open("w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    files_processed += 1
    articles_tagged += len(articles)
    print(f"✅  {news_file.name}: {len(articles)} articles tagged")

if not files_processed:
    print("⚠️  No news_*.json files found in data/. Nothing to do.", file=sys.stderr)
else:
    print(f"\n✔️  Completed: {files_processed} file(s), {articles_tagged} articles total.")
