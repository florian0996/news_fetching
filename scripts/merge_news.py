#!/usr/bin/env python3
import os
import json
from datetime import date

# ── CONFIG ─────────────────────────────────────────────────────────────────────
DATA_DIR = "/Users/florianterne/Documents/M.Sc DMBA/Consulting Project/exaloan_news_tracker/data"
TODAY = date.today().isoformat()   # e.g. "2025-04-23"
NEW_FILE = f"news_{TODAY}.json"
MASTER_FILE = os.path.join(DATA_DIR, "all_news.json")
# ────────────────────────────────────────────────────────────────────────────────

new_path = os.path.join(DATA_DIR, NEW_FILE)
if not os.path.exists(new_path):
    raise FileNotFoundError(f"Expected today’s JSON at {new_path}")

# Load or initialize master list
if os.path.exists(MASTER_FILE):
    with open(MASTER_FILE, "r") as f:
        master = json.load(f)
else:
    master = []

# Load today’s batch
with open(new_path, "r") as f:
    today_batch = json.load(f)

# Optional: dedupe on some unique key, e.g. 'id'
seen = {item.get("id") for item in master if "id" in item}
to_add = [item for item in today_batch if item.get("id") not in seen]

if to_add:
    master.extend(to_add)
    with open(MASTER_FILE, "w") as f:
        json.dump(master, f, indent=2)
    print(f"Appended {len(to_add)} new items to all_news.json")
else:
    print("No new items to append.")
