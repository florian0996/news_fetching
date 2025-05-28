#!/usr/bin/env python3
"""
Merge today's portal JSON files (news_YYYY-MM-DD.json, finanzen_YYYY-MM-DD.json)
into all_news.json while avoiding duplicates, then snapshot per quarter.
"""

import json, re
from datetime import date, datetime
from pathlib import Path
from collections import defaultdict

# ── CONFIG ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path.cwd() / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TODAY = date.today().isoformat()           # e.g. "2025-05-09"
DAILY_PATTERNS = [
    re.compile(rf"news_{TODAY}\.json$"),
    re.compile(rf"finanzen_{TODAY}\.json$"),
]

MASTER_FILE = DATA_DIR / "all_news.json"
# ────────────────────────────────────────────────────────────────────────────────

# ---------- load existing all_news.json (or start fresh) ----------
if MASTER_FILE.exists():
    master = json.loads(MASTER_FILE.read_text(encoding="utf-8"))
else:
    master = []

# ---------- collect today's batches ----------
batches = []
for fp in DATA_DIR.iterdir():
    if any(pat.search(fp.name) for pat in DAILY_PATTERNS):
        batches.extend(json.loads(fp.read_text(encoding="utf-8")))

if not batches:
    raise FileNotFoundError("No daily batch JSON found for today.")

# ---------- dedupe based on id, guid, link, raw equality ----------
seen_ids    = {item.get("id")   for item in master if isinstance(item, dict) and "id"   in item}
seen_guids  = {item.get("guid") for item in master if isinstance(item, dict) and "guid" in item}
seen_links  = {item.get("link") for item in master if isinstance(item, dict) and "link" in item}
seen_raw    = {item             for item in master if not isinstance(item, dict)}

to_add = []
for item in batches:
    if isinstance(item, dict):
        if "id" in item and item["id"] not in seen_ids:
            to_add.append(item); seen_ids.add(item["id"])
        elif "guid" in item and item["guid"] not in seen_guids:
            to_add.append(item); seen_guids.add(item["guid"])
        elif "link" in item and item["link"] not in seen_links:
            to_add.append(item); seen_links.add(item["link"])
        elif all(k not in item for k in ("id","guid","link")):
            # dict without those keys: include it
            to_add.append(item)
    else:
        # primitive (str, int, etc.)
        if item not in seen_raw:
            to_add.append(item); seen_raw.add(item)

# ---------- write back merged master feed ----------
if to_add:
    master.extend(to_add)
    MASTER_FILE.write_text(json.dumps(master, indent=2), encoding="utf-8")
    print(f"Appended {len(to_add)} new items to all_news.json")
else:
    print("No new items to append.")

# ---------- bucket into quarterly files ----------
by_q = defaultdict(list)
for item in master:
    # ensure item has a published_at field
    dt_str = item.get("published_at")
    try:
        dt_obj = datetime.fromisoformat(dt_str)
    except Exception:
        continue
    q = (dt_obj.month - 1) // 3 + 1
    y = dt_obj.year
    by_q[(y, q)].append(item)

for (year, quarter), items in by_q.items():
    quarter_path = DATA_DIR / f"news_{year}_Q{quarter}.json"
    with open(quarter_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(items)} items to {quarter_path.name}")
