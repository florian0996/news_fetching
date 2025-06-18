import json
import csv
from textblob import TextBlob

# Lists of entities for detection (lowercase)
origination_platforms = [
    "acredius", "anodu", "biz2credit", "bondora", "bondster", "cashenable", "cg24",
    "colectual", "conda", "crowd4cash", "crx", "evenfi", "fellow finance", "finbee",
    "finomark", "flex funding", "fulfin", "funding partner", "geldvoorelkaar", "get income",
    "goparity", "hive finance", "itf group", "klear lending", "kom group", "lend",
    "lendahand", "lending club", "max crowdfund", "mozzeno", "raize", "savy", "spraypay",
    "stately credit", "steward", "stockcrowd in", "tapline", "untapped global",
    "vauraus", "winwinner", "wiseed"
]

competitors = ["dv01", "cardoai", "lendity", "i2invest", "crosslend", "alterest"]

fintech_funds = [
    "avellinia", "awi kmu darlehen", "castlelake", "channel capital", "fasanara",
    "nordix", "scayl", "smart lenders", "tavis capital", "viola credit", "winyield",
    "accial capital", "lendable inc.", "goldfinch", "northern arc capital",
    "pollen street capital", "victory park capital", "ranger capital", "gli finance",
    "prime meridian", "stone ridge"
]

# Keywords for classification
regulation_keywords = ['regulation', 'gesetz', 'bafin', 'aufsicht', 'gesetzgebung', 'compliance']
platform_keywords = ['plattform', 'platform', 'credit', 'lending', 'neobank', 'fintech', 'origination']
funding_keywords = ['funding', 'investment', 'capital', 'fund']
partnership_keywords = ['partnership', 'collaboration', 'alliance', 'cooperation']
insolvency_keywords = ['insolvency', 'restructuring', 'default', 'bankruptcy', 'liquidation', 'debt']

exaloan_keywords = ['exaloan', 'creditshelf', 'scorechain']

competitor_keywords = competitors  # can expand if needed

# Normalize all entity lists for matching
all_names = {
    "platforms": origination_platforms,
    "competitors": competitors,
    "funds": fintech_funds,
}

def detect_entities(text):
    text_lower = text.lower()
    platforms_mentioned = [name for name in all_names["platforms"] if name in text_lower]
    competitors_mentioned = [name for name in all_names["competitors"] if name in text_lower]
    funds_mentioned = [name for name in all_names["funds"] if name in text_lower]
    companies_mentioned = []
    if any(word in text_lower for word in exaloan_keywords):
        companies_mentioned.append("exaloan")
    return platforms_mentioned, competitors_mentioned, funds_mentioned, companies_mentioned

def classify_article(text):
    text_lower = text.lower()
    if any(word in text_lower for word in exaloan_keywords):
        return 'exaloan_reputation'
    elif any(word in text_lower for word in competitor_keywords):
        return 'competitor'
    elif any(word in text_lower for word in regulation_keywords):
        return 'regulation'
    elif any(word in text_lower for word in funding_keywords):
        return 'funding'
    elif any(word in text_lower for word in partnership_keywords):
        return 'partnership'
    elif any(word in text_lower for word in insolvency_keywords):
        return 'insolvency_risk'
    elif any(word in text_lower for word in platform_keywords):
        return 'platform'
    else:
        return 'unknown'

def get_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        label = 'positive'
    elif polarity < -0.1:
        label = 'negative'
    else:
        label = 'neutral'
    return label, polarity

def extract_keywords(text):
    # Simple keyword extraction by splitting commas and spaces, filter out short words
    raw_keywords = [kw.strip() for kw in text.lower().replace(',', ' ').split() if len(kw) > 3]
    # Remove duplicates
    return list(set(raw_keywords))

# Load scraped news
with open('all_news.json', 'r', encoding='utf-8') as f:
    news_data = json.load(f)

enriched_data = []

for article in news_data:
    content = article.get('content', '')
    # Fix date: try published_at or fallback to published, else empty string
    date_raw = article.get('published_at') or article.get('published') or ''
    date = date_raw[:10] if len(date_raw) >= 10 else ''
    title = article.get('title', '')
    
    platforms, competitors_mentioned, funds_mentioned, companies_mentioned = detect_entities(content + " " + title)
    category = classify_article(content + " " + title)
    sentiment_label, sentiment_score = get_sentiment(content)
    keywords = extract_keywords(content + " " + title)
    
    insolvency_flag = any(word in content.lower() for word in insolvency_keywords)
    
    enriched_data.append({
        "date": date,
        "source": article.get('source', ''),
        "title": title,
        "url": article.get('url', ''),
        "category": category,
        "sentiment_label": sentiment_label,
        "sentiment_score": sentiment_score,
        "platforms_mentioned": platforms,
        "competitors_mentioned": competitors_mentioned,
        "funds_mentioned": funds_mentioned,
        "companies_mentioned": companies_mentioned,
        "keywords": keywords,
        "insolvency_risk": insolvency_flag
    })

# Save enriched JSON
with open('enriched_news.json', 'w', encoding='utf-8') as f:
    json.dump(enriched_data, f, indent=2, ensure_ascii=False)

# Optionally save to CSV (flattening lists as comma-separated strings)
csv_columns = [
    "date", "source", "title", "url", "category", "sentiment_label", "sentiment_score",
    "platforms_mentioned", "competitors_mentioned", "funds_mentioned", "companies_mentioned",
    "keywords", "insolvency_risk"
]

with open('enriched_news.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    for row in enriched_data:
        row_csv = row.copy()
        # Join lists into strings for CSV
        row_csv["platforms_mentioned"] = ", ".join(row["platforms_mentioned"])
        row_csv["competitors_mentioned"] = ", ".join(row["competitors_mentioned"])
        row_csv["funds_mentioned"] = ", ".join(row["funds_mentioned"])
        row_csv["companies_mentioned"] = ", ".join(row["companies_mentioned"])
        row_csv["keywords"] = ", ".join(row["keywords"])
        writer.writerow(row_csv)

print("✅ Enrichment complete: 'enriched_news.json' and 'enriched_news.csv' created.")
