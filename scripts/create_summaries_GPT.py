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
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "summaries"

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY environment variable not set.")
    sys.exit(1)
client = OpenAI(api_key=api_key)

# --- Models for fallback ---
DEFAULT_MODEL = "gpt-3.5-turbo"
FALLBACK_MODELS = ["gpt-4o-mini"]  # Add more models if needed


# --- Utility function ---
def run_completion(messages, temperature=0.7, max_tokens=400, models=None):
    """Run OpenAI completion with fallback models."""
    if models is None:
        models = [DEFAULT_MODEL] + FALLBACK_MODELS
    last_err = None
    for model in models:
        try:
            print(f"Attempting model: {model}")
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            print(f"✔️ Used model: {model}")
            return resp.choices[0].message.content.strip()
        except Exception as e:
            last_err = e
            print(f"⚠️ Model {model} failed: {e}")
            continue
    raise RuntimeError(f"All models failed. Last error: {last_err}")


# --- News retrieval ---
def latest_news_file() -> tuple[str, list[dict]]:
    files = sorted(DATA_DIR.glob("news_????-??-??.json"), key=lambda p: p.name)
    if len(files) < 2:
        print("ERROR: Not enough news files for daily summary.")
        sys.exit(1)
    target = files[-2]
    date_str = target.stem.split('_')[-1]
    articles = json.loads(target.read_text(encoding="utf-8"))
    return date_str, articles


def latest_weekly_summaries(n: int = 7) -> tuple[str, list[str]]:
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


# --- Summarization ---
def summarize_daily(date_str: str, articles: list[dict]) -> str:
    """Produce a 3–5 sentence daily summary via GPT with revised instructions."""

    # --- System Prompt ---
    system_message = (
        "You are an expert news summarizer. Produce a concise, daily briefing. "
        "Focus on what is most market-moving."
    )

    # --- User Prompt (Revised) ---
    article_list = "\n".join([
        f"- {art.get('title','').strip()}: {art.get('description') or art.get('content','')}"
        for art in articles
    ])
    
    user_message = f"""
Here are today's news items for {date_str}:
{article_list}

**Your Task:**
Write a concise, expert market briefing.

**Priority 1: Core Topics**
Your summary *must* first report any significant news related to these three areas:
1.  **Lending Platforms:** Corporate finance news (funding, deals, M&A, partnerships, financing lines, write-downs).
2.  **Private Debt Funds:** The fund lifecycle (launches, closings, fundraising, LP commitments), portfolio activity (financing, co-investments, defaults, exits, securitization), and relevant regulatory developments.
3.  **Competitors of Exaloan AG (Fintech/Data/Infra):** Providers in P2P, crowdfunding, or digital credit. Product launches, partnerships, regulatory licenses (BaFin, FCA), VC funding, strategic hires, M&A, and expansions.

**Priority 2: Secondary Topics**
After summarizing any Priority 1 news, you may briefly include other highly market-moving news if space permits. If there is *no* Priority 1 news, summarize the most significant general market news.

**Output Format & Rules:**
1.  **Start Directly:** Start with the main takeaway. **Do not** use introductory phrases like 'Today's news highlights...' or 'The main news today is...'.
2.  **Length:** The target summary is **3-5 sentences**.
3.  **Exception for Length:** If there are only one or two significant items in total (from any priority), a shorter 1-2 sentence summary is fine.
4.  **Be Precise:** When referencing corporate deals or regulatory actions, use the specific company, agency (e.g., BaFin, FCA), or law names mentioned in the articles.
"""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

    # Use the fallback-enabled completion
    return run_completion(messages, temperature=0.2, max_tokens=300)


def summarize_weekly(date_str: str, daily_summaries: list[str]) -> str:
    """Produce a 12–15 sentence weekly synthesis via GPT with revised instructions."""
    
    snippets = [f"- {s.strip()}" for s in daily_summaries]
    prompt_body = "\n".join(snippets)
    
    # Calculate week number
    week_num = date.fromisoformat(date_str).isocalendar()[1]

    # --- System Prompt ---
    system_message = (
        "You are an expert weekly news analyst and strategist. "
        "Your task is to synthesize daily briefings into a high-level weekly summary. "
        "Focus on identifying the 2-3 most significant *developing themes* and "
        "their forward-looking implications."
    )

    # --- User Prompt (Revised) ---
    user_message = f"""
Calendar Week {week_num} summary: Here are the daily summaries for week ending {date_str}:
{prompt_body}

**Your Task:**
Write a high-level strategic synthesis of the week (target 12-15 sentences). This must be an *analysis*, not just a list of daily events. Your goal is to identify the 2-3 most significant *developing themes* from the daily snippets, connect them, and explain their forward-looking implications.

**Priority 1: Core Thematic Areas**
Your analysis *must* first focus on and synthesize themes related to these three areas:
1.  **Lending Platforms:** Corporate finance (funding, deals, M&A, partnerships, financing lines, write-downs).
2.  **Private Debt Funds:** The fund lifecycle (launches, closings, fundraising, LP commitments), portfolio activity (financing, co-investments, defaults, exits, securitization), and relevant regulatory developments.
3.  **Competitors of Exaloan AG (Fintech/Data/Infra):** Providers in P2P, crowdfunding, or digital credit. Product launches, partnerships, regulatory licenses (BaFin, FCA), VC funding, strategic hires, M&A, and expansions.

**Priority 2: Secondary Themes**
After analyzing the core topics, you may synthesize other major market-moving themes or significant general news that emerged during the week.

**Output Format & Rules:**
1.  **Required Prefix:** You **must** start your response with the exact prefix Week {week_num}:  (e.g., "Week 42: ").
2.  **Start with Takeaway:** Immediately follow the prefix with the week's most significant takeaway or developing theme. **Do not** use any other introductory phrases.
3.  **Length:** The target analysis is **12-15 sentences**.
4.  **Be Precise:** When discussing corporate actions, name the specific company or fund. When discussing policy, name the specific law or agency (e.g., BaFin, FCA).
"""
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

    # Use the fallback-enabled completion
    return run_completion(messages, temperature=0.5, max_tokens=700)


# --- Main workflow ---
def main():
    parser = argparse.ArgumentParser(description="Generate daily or weekly summaries via GPT.")
    parser.add_argument("mode", choices=["daily", "weekly"], help="Summary mode to run.")
    args = parser.parse_args()

    # Generate summary
    if args.mode == "daily":
        date_str, articles = latest_news_file()
        summary = summarize_daily(date_str, articles)
    else:
        date_str, daily_summaries = latest_weekly_summaries()
        summary = summarize_weekly(date_str, daily_summaries)

    # Ensure directories exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Write Markdown summary
    out_md = OUTPUT_DIR / f"summary_{args.mode}_{date_str}.md"
    out_md.write_text(summary, encoding="utf-8")
    print(f"✔️ Wrote {out_md}")

    # Update JSON
    json_path = DATA_DIR / "summary_GPT_3.5.json"
    data = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {"daily_summary": {}, "weekly_summary": {}}
    key = "daily_summary" if args.mode == "daily" else "weekly_summary"
    data[key][date_str] = summary
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"✔️ Updated {json_path}")


if __name__ == "__main__":
    main()
