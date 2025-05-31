#!/usr/bin/env python3
"""
merge_news.py

- Finds today’s “batch” files (data/news_<YYYY-MM-DD>*.json).
- If none are found: prints a message and exits with status 0.
- Otherwise, loads (or creates) data/all_news.json, appends every JSON entry
  in the batch files, deduplicates by link/id, and writes back to all_news.json.
"""

import glob
import json
import os
import sys
from datetime import datetime
from dateutil import tz

def get_today_utc_date_str() -> str:
    """
    Returns today’s date in UTC as 'YYYY-MM-DD'.
    """
    return datetime.utcnow().strftime("%Y-%m-%d")


def load_json(path: str):
    """
    Safe JSON loader. If the file does not exist or is malformed, returns None.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Warning: could not decode JSON in '{path}': {e}", file=sys.stderr)
        return None


def save_json(path: str, data):
    """
    Writes `data` to `path` as pretty-printed JSON (indent=2, ensure_ascii=False).
    """
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def dedupe_news_items(news_list: list) -> list:
    """
    Deduplicate a list of dicts by 'link', or by 'id', or by the entire object if neither key exists.
    Returns a new list in which each unique key appears only once, preserving first-seen order.
    """
    seen_keys = set()
    unique_items = []

    for item in news_list:
        # Decide on a "key" for deduplication. Prefer link, then id, otherwise a JSON-dump fallback.
        if isinstance(item, dict):
            key = item.get("link") or item.get("id") or json.dumps(item, sort_keys=True)
        else:
            key = repr(item)

        if key in seen_keys:
            continue

        seen_keys.add(key)
        unique_items.append(item)

    return unique_items


def main():
    # 1) Determine today's date (UTC) → e.g. "2025-05-31"
    today = get_today_utc_date_str()

    # === CHANGE START ===
    # Match either `news_YYYY-MM-DD.json` OR `news_YYYY-MM-DD_HHMM.json` etc.
    pattern = f"data/news_{today}*.json"
    # === CHANGE END ===

    batch_files = sorted(glob.glob(pattern))

    # 2) If no batch files found, print a message and exit(0) instead of raising an error.
    if not batch_files:
        print(f"No daily batch JSON found for {today} → skipping merge.")
        sys.exit(0)

    # 3) Load existing all_news.json if present, else start with empty list
    all_news_path = "data/all_news.json"
    existing = load_json(all_news_path)
    if existing is None:
        all_news = []
    elif isinstance(existing, list):
        all_news = existing
    else:
        print(f"Warning: '{all_news_path}' is not a list; overwriting it.", file=sys.stderr)
        all_news = []

    # 4) For each batch file, load its contents (expecting a JSON list) and extend all_news
    total_loaded = 0
    for batch_file in batch_files:
        data = load_json(batch_file)
        if data is None:
            print(f"Warning: skipping '{batch_file}' (could not load or decode).", file=sys.stderr)
            continue

        if not isinstance(data, list):
            print(f"Warning: '{batch_file}' does not contain a JSON list; skipping.", file=sys.stderr)
            continue

        all_news.extend(data)
        total_loaded += len(data)
        print(f"Loaded {len(data)} items from '{batch_file}'.")

    # 5) Deduplicate all_news by link/id
    before_dedupe = len(all_news)
    all_news = dedupe_news_items(all_news)
    after_dedupe = len(all_news)

    # 6) (Optional) Sort by published date, if each item has a 'published' or 'published_parsed' field.
    #    If you want to keep them in insertion order, you can comment this block out.
    def _get_timestamp(item):
        if not isinstance(item, dict):
            return 0
        if "published_parsed" in item and item["published_parsed"]:
            try:
                dt = datetime(*item["published_parsed"][:6], tzinfo=tz.tzutc())
                return dt.timestamp()
            except Exception:
                pass
        if "published" in item and isinstance(item["published"], str):
            try:
                dt = datetime.fromisoformat(item["published"])
                return dt.timestamp()
            except Exception:
                pass
        return 0

    try:
        all_news.sort(key=_get_timestamp, reverse=True)
    except Exception:
        # If sorting fails for any reason, just leave the order as is.
        pass

    # 7) Write back to data/all_news.json
    save_json(all_news_path, all_news)

    # 8) Print a summary
    print(
        f"Merged {len(batch_files)} batch file(s) (≈{total_loaded} total items), "
        f"deduped from {before_dedupe} → {after_dedupe} items. "
        f"Wrote to '{all_news_path}'."
    )


if __name__ == "__main__":
    main()
