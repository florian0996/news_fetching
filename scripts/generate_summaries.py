#!/usr/bin/env python3
"""Generate daily and weekly news summaries.

This script reads a JSON file containing news entries, each with at least a
``title`` and optional ``content`` field as well as a publication date under
``published_at`` or ``published``. It outputs a JSON file with two sections:
``daily_summary`` and ``weekly_summary``. Each section maps a date/week key to a
short summary string.
"""

import argparse
import json
import datetime
import os
from collections import defaultdict
from email.utils import parsedate_to_datetime
from dateutil import parser as dateutil_parser

try:
    from gensim.summarization import summarize
except Exception:  # pragma: no cover - gensim optional
    summarize = None


def parse_date(date_str: str) -> datetime.datetime:
    """
    Parse various date string formats to a datetime.
    Uses dateutil.isoparse for ISO-8601 (handles 'Z', offsets, etc.),
    then falls back to email.utils for other formats.
    """
    if not date_str:
        raise ValueError("empty date string")

    # 1) Try dateutil for full ISO-8601 support (incl. trailing Z)
    try:
        return dateutil_parser.isoparse(date_str)
    except (ValueError, TypeError):
        pass

    # 2) Fallback to email.utils (for RFC-2822, etc.)
    try:
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        pass

    # 3) Give up
    raise ValueError(f"Unrecognized date format: {date_str!r}")


def summarize_text(text: str, word_count: int) -> str:
    """Return a condensed summary of ``text``."""
    if summarize:
        try:
            return summarize(text, word_count=word_count)
        except Exception:
            pass
    words = text.split()
    excerpt = " ".join(words[:word_count])
    if len(words) > word_count:
        excerpt += "..."
    return excerpt


def generate_summaries(input_path: str, output_path: str) -> None:
    """Create daily and weekly summaries from ``input_path`` and save them."""

    # ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    daily_texts: dict[str, list[str]] = defaultdict(list)
    weekly_texts: dict[str, list[str]] = defaultdict(list)

    for entry in entries:
        date_raw = entry.get("published_at") or entry.get("published") or ""
        dt = parse_date(date_raw)
        date_key = dt.strftime("%Y-%m-%d")
        week_key = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"

        text_block = " ".join(
            filter(None, [entry.get("title", ""), entry.get("content", "")])
        )
        if text_block:
            daily_texts[date_key].append(text_block)
            weekly_texts[week_key].append(text_block)

    daily_summary: dict[str, str] = {}
    for day, texts in daily_texts.items():
        combined = "\n".join(texts)
        daily_summary[day] = summarize_text(combined, word_count=60)

    weekly_summary: dict[str, str] = {}
    for week, texts in weekly_texts.items():
        combined = "\n".join(texts)
        weekly_summary[week] = summarize_text(combined, word_count=200)

    summary = {"daily_summary": daily_summary, "weekly_summary": weekly_summary}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate daily and weekly summaries from a news JSON file."
    )
    parser.add_argument(
        "-i",
        "--input",
        default="data/all_news.json",
        help="Path to the input news JSON file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="data/summary.json",
        help="Path to the output summary JSON file",
    )
    args = parser.parse_args()
    generate_summaries(args.input, args.output)
