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
import json, re, sys, unicodedata
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
daily_files     = set(DATA_DIR.glob("news_????-??-??.json"))
quarterly_files = set(DATA_DIR.glob("news_*_Q*.json"))
NEWS_FILES = sorted(
    p for p in (daily_files | quarterly_files)
    if p.name not in {"news_filtered_for_companies_of_interest.json", "all_news.json"}
)

if not NEWS_FILES:
    print("⚠️  No news files found to tag.", file=sys.stderr)
    sys.exit(0)

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
def norm_space(s: str) -> str:
    # Unicode normalize, replace NBSP, collapse spaces, strip
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\xa0", " ").replace("–", "-").replace("—", "-").replace("’", "'")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def split_aliases(val: str) -> list[str]:
    # Accept semicolon/comma/pipe/slash separated lists
    val = norm_space(val)
    if not val:
        return []
    parts = re.split(r"[;,|/]+", val)
    return [norm_space(p) for p in parts if norm_space(p)]

def nospace(s: str) -> str:
    # remove all non-alphanumerics; used for merged-name matching
    return re.sub(r"[\W_]+", "", s.lower())

# ────────────────────────────────────────────────────────────────
# 1) Build alias → canonical-name map
# ────────────────────────────────────────────────────────────────
df = pd.read_csv(MASTER_CSV)
cols = [c.lower() for c in df.columns]
if "entity_name" in cols:
    canon_col = df.columns[cols.index("entity_name")]
else:
    canon_col = next(c for c in df.columns if not c.lower().startswith("alias"))

alias_cols = [c for c in df.columns if c.lower().startswith("alias")]

alias_to_name: dict[str, str] = {}
for _, row in df.iterrows():
    canon = norm_space(row[canon_col])
    if not canon:
        continue
    candidates = [canon]
    for col in alias_cols:
        candidates.extend(split_aliases(row.get(col, "")))

    for a in candidates:
        if not a:
            continue
        a_l = a.lower()
        alias_to_name[a_l] = canon
        alias_to_name[nospace(a)] = canon  # add merged variant e.g., 'lendingclub'

# Regex for multi-word aliases; single tokens use nospace matching
wordish_regex = {
    a: re.compile(rf"\b{re.escape(a)}\b", re.I)
    for a in alias_to_name
    if (" " in a or "-" in a) and a == a.lower() and len(a) > 2
}

# ────────────────────────────────────────────────────────────────
# 2) Tag files
# ────────────────────────────────────────────────────────────────
files_processed = 0
articles_tagged = 0

def ensure_article_dict(item, file_name: str, idx: int) -> dict:
    if not isinstance(item, dict):
        raise ValueError(f"{file_name}[{idx}] expected object, got {type(item).__name__}")
    title   = norm_space(item.get("title") or item.get("headline") or "")
    content = norm_space(item.get("content") or item.get("text") or "")
    if not title and not content:
        raise ValueError(f"{file_name}[{idx}] missing both title AND content")
    if not title:
        title = (content[:120] + "…") if len(content) > 120 else content
    item["title"], item["content"] = title, content
    return item

try:
    for news_file in NEWS_FILES:
        with news_file.open(encoding="utf-8") as f:
            raw_items = json.load(f)

        articles = []
        for idx, raw in enumerate(raw_items):
            art = ensure_article_dict(raw, news_file.name, idx)
            t1 = norm_space((art["title"] + " " + art["content"]).lower())
            t2 = nospace(t1)

            matches = set()
            # 1) wordish aliases with boundaries on t1
            for a, rgx in wordish_regex.items():
                if rgx.search(t1):
                    matches.add(alias_to_name[a])

            # 2) single-token/merged aliases checked in nospace string
            for a, canon in alias_to_name.items():
                if a not in wordish_regex and a in t2:
                    matches.add(canon)

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
    print("⚠️  No news files found to tag.", file=sys.stderr)
else:
    print(f"\n✔️  Completed: {files_processed} file(s), {articles_tagged} articles total.")
