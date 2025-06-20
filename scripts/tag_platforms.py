#!/usr/bin/env python3
"""
tag_platforms.py – Populate `platforms_mentioned` in every raw news_*.json
stored in data/, ignoring the summary file
news_filtered_for_companies_of_interest.json.

Folder layout
.
├─ data/
│  ├─ Master_Entities_Table - Originator_Platforms_Funds_and_Competitors.csv
│  ├─ news_2025-06-15.json
│  ├─ news_2025-06-16.json
│  ├─ news_filtered_for_companies_of_interest.json  ← skipped
│  └─ …
└─ scripts/
   └─ tag_platforms.py
"""

from pathlib import Path
import json, re, sys
import pandas as pd

# ────────────────────────────────────────────────────────────────
# PATHS
# ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"

MASTER_CSV = DATA_DIR / "Master_Entities_Table - Originator_Platforms_Funds_and_Competitors.csv"

# collect only genuine daily news files
NEWS_GLOB = [
    p for p in DATA_DIR.glob("news_*.json")
    if "filtered_for_companies_of_interest" not in p.name        # ▼ skip digest
]

# ────────────────────────────────────────────────────────────────
# 1. Build alias → canonical-name map
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
    a: re.compile(rf"\b{re.escape(a)}\b", re.I)      # whole-word, case-insensitive
    for a in alias_to_name
}

# ────────────────────────────────────────────────────────────────
# 2. Helper – validate / normalise one raw item
# ────────────────────────────────────────────────────────────────
def ensure_article_dict(item, file_name: str, idx: int) -> dict:
    """Return a dict with at least one non-empty field (title or content)."""
    if not isinstance(item, dict):
        raise ValueError(f"{file_name}[{idx}] expected object, got {type(item).__name__}")

    title   = (item.get("title")   or item.get("headline") or "").strip()
    content = (item.get("content") or item.get("text")     or "").strip()

    if not title and not content:
        raise ValueError(f"{file_name}[{idx}] missing both title AND content")

    if not title:
        title = (content[:120] + "…") if len(content) > 120 else content
    if not content:
        content = ""

    item["title"], item["content"] = title, content
    return item

# ────────────────────────────────────────────────────────────────
# 3. Tag every raw news file
# ────────────────────────────────────────────────────────────────
files_processed = 0
articles_tagged = 0

try:
    for news_file in sorted(NEWS_GLOB):
        with news_file.open(encoding="utf-8") as f:
            raw_items = json.load(f)

        articles = []
        for idx, raw in enumerate(raw_items):
            art = ensure_article_dict(raw, news_file.name, idx)

            haystack = f"{art['title']} {art['content']}".lower()
            matches  = {
                alias_to_name[a]
                for a, rgx in alias_regex.items()
                if rgx.search(haystack)
            }
            art["platforms_mentioned"] = sorted(matches)
            articles.append(art)

        with news_file.open("w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        files_processed += 1
        articles_tagged += len(articles)
        print(f"✅  {news_file.name}: {len(articles)} articles tagged")

except ValueError as err:
    sys.exit(f"✋  Data validation failed – {err}")

if not files_processed:
    print("⚠️  No raw news_*.json files found in data/.", file=sys.stderr)
else:
    print(f"\n✔️  Completed: {files_processed} file(s), {articles_tagged} articles total.")
