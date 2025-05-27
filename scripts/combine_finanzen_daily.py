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

    seen = set()
    all_items = []

    # load only the timestamped feeds for today
    for filepath in sorted(data_dir.glob(f"finanzen_{today}_*.json")):
        with open(filepath, encoding="utf-8") as f:
            try:
                batch = json.load(f)
            except Exception as e:
                print(f"⚠️  Failed to load {filepath.name}: {e}")
                continue

        for item in batch:
            url = item.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            all_items.append(item)

    if not all_items:
        print(f"No finanzen files found for {today} – nothing to combine.")
        return

    # write out the daily-aggregated file
    outfile = data_dir / f"finanzen_{today}.json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(all_items)} unique entries to {outfile.name}")

if __name__ == "__main__":
    main()
