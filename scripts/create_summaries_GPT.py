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
import os, sys, json, re, glob, textwrap, itertools, pathlib, datetime as dt
import openai

# ─── configuration ─────────────────────────────────────────────────────────
ROOT      = pathlib.Path(__file__).resolve().parents[1]   # repo root
DATA_DIR  = ROOT / "data"
OUT_PATH  = DATA_DIR / "summary GPT 3.5.json"
MODEL     = "gpt-3.5-turbo"
openai.api_key = os.getenv("OPENAI_API_KEY")
# ───────────────────────────────────────────────────────────────────────────

def latest_news_file() -> tuple[str, list[dict]]:
    """Return (date_str, articles[]) for the most-recent raw JSON file."""
    files = sorted(glob.glob(str(DATA_DIR / "news_*.json")))
    if not files:
        print("::notice ::No raw news files present")
        sys.exit(0)
    latest = files[-1]
    date_str = re.search(r"news_(\d{4}-\d{2}-\d{2})", latest).group(1)
    return date_str, json.load(open(latest))

def seven_recent_articles() -> tuple[str, list[dict]]:
    """Return (ISO-week key, aggregated_articles[]) from last seven files."""
    files = sorted(glob.glob(str(DATA_DIR / "news_*.json")), reverse=True)[:7]
    if not files:
        print("::notice ::No raw news files present")
        sys.exit(0)
    articles = list(itertools.chain.from_iterable(json.load(open(f)) for f in files))
    today = dt.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    return f"{iso_year}-W{iso_week:02d}", articles

def gpt_summary(prompt: str, max_tokens: int) -> str:
    resp = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()

def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "daily").lower()
    if mode not in {"daily", "weekly"}:
        sys.exit("Usage: create_summaries_GPT.py [daily|weekly]")

    # ------------------------------------------------ daily mode ----------
    if mode == "daily":
        date_str, articles = latest_news_file()
        prompt = textwrap.dedent(f"""
            Provide an objective news summary (3–5 sentences) for analysts.
            Date: {date_str}
            ---
        """) + "\n\n".join(f"{a.get('title')}\n{a.get('content')}" for a in articles)

        summary_txt = gpt_summary(prompt, max_tokens=600)

        key_path = ("daily_summary", date_str)

    # ------------------------------------------------ weekly mode ---------
    else:  # weekly
        week_key, articles = seven_recent_articles()
        iso_week_num = week_key.split("-W")[1]
        prompt = textwrap.dedent(f"""
            Summarise the following {len(articles)} news items in 12–15 sentences.
            Tone: objective, analyst-friendly.
            First sentence must begin: "Calendar Week {iso_week_num} summary".
            ---
        """) + "\n\n".join(f"{a.get('title')}\n{a.get('content')}" for a in articles)

        summary_txt = gpt_summary(prompt, max_tokens=1200)

        key_path = ("weekly_summary", week_key)

    # -------------------------- write / update output JSON ---------------
    doc = {"daily_summary": {}, "weekly_summary": {}}
    if OUT_PATH.exists():
        doc.update(json.load(open(OUT_PATH)))

    parent_key, child_key = key_path
    doc[parent_key][child_key] = summary_txt

    with open(OUT_PATH, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    print(f"Wrote {parent_key[:-8]} summary for {child_key} → {OUT_PATH.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
