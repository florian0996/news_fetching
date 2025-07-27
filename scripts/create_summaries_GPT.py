#!/usr/bin/env python
"""
create_summaries_GPT.py
-----------------------
• Mode 'daily'  : pick newest news_YYYY-MM-DD.json and store a 3-5-sentence
                  summary under daily_summary[date].

• Mode 'weekly' : look at the seven most-recent news_*.json files
                  (regardless of gaps) and write a 12-15-sentence synthesis
                  under weekly_summary[YYYY-Www]. 1st sentence must start with
                  "Calendar Week <N> summary …".
"""
import os, sys, argparse, json, re, pathlib
from datetime import date
from openai import OpenAI

# --- Configuration ---
# Base directory of the project (assumes this script lives in scripts/)
BASE_DIR   = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "summaries"

# Ensure OpenAI key is set in env and initialize client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY environment variable not set.")
    sys.exit(1)
client = OpenAI(api_key=api_key)


def latest_news_file() -> tuple[str, list[dict]]:
    """Return (date_str, articles[]) for the most-recent daily JSON file in data/."""
    # 1) Glob only daily dumps YYYY-MM-DD
    pattern = "news_[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"
    files = list(DATA_DIR.glob(pattern))
    if not files:
        print(f"::notice ::No daily news files present in {DATA_DIR}")
        sys.exit(0)

    # 2) Pick the file with the latest modified timestamp
    latest = max(files, key=lambda p: p.stat().st_mtime)

    # 3) Extract date from filename
    fname = latest.name  # e.g. "news_2025-07-27.json"
    m = re.match(r"^news_(\d{4}-\d{2}-\d{2})\.json$", fname)
    if not m:
        raise RuntimeError(f"Unexpected daily news filename format: {fname}")
    date_str = m.group(1)

    # 4) Load and return
    articles = json.loads(latest.read_text())
    return date_str, articles


def summarize_daily(date_str: str, articles: list[dict]) -> str:
    """Generate a daily summary via GPT."""
    snippets = []
    for art in articles:
        title = art.get("title") or ""
        desc  = art.get("description") or art.get("content") or ""
        snippets.append(f"- {title}: {desc}")
    prompt_body = "\n".join(snippets)

    # Build message list
    messages = [
        {"role": "system", "content": (
            "You are an expert news summarizer. Produce a concise, forward-looking daily briefing."
        )},
        {"role": "user", "content": (
            f"Here are today's news items for {date_str}:\n{prompt_body}\n\n"
            "Write me a 3–5 sentence summary highlighting key trends and implications."
        )}
    ]

    # Call new OpenAI client
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


def summarize_weekly(date_str: str, articles: list[dict]) -> str:
    """Generate a weekly analysis summary via GPT."""
    messages = [
        {"role": "system", "content": "You are an expert weekly news analyst."},
        {"role": "user",   "content": (
            f"Summarize the key themes and forward-looking insights for the week ending {date_str}. "
            "Focus on developments that will matter next week."
        )}
    ]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7,
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()


def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=["daily", "weekly"],
        help="Which summary mode to run."
    )
    args = parser.parse_args()

    # Fetch the most recent daily news
    date_str, articles = latest_news_file()

    # Generate summary
    if args.mode == "daily":
        summary = summarize_daily(date_str, articles)
    else:
        summary = summarize_weekly(date_str, articles)

    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"summary_{args.mode}_{date_str}.md"
    out_file.write_text(summary)
    print(f"✔️ Wrote {out_file}")


if __name__ == "__main__":
    main()
