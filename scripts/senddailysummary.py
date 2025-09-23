import json
import requests
from datetime import datetime, timedelta
import os

flow_url = os.getenv("TEAMS_WEBHOOK")  # your flow trigger URL

# Load summaries
with open("data/summary_GPT_3.5.json", "r") as f:
    summaries = json.load(f)

today = datetime.utcnow().date()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.isoformat()

# Daily summary text
daily_summary = summaries.get("daily_summary", {}).get(yesterday_str, "No daily summary.")

# Load company news
with open("data/news_filtered_for_companies_of_interest.json", "r") as f:
    company_news = json.load(f)

company_articles = company_news.get(yesterday_str, {}).get("articles", [])

# ------------------------
# Teams (Adaptive Card)
# ------------------------
teams_body = [
    {
        "type": "TextBlock",
        "text": f"**Daily Summary ({yesterday_str})**",
        "weight": "Bolder",
        "size": "Medium"
    },
    {
        "type": "TextBlock",
        "text": daily_summary,
        "wrap": True
    }
]

if company_articles:
    teams_body.append({
        "type": "TextBlock",
        "text": "**Companies of Interest in the News:**",
        "weight": "Bolder",
        "spacing": "Medium"
    })
    teams_body.extend(
        {
            "type": "TextBlock",
            "text": f"- [{article['title']}]({article['url']})",
            "wrap": True
        }
        for article in company_articles
    )

teams_card = {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": teams_body
}

# ------------------------
# Email (HTML body)
# ------------------------
email_html = f"""
<h2>Daily Summary ({yesterday_str})</h2>
<p>{daily_summary}</p>
"""

if company_articles:
    email_html += """
    <h3>Companies of Interest in the News:</h3>
    <ul>
    """
    for article in company_articles:
        email_html += f'<li><a href="{article["url"]}">{article["title"]}</a></li>'
    email_html += "</ul>"

# ------------------------
# Final payload (both versions)
# ------------------------
payload = {
    "card": teams_card,
    "emailBody": email_html
}

response = requests.post(flow_url, json=payload)
print("Status:", response.status_code, response.text)
