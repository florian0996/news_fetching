#!/usr/bin/env python3
"""Combine yesterday's hourly Finanzen.net RSS snapshots into a single daily file.

The old version expected every news item to carry an ``id`` field, but
``fetch_finanzen_net_json.py`` only stores ``url`` and ``title``. This rewrite
falls back to those fields to de‑duplicate items, so the daily file is no
longer empty.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable


def unique_key(item: dict[str, Any]) -> str | None:
    """Return a stable key to identify one news item.

    Priority order:
    1. ``id``  – if the upstream collector starts adding IDs later on.
    2. ``url`` – stable across multiple hourly snapshots.
    3. ``title`` – best‑effort fallback (rarely duplicates exactly).
    """

    return item.get("id") or item.get("url") or item.get("title")


def iter_items(files: Iterable[Path]) -> list[dict[str, Any]]:
    """Yield all JSON objects from *files*, skipping invalid JSON gracefully."""

    aggregated: list[dict[str, Any]] = []
    for fp in files:
        try:
            aggregated.extend(json.loads(fp.read_text("utf-8")))
        except json.JSONDecodeError as exc:
            print(f"⚠️  Skipping {fp.name} – invalid JSON: {exc}")
    return aggregated


def main() -> None:
    # ── CONFIG ────────────────────────────────────────────────────────────
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(exist_ok=True)
    # combine *yesterday's* hourly files so today's crawler can keep running
    yesterday = (date.today() - timedelta(days=1)).isoformat()  # e.g. "2025-06-17"
    # ───────────────────────────────────────────────────────────────────────

    parts = sorted(data_dir.glob(f"finanzen_{yesterday}_*.json"))
    if not parts:
        print(f"No finanzen parts found for {yesterday} – nothing to combine.")
        return

    # 1) read and de‑duplicate
    seen: set[str] = set()
    unique_items: list[dict[str, Any]] = []

    for item in iter_items(parts):
        key = unique_key(item)
        if key is None:  # keep, but cannot dedupe reliably
            unique_items.append(item)
            continue
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    # 2) write out the daily aggregate
    outfile = data_dir / f"finanzen_{yesterday}.json"
    outfile.write_text(json.dumps(unique_items, ensure_ascii=False, indent=2), "utf-8")
    print(f"✅ Saved {len(unique_items)} unique entries to {outfile.name}")

    # 3) delete the individual hourly parts
    for fp in parts:
        try:
            fp.unlink()
            print(f"🗑️  Deleted {fp.name}")
        except Exception as exc:
            print(f"⚠️  Failed to delete {fp.name}: {exc}")


if __name__ == "__main__":
    main()
