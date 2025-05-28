#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import date

def main():
    # ── CONFIG ────────────────────────────────────────────────────────────────
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(exist_ok=True)
    today = date.today().isoformat()  # e.g. "2025-05-27"
    # ──────────────────────────────────────────────────────────────────────────

    # 0) grab all the hourly parts up front
    parts = sorted(data_dir.glob(f"finanzen_{today}_*.json"))
    if not parts:
        print(f"No finanzen parts found for {today} – nothing to combine.")
        return

    seen = set()
    all_items = []

    # 1) Read & dedupe
    for filepath in parts:
        try:
            batch = json.loads(filepath.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️  Failed to load {filepath.name}: {e}")
            continue

        for item in batch:
            url = item.get("url")
            if url and url not in seen:
                seen.add(url)
                all_items.append(item)

    # 2) write out the daily-aggregated file
    outfile = data_dir / f"finanzen_{today}.json"
    outfile.write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Saved {len(all_items)} unique entries to {outfile.name}")

    # 3) Delete the individual parts
    for filepath in parts:
        try:
            filepath.unlink()
            print(f"🗑️  Deleted {filepath.name}")
        except Exception as e:
            print(f"⚠️  Failed to delete {filepath.name}: {e}")

if __name__ == "__main__":
    main()
