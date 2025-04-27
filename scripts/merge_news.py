#!/usr/bin/env python3
import json
from datetime import date
from pathlib import Path

# ── CONFIG ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path.cwd() / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TODAY = date.today().isoformat()
NEW_FILE = DATA_DIR / f"news_{TODAY}.json"
MASTER_FILE = DATA_DIR / "all_news.json"
# ────────────────────────────────────────────────────────────────────────────────

if not NEW_FILE.exists():
    raise FileNotFoundError(f"Expected today’s JSON at {NEW_FILE}")

# Load or initialize master list
if MASTER_FILE.exists():
    master = json.loads(MASTER_FILE.read_text(encoding="utf-8"))
else:
    master = []

# Load today’s batch
today_batch = json.loads(NEW_FILE.read_text(encoding="utf-8"))

# ── DEDUPE LOGIC ────────────────────────────────────────────────────────────────
# Build set of seen IDs (for dicts with "id") and raw values (for non-dicts)
seen_ids = {
    item["id"]
    for item in master
    if isinstance(item, dict) and "id" in item
}
seen_raw = {
    item
    for item in master
    if not isinstance(item, dict)
}

to_add = []
for item in today_batch:
    if isinstance(item, dict) and "id" in item:
        # Deduplicate on id
        if item["id"] not in seen_ids:
            to_add.append(item)
            seen_ids.add(item["id"])
    else:
        # Non-dict (e.g. string) dedupe on the raw value
        if item not in seen_raw:
            to_add.append(item)
            seen_raw.add(item)
# ────────────────────────────────────────────────────────────────────────────────

# Append & write back
if to_add:
    master.extend(to_add)
    MASTER_FILE.write_text(json.dumps(master, indent=2), encoding="utf-8")
    print(f"Appended {len(to_add)} new items to all_news.json")
else:
    print("No new items to append.")
