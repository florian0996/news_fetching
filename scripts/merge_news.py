#!/usr/bin/env python3
import json
from datetime import date
from pathlib import Path

# ── CONFIG ─────────────────────────────────────────────────────────────────────
# Compute a repo-relative data directory
# In Actions, cwd() == /github/workspace; locally it'll be wherever you run this
DATA_DIR = Path.cwd() / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Filenames
TODAY = date.today().isoformat()   # e.g. "2025-04-23"
NEW_FILE = f"news_{TODAY}.json"
MASTER_FILE = DATA_DIR / "all_news.json"
# ────────────────────────────────────────────────────────────────────────────────

new_path = DATA_DIR / NEW_FILE
if not new_path.exists():
    raise FileNotFoundError(f"Expected today’s JSON at {new_path}")

# Load or initialize master list
if MASTER_FILE.exists():
    master = json.loads(MASTER_FILE.read_text(encoding="utf-8"))
else:
    master = []

# Load today’s batch
today_batch = json.loads(new_path.read_text(encoding="utf-8"))

# Optional: dedupe on some unique key, e.g. 'id'
seen_ids = {item.get("id") for item in master if "id" in item}
to_add = [item for item in today_batch if item.get("id") not in seen_ids]

if to_add:
    master.extend(to_add)
    MASTER_FILE.write_text(json.dumps(master, indent=2), encoding="utf-8")
    print(f"Appended {len(to_add)} new items to all_news.json")
else:
    print("No new items to append.")
