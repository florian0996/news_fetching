#!/usr/bin/env python
"""
create_summaries_GPT.py
-----------------------
• Mode 'daily'  : pick second-most-recent finished news_YYYY-MM-DD.json
                  and store a 3–5 sentence summary under daily_summary[date].

• Mode 'weekly' : pick the second-most-recent file plus the six files before it
                  (skipping the most recent, which may still be populating), and
                  write a 12–15 sentence synthesis under weekly_summary[YYYY-Www].
                  1st sentence must start with "Calendar Week <N> summary …".
"""
import os
import sys
import argparse
import json
import re
import pathlib
from datetime import date
from openai import OpenAI

# --- Configuration ---
BASE_DIR   = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "summaries"

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY environment variable not set.")
    sys.exit(1)
client = OpenAI(api_key=api_key)


def latest_news_file() -> tuple[str, list[dict]]:
    """Return date_str and articles list for the second-most-recent daily file."""
    pattern = "news_????-??-??.json"
    files = sorted(DATA_DIR.glob(pattern), key=lambda p: p.name)
    if not files:
        print(f"::notice ::No daily news files present in {DATA_DIR}")
        sys.exit(0)

    target = files[-2] if len(files) >= 2 else files[-1]
    m = re.match(r"news_(\d{4}-\d{2}-\d{2})\.json", target.name)
    if not m:
        raise RuntimeError(f"Unexpected filename: {target.name}")
    date_str = m.group(1)
    articles = json.loads(target.read_text(encoding="utf-8"))
    return date_str, articles


def latest_weekly_files(n: int = 7) -> tuple[str, list[dict]]:
    """Return date_str (of second-most-recent) and combined articles from that plus n-1 preceding files."""
    pattern = "news_????-??-??.json"
    files = sorted(DATA_DIR.glob(pattern), key=lambda p: p.name)
    if not files:
        print(f"::notice ::No daily news files present in {DATA_DIR}")
        sys.exit(0)

    # drop the most recent file
    remainder = files[:-1]
    # take last n files (second-most-recent and preceding n-1)
    week_files = remainder[-n:]
    if not week_files:
        print("::notice ::Not enough files for weekly summary, using available ones.")
        week_files = remainder

    # date_str is the date of the latest in this set (the second-most-recent overall)
    latest = week_files[-1]
    m = re.match(r"news_(\d{4}-\d{2}-\d{2})\.json", latest.name)
    date_str = m.group(1) if m else date.today().isoformat()

    # aggregate articles
    articles = []
    for f in week_files:
        batch = json.loads(f.read_text(encoding="utf-8"))
        articles.extend(batch)
    return date_str, articles


def summarize_daily(date_str: str, articles: list[dict]) -> str:
    """Produce a forward-looking 3–5 sentence daily summary via GPT."""
    snippets = [f"- {art.get('title','').strip()}: {art.get('description') or art.get('content','')}" for art in articles]
    prompt_body = "\n".join(snippets)

    messages = [
        {"role": "system", "content": "You are an expert news summarizer. Produce a concise, forward-looking daily briefing."},
        {"role": "user", "content": (
            f"Here are today's news items for {date_str}:\n{prompt_body}\n\n"
            "Write me a 3–5 sentence summary highlighting key trends and implications, "
            "focusing on topics such as credit, loan, lending, fintech startups, digital lending, "
            "credit platforms, loan services, peer-to-peer lending, online loan platforms, investment platforms, "
            "digital wealth management, fractional investing, seed funding, fintech VC, and risk assessment."
        )}
    ]
    resp = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages, temperature=0.7, max_tokens=300)
    return resp.choices[0].message.content.strip()


def summarize_weekly(date_str: str, articles: list[dict]) -> str:
    """Produce a 12–15 sentence weekly synthesis via GPT."""
    snippets = [f"- {art.get('title','').strip()}: {art.get('description') or art.get('content','')}" for art in articles]
    prompt_body = "\n".join(snippets)

    week_num = date.fromisoformat(date_str).isocalendar()[1]
    messages = [
        {"role": "system", "content": "You are an expert weekly news analyst."},
        {"role": "user", "content": (
            f"Calendar Week {week_num} summary: Here are the week's finished news items for week ending {date_str}:\n{prompt_body}\n\n"
            "Summarize the key themes and forward-looking insights, focusing especially on developments in areas such as credit, loan, Exaloan, lending, "
            "fintech startups, digital lending, credit platforms, loan services, peer-to-peer lending, online loan platforms, investment platforms, "
            "digital wealth management, fractional investing, seed funding, fintech VC, and risk assessment."
        )}
    ]
    resp = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages, temperature=0.7, max_tokens=400)
    return resp.choices[0].message.content.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["daily", "weekly"], help="Summary mode to run.")
    args = parser.parse_args()

    if args.mode == "daily":
        date_str, articles = latest_news_file()
        summary = summarize_daily(date_str, articles)
    else:
        date_str, articles = latest_weekly_files(n=7)
        summary = summarize_weekly(date_str, articles)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_md = OUTPUT_DIR / f"summary_{args.mode}_{date_str}.md"
    out_md.write_text(summary, encoding="utf-8")
    print(f"✔️ Wrote {out_md}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "summary_GPT_3.5.json"
    data = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {"daily_summary": {}, "weekly_summary": {}}
    key = "daily_summary" if args.mode == "daily" else "weekly_summary"
    data[key][date_str] = summary
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"✔️ Updated {json_path}")


if __name__ == "__main__":
    main()
