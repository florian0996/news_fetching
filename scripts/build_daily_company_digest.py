#!/usr/bin/env python3
"""
build_daily_company_digest.py
Create data/news_filtered_for_companies_of_interest.json

What this script does
- Scans quarterly aggregate files: data/news_*_Q*.json
- Robustly derives an article’s day from its timestamp:
  * Accepts ISO strings (fromisoformat)
  * Accepts RFC 2822/5322 strings ("Tue, 13 Aug 2025 05:43:55 GMT")
  * Accepts Unix epoch seconds / milliseconds (int/float)
  * Accepts YYYY/MM/DD and YYYY-MM-DD inside longer strings
  * Looks for multiple keys: published_at, publishedAt, pubDate, etc., also under 'metadata'/'source'
- Groups by day; days without hits get {"status": "no company in the news"}
- Prints a summary; can emit deeper diagnostics when RUN_DEBUG=1

Exits non-zero when:
- data/ dir cannot be found
- no input files matched
- zero days extracted from inputs
"""

from pathlib import Path
import json
import re
import sys
import os
from collections import defaultdict, Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

# ---------------- locate data dir robustly ----------------
HERE = Path(__file__).resolve()
CANDIDATE_DATA_DIRS = [
    HERE.parent / "data",
    HERE.parent.parent / "data",
    Path.cwd() / "data",
]
DATA_DIR = next((p for p in CANDIDATE_DATA_DIRS if p.is_dir()), None)
if DATA_DIR is None:
    sys.stderr.write(
        "ERROR: Could not locate the data/ directory. Tried:\n  - "
        + "\n  - ".join(str(p) for p in CANDIDATE_DATA_DIRS)
        + "\n"
    )
    sys.exit(2)

OUTFILE = DATA_DIR / "news_filtered_for_companies_of_interest.json"

# current-quarter aggregates (fetcher appends here)
NEWS_FILES = sorted(DATA_DIR.glob("news_*_Q*.json"))
if not NEWS_FILES:
    sys.stderr.write(f"ERROR: No input files matched: {DATA_DIR}/news_*_Q*.json\n")
    sys.exit(3)

# ---------------- timestamp handling ----------------
# also accept YYYY/MM/DD
DATE_RX = re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}")

TS_KEYS = (
    "published_at", "publishedAt", "pubDate",
    "published", "date", "published_time", "time", "created_at",
    "updated_at", "created", "timestamp"
)

def normalize_yyyymmdd(s: str) -> str:
    """Return YYYY-MM-DD if s contains YYYY-MM-DD or YYYY/MM/DD; else ''."""
    m = DATE_RX.search(s)
    if not m:
        return ""
    val = m.group(0)
    return val.replace("/", "-")

def epoch_to_day(val: float | int) -> str:
    """Handle seconds or milliseconds epoch."""
    try:
        x = float(val)
    except Exception:
        return ""
    # ms vs s heuristic
    if x > 10_000_000_000:  # > ~2001 in seconds → treat as ms
        x = x / 1000.0
    try:
        return str(datetime.fromtimestamp(x, tz=timezone.utc).date())
    except Exception:
        return ""

def get_timestamp_value(art: dict) -> Any:
    """Return the raw timestamp value if present (may be str/int/float)."""
    # flat keys
    for k in TS_KEYS:
        if k in art:
            v = art.get(k)
            if v is not None and (isinstance(v, (str, int, float))):
                return v
    # common nesting
    for container in ("metadata", "source", "sys", "attributes"):
        c = art.get(container)
        if isinstance(c, dict):
            for k in TS_KEYS:
                if k in c:
                    v = c.get(k)
                    if v is not None and (isinstance(v, (str, int, float))):
                        return v
    return None

def extract_day(ts_val: Any) -> str:
    """
    Return YYYY-MM-DD from a timestamp value that might be:
    - ISO string
    - RFC 2822 string
    - str containing YYYY-MM-DD or YYYY/MM/DD
    - Unix epoch seconds/milliseconds (int/float)
    """
    if ts_val is None:
        return ""

    # numbers: epoch seconds/milliseconds
    if isinstance(ts_val, (int, float)):
        d = epoch_to_day(ts_val)
        if d:
            return d
        return ""

    # strings
    if isinstance(ts_val, str):
        s = ts_val.strip()
        if not s:
            return ""

        # fast path: YYYY[-/]MM[-/]DD inside
        norm = normalize_yyyymmdd(s)
        if norm:
            return norm

        # ISO 8601
        try:
            return str(datetime.fromisoformat(s).date())
        except Exception:
            pass

        # RFC 2822/5322
        try:
            return str(parsedate_to_datetime(s).date())
        except Exception:
            return ""

    return ""

