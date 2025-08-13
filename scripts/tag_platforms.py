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
    # remove all non-alphanumerics; used only for multi-word merged-name matching
    return re.sub(r"[\W_]+", "", s.lower())

# Ambiguous single-word aliases that need stricter checks
# - TitleCase match required (case-sensitive)
# - Plus one of the context terms must appear nearby in text
AMBIGUOUS_SINGLE = {
    "steward": ["health", "healthcare", "health care", "hospital"],
    "goldfinch": ["capital", "finance", "protocol", "network", "crypto", "web3"],
    "conda": ["crowdinvest", "crowd", "platform", "austria", "funding"],
}
# Aliases that are too generic to match reliably; drop them entirely
DROP_ALIASES = {"lend"}  # avoid thousands of generic hits

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

# Collect (alias, canon) with normalization and filtering
pairs: list[tuple[str, str]] = []
for _, row in df.iterrows():
    canon = norm_space(row.get(canon_col, ""))
    if not canon:
        continue
    # include the canonical name itself as an alias
    candidates = [canon]
    for col in alias_cols:
        candidates.extend(split_aliases(row.get(col, "")))
    for a in candidates:
        a_norm = norm_space(a)
        if not a_norm:
            continue
        a_low = a_norm.lower()
        if a_low in DROP_ALIASES:
            continue
        pairs.append((a_norm, canon))

# Partition aliases by single-word vs multi-word
single_aliases: dict[str, str] = {}  # lower(alias) -> canon
multi_aliases: dict[str, str]  = {}  # lower(alias) -> canon
for a, canon in pairs:
    if " " in a or "-" in a:
        multi_aliases[a.lower()] = canon
    else:
        single_aliases[a.lower()] = canon

# Compile regex for multi-word aliases (word-boundary, case-insensitive)
multi_regex = {
    a: re.compile(rf"\b{re.escape(a)}\b", re.I)
    for a in multi_aliases
}

# For single words, compile a case-insensitive boundary regex
single_regex_ci = {
    a: re.compile(rf"(?<![A-Za-z0-9]){re.escape(a)}(?![A-Za-z0-9])", re.I)
    for a in single_aliases
}
# And a case-sensitive TitleCase boundary regex for ambiguous ones
single_regex_title = {
    a: re.compile(rf"(?<![A-Za-z0-9]){re.escape(a.capitalize())}(?![A-Za-z0-9])")
    for a in AMBIGUOUS_SINGLE
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

            raw_text = norm_space(f"{art['title']} {art['content']}")
            t_ci     = raw_text.lower()
            t_ns     = nospace(raw_text)  # only for multi-word merged alias check

            matches = set()

            # 1) Multi-word aliases:
            #    - boundary match (ci)
            #    - merged variant (no spaces/hyphens) present in nospace text
            for a, canon in multi_aliases.items():
                if multi_regex[a].search(t_ci):
                    matches.add(canon)
                    continue
                merged = nospace(a)
                if merged and merged in t_ns:
                    matches.add(canon)

            # 2) Single-word aliases:
            #    - NEVER use 'nospace' containment (avoids 'lend' in 'blend', 'conda' in 'anacondas')
            #    - default: boundary, case-insensitive
            #    - ambiguous ones: require TitleCase boundary AND at least one context term nearby
            for a, canon in single_aliases.items():
                if a in AMBIGUOUS_SINGLE:
                    # Case-sensitive TitleCase boundary
                    if not single_regex_title[a].search(raw_text):
                        continue
                    # Context guard
                    if not any(ctx in t_ci for ctx in AMBIGUOUS_SINGLE[a]):
                        continue
                    matches.add(canon)
                else:
                    if single_regex_ci[a].search(t_ci):
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
