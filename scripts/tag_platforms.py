#!/usr/bin/env python3
"""
tag_platforms.py – Populate `platforms_mentioned` across *daily* and *quarterly* news JSONs.

Targets:
  data/news_YYYY-MM-DD.json      (daily)
  data/news_YYYY_QN.json         (quarterly)

Skips:
  data/news_filtered_for_companies_of_interest.json
  data/all_news.json
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

# ────────────────────────────────────────────────────────────────
# FILE SELECTION (daily + quarterly, skip digest/all_news)
# ────────────────────────────────────────────────────────────────
daily_files      = set(DATA_DIR.glob("news_????-??-??.json"))
quarterly_files  = set(DATA_DIR.glob("news_*_Q*.json"))
NEWS_FILES = sorted(
    p for p in (daily_files | quarterly_files)
    if p.name not in {"news_filtered_for_companies_of_interest.json", "all_news.json"}
)

if not NEWS_FILES:
    print("⚠️  No news files found to tag.", file=sys.stderr)
    sys.exit(0)

# ────────────────────────────────────────────────────────────────
# 1) Build alias → canonical-name map
# ────────────────────────────────────────────────────────────────
df = pd.read_csv(MASTER_CSV)

canon_col  = next(c for c in df.columns if not c.lower().startswith("alias"))
alias_cols = [c for c in df.columns if c.lower().startswith("alias")]

alias_to_name = {}
for _, row in df.iterrows():
    canon = str(row[canon_col]).strip()
    for col in alias_cols:
        alias_val = str(row[col]).strip()
        if alias_val and alias_val.lower() != "nan":
            alias_to_name[alias_val.lower()] = canon

alias_regex = {
    a: re.compile(rf"\b{re.escape(a)}\b", re.I)   # whole-word, case-insensitive
    for a in alias_to_name
}

# ────────────────────────────────────────────────────────────────
# 2) Helper – normalise one item
# ────────────────────────────────────────────────────────────────
def ensure_article_dict(item, file_name: str, idx: int) -> dict:
    """Ensure dict and guarantee title/content presence."""
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
# 3) Tag files
# ────────────────────────────────────────────────────────────────
files_processed = 0
articles_tagged = 0

try:
    for news_file in NEWS_FILES:
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

print(f"\n✔️  Completed: {files_processed} file(s), {articles_tagged} articles total.")
