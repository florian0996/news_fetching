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
   
    # --- System Prompt ---
    system_message = (
        "You are an expert news summarizer. Produce a concise, daily briefing. "
        "Focus on what is most market-moving."
    )

    # --- User Prompt ---
    article_list = "\n".join([
        f"- {art.get('title','').strip()}: {art.get('description') or art.get('content','')}"
        for art in articles
    ])
   
    user_message = f"""
Here are today's news items for {date_str}:
{article_list}

Write a summary highlighting key trends and implications, **prioritizing quality (market impact) over quantity.**

- If there is significant, market-moving news, write a 3-5 sentence summary.
- If there are only one or two significant items, a shorter 1-2 sentence summary is fine.
- If none of the articles are truly market-moving, please state that (e.g., 'No significant market-moving news today.').

Be precise: if you refer to regulatory actions or corporate deals, give the exact law, agency, or company name.

**Start the summary directly with the main takeaway.** Do not use introductory phrases like 'Today's news highlights...'.
"""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
   
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.2,
        max_tokens=300
    )
    return resp.choices[0].message.content.strip()

def summarize_weekly(date_str: str, daily_summaries: list[str]) -> str:
    """Produce a 12–15 sentence weekly synthesis via GPT."""
   
    snippets = [f"- {s.strip()}" for s in daily_summaries]
    prompt_body = "\n".join(snippets)
   
    # Calculate week number
    try:
        week_num = date.fromisoformat(date_str).isocalendar()[1]
    except ValueError:
        print(f"Error: Invalid date_str '{date_str}'. Expected YYYY-MM-DD.")
        # Handle error appropriately, e.g., use a placeholder or raise
        week_num = "[INVALID WEEK]"

    # --- System Prompt ---
    system_message = (
        "You are an expert weekly news analyst and strategist. "
        "Your task is to synthesize daily briefings into a high-level weekly summary. "
        "Focus on identifying the 2-3 most significant *developing themes* and "
        "their forward-looking implications."
    )

    # --- User Prompt ---
    user_message = f"""
Calendar Week {week_num} summary: Here are the daily summaries for week ending {date_str}:
{prompt_body}

Write a concise analysis (up to 15 sentences). This must be a *synthesis* of the entire week, not just a list of daily events. Identify the major stories and explain why they matter and what they signal for the future.

Your top priority is to focus on news related to these three areas:
1.  **Lending Platforms:** Corporate finance news (funding, deals, M&A, partnerships, financing lines, write-downs).
2.  **Private Debt Funds:** The fund lifecycle (launches, closings, fundraising, LP commitments), portfolio activity (financing, co-investments, defaults, exits, securitization), and relevant regulatory developments.
3.  **Competitors (Fintech/Data/Infra):** Providers in P2P, crowdfunding, or digital credit. Track product launches, partnerships, regulatory licenses (BaFin, FCA), VC funding, strategic hires, M&A, and expansions.

Summarize any significant news in these categories first. General market-moving news outside these topics is a secondary priority.

Whenever regulatory moves or economic policies get mentioned, name the law or agency.
Whenever corporate actions get mentioned, name the exact company or fund.

**IMPORTANT: Start your response with the exact prefix 'Week {week_num}: ' followed immediately by the week's most significant takeaway or developing theme.** Do not use any other introductory phrases.
"""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
   
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.5,
        max_tokens=500
    )
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
