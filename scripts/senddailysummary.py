import json
import requests
from datetime import datetime, timedelta
import os

flow_url = os.getenv("TEAMS_WEBHOOK")  # your flow trigger URL

with open("data/summary_GPT_3.5.json", "r") as f:
    summaries = json.load(f)

today = datetime.utcnow().date()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.isoformat()

# Daily summary
daily_summary = summaries.get("daily_summary", {}).get(yesterday_str, "No daily summary.")

# Check if there are articles for companies of interest
company_articles = company_news.get(yesterday_str, {}).get("articles", [])
if company_articles:
    articles_text = "\n".join(
        f"- [{article['title']}]({article['url']})"
        for article in company_articles
    )
    daily_summary += "\n\n**Companies of Interest in the News:**\n" + articles_text

# Build Adaptive Card 
card = {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": []
}

card["body"].append({
    "type": "TextBlock",
    "text": f"**Daily Summary ({yesterday_str})**",
    "weight": "Bolder",
    "size": "Medium"
}) 
card["body"].append({
    "type": "TextBlock",
    "text": daily_summary,
    "wrap": True
})
    
response = requests.post(flow_url, json=card)
print("Status:", response.status_code, response.text)
