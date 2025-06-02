#!/usr/bin/env python3
"""
merge_news.py

- Finds today’s batch files: data/news_<YYYY-MM-DD>*.json
- If none are found: prints a message and exits(0).
- Otherwise:
    • Loads (or creates) data/all_news.json → appends batch items → dedupes → writes it.
    • Then computes the current quarter (YYYY_Qn), loads that file (or starts empty) → appends the same batch items → dedupes → writes it.
"""

import glob
import json
import os
import sys
from datetime import date, datetime
from dateutil import tz


def get_today_local_date_str() -> str:
    """
    Returns today’s date in the local timezone as 'YYYY-MM-DD'.
    """
    return date.today().strftime("%Y-%m-%d")


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
        if isinstance(item, dict):
            key = item.get("link") or item.get("id") or json.dumps(item, sort_keys=True)
        else:
            key = repr(item)

        if key in seen_keys:
            continue

        seen_keys.add(key)
        unique_items.append(item)

    return unique_items


def get_quarter_str(dt: datetime) -> str:
    """
    Given a datetime (or date) object, return a string like '2025_Q2'.
    Q1: Jan–Mar, Q2: Apr–Jun, Q3: Jul–Sep, Q4: Oct–Dec.
    """
    quarter_num = (dt.month - 1) // 3 + 1
    return f"{dt.year}_Q{quarter_num}"


def main():
    # 1) Determine today's date in local time
    today_str = get_today_local_date_str()

    # 2) Find all files matching data/news_<YYYY-MM-DD>*.json
    pattern = f"data/news_{today_str}*.json"
    batch_files = sorted(glob.glob(pattern))

    # 3) If no daily file is found, skip (exit 0)
    if not batch_files:
        print(f"No daily batch JSON found for {today_str} → skipping merge.")
        sys.exit(0)

    # 4) Load existing data/all_news.json (or start with an empty list)
    all_news_path = "data/all_news.json"
    existing_all = load_json(all_news_path)
    if existing_all is None:
        all_news = []
    elif isinstance(existing_all, list):
        all_news = existing_all
    else:
        print(f"Warning: '{all_news_path}' is not a list; overwriting it.", file=sys.stderr)
        all_news = []

    # 5) Load each batch file, extend all_news, and also collect “today’s batch items”
    total_loaded = 0
    today_batch_items = []
    for batch_file in batch_files:
        data = load_json(batch_file)
        if data is None or not isinstance(data, list):
            print(f"Warning: skipping '{batch_file}' (could not load or not a list)", file=sys.stderr)
            continue

        all_news.extend(data)
        total_loaded += len(data)
        today_batch_items.extend(data)
        print(f"Loaded {len(data)} items from '{batch_file}'.")

    # 6) Deduplicate the combined all_news list
    before_dedupe_all = len(all_news)
    all_news = dedupe_news_items(all_news)
    after_dedupe_all = len(all_news)

    # 7) (Optional) Sort all_news by published date if that field exists
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
        pass

    # 8) Write back to data/all_news.json
    save_json(all_news_path, all_news)

    # 9) Print a summary of all_news merge
    print(
        f"Merged {len(batch_files)} batch file(s) (≈{total_loaded} items), "
        f"deduped from {before_dedupe_all} → {after_dedupe_all} items. "
        f"Wrote to '{all_news_path}'."
    )

    # === NEW: QUARTERLY FILE MERGE ===

    # 10) Compute which quarter this date belongs to, e.g. "2025_Q2"
    today_dt = datetime.fromisoformat(today_str)
    quarter_filename = f"data/news_{get_quarter_str(today_dt)}.json"

    # 11) Load the existing quarter file, or start with an empty list
    existing_quarter = load_json(quarter_filename)
    if existing_quarter is None:
        quarter_list = []
    elif isinstance(existing_quarter, list):
        quarter_list = existing_quarter
    else:
        print(f"Warning: '{quarter_filename}' is not a list; overwriting it.", file=sys.stderr)
        quarter_list = []

    # 12) Append today’s batch items, then dedupe
    before_dedupe_q = len(quarter_list)
    quarter_list.extend(today_batch_items)
    quarter_list = dedupe_news_items(quarter_list)
    after_dedupe_q = len(quarter_list)

    # 13) (Optional) Sort the quarter list by published date (same logic)
    try:
        quarter_list.sort(key=_get_timestamp, reverse=True)
    except Exception:
        pass

    # 14) Write back to data/news_<YYYY>_Qn.json
    save_json(quarter_filename, quarter_list)

    # 15) Print a summary of the quarterly merge
    print(
        f"Quarter file '{quarter_filename}': "
        f"added {len(today_batch_items)} new → deduped from {before_dedupe_q} → {after_dedupe_q} items."
    )


if __name__ == "__main__":
    main()
