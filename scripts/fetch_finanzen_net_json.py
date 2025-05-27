#!/usr/bin/env python3
"""
Grab the current Finanzen.net RSS feed and save it as a time-stamped JSON
inside data/, enriched with extracted (ASCII-only) keywords.
"""
from pathlib import Path
import feedparser, json, datetime as dt
from langdetect import detect
import yake

FEED_URL = "https://www.finanzen.net/rss/news"

# ── transliteration map for German Umlauts & ß ────────────────────────────
GERMAN_CHAR_MAP = {
    ord("Ä"): "Ae", ord("ä"): "ae",
    ord("Ö"): "Oe", ord("ö"): "oe",
    ord("Ü"): "Ue", ord("ü"): "ue",
    ord("ß"): "ss",
}

def transliterate_de(text: str) -> str:
    """
    Replace German umlauts and ß with their ASCII equivalents.
    """
    if not isinstance(text, str):
        return text
    return text.translate(GERMAN_CHAR_MAP)

def extract_keywords(text: str, n: int = 1, top_k: int = 10) -> list[str]:
    """
    Detect language, run YAKE, return top_k keywords (after transliteration).
    """
    # first transliterate so detector & extractor see only ASCII
    text_ascii = transliterate_de(text)
    if not text_ascii:
        return []

    try:
        language = detect(text_ascii)
    except Exception:
        language = "en"  # fallback

    kw_extractor = yake.KeywordExtractor(lan=language, n=n, top=top_k)
    keywords = kw_extractor.extract_keywords(text_ascii)
    # each kw is a tuple (keyword, score)
    return [kw for kw, _ in keywords]

def main() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(exist_ok=True)

    ts = dt.datetime.utcnow().strftime("%Y-%m-%d_%H%M")
    outfile = data_dir / f"finanzen_{ts}.json"

    feed = feedparser.parse(FEED_URL)
    items = []

    for e in feed.entries:
        # transliterate title for storage & keyword extraction
        title_clean = transliterate_de(e.title)
        keywords     = extract_keywords(title_clean)

        items.append({
            "source": "finanzen.net",
            "url":    e.link,
            "title":  title_clean,
            "published_at": dt.datetime(*e.published_parsed[:6]).isoformat(),
            # join your ASCII-only keywords for the "content" field
            "content": ", ".join(keywords),
            "platforms_mentioned": []
        })

    with outfile.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Wrote {outfile.relative_to(Path.cwd())} ({len(items)} items)")

if __name__ == "__main__":
    main()
