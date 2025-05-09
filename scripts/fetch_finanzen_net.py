import feedparser, sqlite3, datetime

FEED_URL   = "https://www.finanzen.net/rss/news"
DB_PATH    = "finanzen_news.sqlite"

def fetch_and_store():
    feed  = feedparser.parse(FEED_URL)
    conn  = sqlite3.connect(DB_PATH)
    c     = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS news (
                   guid TEXT PRIMARY KEY,
                   title TEXT, link TEXT, published TIMESTAMP)""")

    for entry in feed.entries:
        try:
            c.execute("INSERT INTO news VALUES (?,?,?,?)", (
                entry.id,
                entry.title,
                entry.link,
                datetime.datetime(*entry.published_parsed[:6])
            ))
        except sqlite3.IntegrityError:
            # duplicate – already captured earlier
            pass
    conn.commit(); conn.close()

if __name__ == "__main__":
    fetch_and_store()
