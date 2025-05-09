#!/usr/bin/env python3
"""
Grab the current Finanzen.net RSS feed and save it as a time-stamped JSON
inside data/.
"""
from pathlib import Path
import feedparser, json, datetime as dt

FEED_URL = "https://www.finanzen.net/rss/news"

def main() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(exist_ok=True)

    ts = dt.datetime.utcnow().strftime("%Y-%m-%d_%H%M")
    outfile = data_dir / f"finanzen_{ts}.json"

    feed = feedparser.parse(FEED_URL)
    items = [
        {
            "guid": e.id,
            "title": e.title,
            "link": e.link,
            "published": dt.datetime(*e.published_parsed[:6]).isoformat(),
            "source": "finanzen.net",
        }
        for e in feed.entries
    ]

    with outfile.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Wrote {outfile.relative_to(Path.cwd())}  ({len(items)} items)")

if __name__ == "__main__":
    main()
