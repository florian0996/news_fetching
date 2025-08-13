#!/usr/bin/env python3
"""
build_daily_company_digest.py
Create data/news_filtered_for_companies_of_interest.json

Changes vs. the original version
────────────────────────────────
▸ Looks only at *quarterly* aggregate files:  news_*_Q*.json
▸ Derives each article’s day from its `published_at` timestamp instead of
  the file name.
▸ Everything else (filtering logic, output format) is unchanged.

Output example for a day with hits
{
  "2025-04-28": {
    "articles": [
      { "title": "...", "url": "...", "platforms_mentioned": ["Platform A", …] },
      …
    ]
  },
  …
}
and for a day without hits
{ "2025-04-28": { "status": "no company in the news" } }
"""

from pathlib import Path
import json
import re
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime

# ───────────────────────── paths ─────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"

# take only quarterly files, e.g.  news_2025_Q2.json
NEWS_FILES = sorted(DATA_DIR.glob("news_*_Q*.json"))

# Suggestion 1: fail early if no files are present
if not NEWS_FILES:
    raise SystemExit("No quarterly news files found (news_*_Q*.json). Aborting.")

OUTFILE = DATA_DIR / "news_filtered_for_companies_of_interest.json"

# recognise YYYY-MM-DD inside published_at
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")

# ───────────────────────── helpers ───────────────────────
def extract_day(ts: str) -> str | None:
    if not ts:
        return None
    m = DATE_RX.search(ts)              # fast path: YYYY-MM-DD substring
    if m:
        return m.group(0)
    try:                                # RFC 1123 like: "Tue, 01 Jul 2025 05:43:55 GMT"
        return parsedate_to_datetime(ts).date().isoformat()
    except Exception:
        pass
    try:                                # ISO-ish fallback
        return datetime.fromisoformat(ts).date().isoformat()
    except Exception:
        return None

# ───────────────────────── pass 1: gather dates & matches ────────────
all_days: set[str]          = set()
hits:     dict[str, list]   = defaultdict(list)   # day → list[article]

# Suggestion 2: track unparseable timestamps and fail loudly
unparsed_total = 0
unparsed_samples: list[str | None] = []

for jf in NEWS_FILES:
    with jf.open(encoding="utf-8") as f:
        articles = json.load(f)

    for art in articles:
        day = extract_day(art.get("published_at", ""))
        if not day:
            unparsed_total += 1
            if len(unparsed_samples) < 5:
                unparsed_samples.append(art.get("published_at"))
            continue

        all_days.add(day)

        plats = art.get("platforms_mentioned", [])
        if plats:                                   # keep only relevant stories
            hits[day].append({
                "title": art.get("title", "").strip(),
                "url":   art.get("url"),            # may be None / missing
                "platforms_mentioned": plats
            })

if unparsed_total:
    raise RuntimeError(
        f"{unparsed_total} articles had unparseable published_at. "
        f"Examples: {unparsed_samples}"
    )

# ───────────────────────── build digest object ───────────────────────
digest: dict[str, dict] = {}
for day in sorted(all_days):
    digest[day] = (
        {"articles": hits[day]}
        if hits.get(day)
        else {"status": "no company in the news"}
    )

# ───────────────────────── write file ────────────────────────────────
with OUTFILE.open("w", encoding="utf-8") as f:
    json.dump(digest, f, ensure_ascii=False, indent=2)

print(
    f"✅ Digest created from {len(NEWS_FILES)} quarterly file(s) "
    f"covering {len(digest)} day(s) → {OUTFILE.relative_to(REPO_ROOT)}"
)