# ---------------- scan & collect ----------------
all_days: set[str] = set()
hits: dict[str, list] = defaultdict(list)
total_articles = 0
scanned_files = []
ts_kind_counter = Counter()
no_ts_samples: list[dict] = []
no_day_samples: list[dict] = []

def sample(obj: dict) -> dict:
    """Small, safe sample of an article for diagnostics."""
    keys = ("title", "url", "published_at", "publishedAt", "pubDate", "date", "time", "timestamp")
    out = {k: obj.get(k) for k in keys if k in obj}
    # nested hints
    for container in ("metadata", "source"):
        if isinstance(obj.get(container), dict):
            c = obj[container]
            for k in ("published_at", "publishedAt", "pubDate", "date", "time", "timestamp"):
                if k in c:
                    out[f"{container}.{k}"] = c.get(k)
    return out

for jf in NEWS_FILES:
    scanned_files.append(jf.name)
    with jf.open(encoding="utf-8") as f:
        payload = json.load(f)
        if isinstance(payload, list):
            articles = payload
        elif isinstance(payload, dict):
            articles = payload.get("articles") or payload.get("items") or []
        else:
            articles = []

    total_articles += len(articles)

    for art in articles:
        raw_ts = get_timestamp_value(art)
        if raw_ts is None:
            if len(no_ts_samples) < 5:
                no_ts_samples.append(sample(art))
            ts_kind_counter["missing"] += 1
            continue

        if isinstance(raw_ts, (int, float)):
            ts_kind_counter["epoch"] += 1
        elif isinstance(raw_ts, str):
            ts_kind_counter["string"] += 1
        else:
            ts_kind_counter["other"] += 1

        day = extract_day(raw_ts)
        if not day:
            if len(no_day_samples) < 5:
                no_day_samples.append(sample(art))
            ts_kind_counter["unparsed"] += 1
            continue

        all_days.add(day)

        plats = (
            art.get("platforms_mentioned")
            or art.get("companies_mentioned")
            or art.get("companies_of_interest")
            or []
        )
        if plats:
            title_val = art.get("title")
            title = title_val.strip() if isinstance(title_val, str) else ""
            hits[day].append({
                "title": title,
                "url": art.get("url"),
                "platforms_mentioned": plats
            })

if not all_days:
    # print diagnostics to help fix the upstream mapping
    sys.stderr.write(
        "ERROR: Scanned inputs but extracted zero days. "
        "Likely timestamp key/format mismatch.\n"
        f"Files scanned: {', '.join(scanned_files) or '—'}\n"
        f"Articles total: {total_articles}\n"
        f"TS kinds: {dict(ts_kind_counter)}\n"
    )
    if no_ts_samples:
        sys.stderr.write(f"\nSamples without any timestamp key ({len(no_ts_samples)}):\n")
        sys.stderr.write(json.dumps(no_ts_samples, ensure_ascii=False, indent=2) + "\n")
    if no_day_samples:
        sys.stderr.write(f"\nSamples with timestamp but unparsable ({len(no_day_samples)}):\n")
        sys.stderr.write(json.dumps(no_day_samples, ensure_ascii=False, indent=2) + "\n")
    sys.exit(4)

# ---------------- build digest ----------------
digest: dict[str, dict] = {}
for day in sorted(all_days):
    digest[day] = {"articles": hits[day]} if hits.get(day) else {"status": "no company in the news"}

# ---------------- write output ----------------
OUTFILE.parent.mkdir(parents=True, exist_ok=True)
with OUTFILE.open("w", encoding="utf-8") as f:
    json.dump(digest, f, ensure_ascii=False, indent=2)

# ---------------- summary ----------------
latest_day = max(all_days)
summary = (
    "✅ Company digest updated\n"
    f"  data dir:      {DATA_DIR}\n"
    f"  inputs:        {len(NEWS_FILES)} file(s) → {', '.join(scanned_files)}\n"
    f"  articles read: {total_articles}\n"
    f"  ts kinds:      {dict(ts_kind_counter)}\n"
    f"  days covered:  {len(digest)} (latest: {latest_day})\n"
    f"  hits (days):   {sum(1 for d in hits if hits[d])}\n"
    f"  output:        {OUTFILE}\n"
)
print(summary)

# Optional verbose debug if RUN_DEBUG=1
if os.environ.get("RUN_DEBUG") == "1":
    print("\nDEBUG: First 5 days with hits:\n" +
          json.dumps({d: hits[d][:2] for d in list(sorted(hits))[:5]}, ensure_ascii=False, indent=2))
