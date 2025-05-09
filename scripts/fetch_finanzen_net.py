from pathlib import Path
import feedparser, sqlite3, datetime as dt

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)          # create data/ if it doesn't exist
DB_PATH  = DATA_DIR / "finanzen_news.sqlite"

def fetch_and_store():
    feed = feedparser.parse("https://www.finanzen.net/rss/news")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS news (
                       guid TEXT PRIMARY KEY,
                       title TEXT, link TEXT, published TIMESTAMP)""")
        for e in feed.entries:
            try:
                c.execute("INSERT INTO news VALUES (?,?,?,?)",
                          (e.id, e.title, e.link,
                           dt.datetime(*e.published_parsed[:6])))
            except sqlite3.IntegrityError:
                pass      # already stored
        conn.commit()

if __name__ == "__main__":
    fetch_and_store()
