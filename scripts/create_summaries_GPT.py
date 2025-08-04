#!/usr/bin/env python
"""
create_summaries_GPT.py
-----------------------
• Mode 'daily': pick second-most-recent finished news_YYYY-MM-DD.json
                and store a 3–5 sentence summary under summaries/summary_daily_{date}.md.

• Mode 'weekly': load the latest 7 daily summaries from data/summary_GPT_3.5.json
                 and write a 12–15 sentence synthesis under summaries/summary_weekly_{date}.md.
                 The first sentence starts with "Calendar Week <N> summary …".
"""
import os
import sys
import argparse
import json
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
    """Return date_str and articles list for daily summary."""
    files = sorted(DATA_DIR.glob("news_????-??-??.json"), key=lambda p: p.name)
    if len(files) < 2:
        print("ERROR: Not enough news files for daily summary.")
        sys.exit(1)
    target = files[-2]
    date_str = target.stem.split('_')[-1]
    articles = json.loads(target.read_text(encoding="utf-8"))
    return date_str, articles


def latest_weekly_summaries(n: int = 7) -> tuple[str, list[str]]:
    """Return last date_str and list of last n daily summary texts from JSON."""
    json_path = DATA_DIR / "summary_GPT_3.5.json"
    if not json_path.exists():
        print(f"::notice ::No summary JSON at {json_path}")
        sys.exit(0)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    daily = data.get("daily_summary", {})
    if not daily:
        print("::notice ::No daily summaries present.")
        sys.exit(0)
    dates = sorted(daily.keys())
    last_dates = dates[-n:]
    summaries = [daily[d] for d in last_dates]
    week_label = last_dates[-1]
    return week_label, summaries


def summarize_daily(date_str: str, articles: list[dict]) -> str:
    """Produce a 3–5 sentence daily summary via GPT."""
    messages = [
        {"role": "system", "content": "You are an expert news summarizer. Produce a concise, forward-looking daily briefing."},
        {"role": "user",   "content": (
            f"Here are today's news items for {date_str}:\n" +
            "\n".join([f"- {art.get('title','').strip()}: {art.get('description') or art.get('content','')}" for art in articles]) +
            "\n\nWrite me a 3–5 sentence summary highlighting key trends and implications."
        )}
    ]
    resp = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages, temperature=0.7, max_tokens=300)
    return resp.choices[0].message.content.strip()


def summarize_weekly(date_str: str, daily_summaries: list[str]) -> str:
    """Produce a 12–15 sentence weekly synthesis via GPT."""
    snippets = [f"- {s.strip()}" for s in daily_summaries]
    prompt_body = "\n".join(snippets)
    week_num = date.fromisoformat(date_str).isocalendar()[1]
    messages = [
        {"role": "system", "content": "You are an expert weekly news analyst."},
        {"role": "user",   "content": (
            f"Calendar Week {week_num} summary: Here are the daily summaries for week ending {date_str}:\n{prompt_body}\n\n"
            "Please produce a 12–15 sentence summary highlighting key themes and forward-looking insights."
        )}
    ]
    resp = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages, temperature=0.7, max_tokens=400)
    return resp.choices[0].message.content.strip()


def main():
    parser = argparse.ArgumentParser(description="Generate daily or weekly summaries via GPT.")
    parser.add_argument("mode", choices=["daily", "weekly"], help="Summary mode to run.")
    args = parser.parse_args()

    if args.mode == "daily":
        date_str, articles = latest_news_file()
        summary = summarize_daily(date_str, articles)
    else:
        date_str, daily_summaries = latest_weekly_summaries()
        summary = summarize_weekly(date_str, daily_summaries)

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
