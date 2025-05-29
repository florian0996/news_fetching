#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import date

def main():
    # ── CONFIG ────────────────────────────────────────────────────────────────
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(exist_ok=True)
    today = date.today().isoformat()  # e.g. "2025-05-29"
    # ──────────────────────────────────────────────────────────────────────────

    # 0) grab all the hourly parts up front
    parts = sorted(data_dir.glob(f"finanzen_{today}_*.json"))
    if not parts:
        print(f"No finanzen parts found for {today} – nothing to combine.")
        return

    all_items = []
    seen_ids = set()

    # 1) read each hourly file and collect unique entries
    for filepath in parts:
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"⚠️  Skipping {filepath.name} – invalid JSON: {e}")
            continue

        for item in data:
            item_id = item.get("id")
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                all_items.append(item)

    # 2) write out the daily aggregate
    outfile = data_dir / f"finanzen_{today}.json"
    outfile.write_text(
        json.dumps(all_items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"✅ Saved {len(all_items)} unique entries to {outfile.name}")

    # 3) Delete the individual hourly parts now that they've been combined
    for filepath in parts:
        try:
            filepath.unlink()
            print(f"🗑️  Deleted {filepath.name}")
        except Exception as e:
            print(f"⚠️  Failed to delete {filepath.name}: {e}")

if __name__ == "__main__":
    main()
