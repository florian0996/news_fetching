#!/usr/bin/env python3
"""
Grab the current Finanzen.net RSS feed and save it as a time-stamped JSON
inside data/, enriched with extracted keywords.
"""
from pathlib import Path
import feedparser, json, datetime as dt
from langdetect import detect
import yake

FEED_URL = "https://www.finanzen.net/rss/news"

def extract_keywords(text, n=1, top_k=10):
    if not text:
        return []
    try:
        language = detect(text)
    except:
        language = "en"  # fallback if detection fails
    kw_extractor = yake.KeywordExtractor(lan=language, n=n, top=top_k)
    keywords = kw_extractor.extract_keywords(text)
    return [kw for kw, _ in keywords]

def main() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(exist_ok=True)

    ts = dt.datetime.utcnow().strftime("%Y-%m-%d_%H%M")
    outfile = data_dir / f"finanzen_{ts}.json"

    feed = feedparser.parse(FEED_URL)
    items = [
        {
            "source": "finanzen.net",
            "url": e.link,
            "title": e.title,
            "published_at": dt.datetime(*e.published_parsed[:6]).isoformat(),
            "content": ", ".join(extract_keywords(e.title)),
            "platforms_mentioned": []
        }
        for e in feed.entries
    ]

    with outfile.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Wrote {outfile.relative_to(Path.cwd())}  ({len(items)} items)")

if __name__ == "__main__":
    main()
