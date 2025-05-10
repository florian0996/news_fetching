#!/usr/bin/env python3
"""
Collect today's hourly `finanzen_YYYY-MM-DD_HHMM.json` files,
deduplicate them, write a single `finanzen_YYYY-MM-DD.json`,
and delete the hourly shards.
"""
from pathlib import Path
import json, datetime as dt

def main() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    today = dt.datetime.utcnow().strftime("%Y-%m-%d")
    parts = sorted(data_dir.glob(f"finanzen_{today}_*.json"))

    if not parts:
        print("No hourly Finanzen files to combine.")
        return

    seen, combined = set(), []
    for part in parts:
        with part.open(encoding="utf-8") as f:
            for item in json.load(f):
                if item["guid"] not in seen:
                    combined.append(item)
                    seen.add(item["guid"])

    combined.sort(key=lambda x: x["published"], reverse=True)
    out = data_dir / f"finanzen_{today}.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    # remove shards
    for part in parts:
        part.unlink()

    print(f"Wrote {out.name} with {len(combined)} items")
    print(f"Deleted {len(parts)} hourly files")

if __name__ == "__main__":
    main()
