import json
import requests
from datetime import datetime, timedelta
import os

webhook_url = os.getenv("TEAMS_WEBHOOK")

with open("data/summary_GPT_3.5.json", "r") as f:
    summaries = json.load(f)

today = datetime.utcnow().date()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.isoformat()

# Daily summary (for yesterday)
if yesterday_str in summaries.get("daily_summaries", {}):
    daily_summary = summaries["daily_summaries"][yesterday_str]
else:
    daily_summary = "No daily summary."

# Weekly summary (only Monday → show Sunday)
weekly_summary = None
if today.weekday() == 0:
    last_sunday = today - timedelta(days=1)
    last_sunday_str = last_sunday.isoformat()
    if last_sunday_str in summaries.get("weekly_summaries", {}):
        weekly_summary = summaries["weekly_summaries"][last_sunday_str]
    else:
        weekly_summary = "No weekly summary."

# Build Adaptive Card
card = {
    "type": "message",
    "attachments": [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
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
            }
        }
    ]
}

# Add weekly summary if Monday
if weekly_summary is not None:
    card["attachments"][0]["content"]["body"].append(
        {
            "type": "TextBlock",
            "text": f"**Weekly Summary ({last_sunday_str})**",
            "weight": "Bolder",
            "size": "Medium",
            "spacing": "Medium"
        }
    )
    card["attachments"][0]["content"]["body"].append(
        {
            "type": "TextBlock",
            "text": weekly_summary,
            "wrap": True
        }
    )

response = requests.post(webhook_url, json=card)
print("Status:", response.status_code, response.text)
