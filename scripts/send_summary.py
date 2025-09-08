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

daily_summary = None
weekend_summary = None
weekly_summary = None
last_sunday_str = None

if today.weekday() == 0:  # Monday
    # Weekend (Fri–Sun)
    friday = today - timedelta(days=3)
    saturday = today - timedelta(days=2)
    sunday = today - timedelta(days=1)

    weekend_parts = []
    for d in [friday, saturday, sunday]:
        d_str = d.isoformat()
        txt = summaries.get("daily_summary", {}).get(d_str)
        if txt:
            weekend_parts.append(f"**{d_str}:** {txt}")
    weekend_summary = "\n\n".join(weekend_parts) if weekend_parts else "No weekend summary."

    # Weekly summary (last Sunday)
    last_sunday_str = sunday.isoformat()
    weekly_summary = summaries.get("weekly_summary", {}).get(last_sunday_str, "No weekly summary.")

else:
    # Other days: just yesterday’s summary
    daily_summary = summaries.get("daily_summary", {}).get(yesterday_str, "No daily summary.")

# Build Adaptive Card body
body = []

if daily_summary:
    body.append({
        "type": "TextBlock",
        "text": f"**Daily Summary ({yesterday_str})**",
        "weight": "Bolder",
        "size": "Medium"
    })
    body.append({
        "type": "TextBlock",
        "text": daily_summary,
        "wrap": True
    })

if weekend_summary:
    body.append({
        "type": "TextBlock",
        "text": "**Weekend Summary (Fri–Sun)**",
        "weight": "Bolder",
        "size": "Medium",
        "spacing": "Medium"
    })
    body.append({
        "type": "TextBlock",
        "text": weekend_summary,
        "wrap": True
    })

if weekly_summary:
    body.append({
        "type": "TextBlock",
        "text": f"**Weekly Summary ({last_sunday_str})**",
        "weight": "Bolder",
        "size": "Medium",
        "spacing": "Medium"
    })
    body.append({
        "type": "TextBlock",
        "text": weekly_summary,
        "wrap": True
    })

# Assemble final card
card = {
    "type": "message",
    "attachments": [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": body
            }
        }
    ]
}

response = requests.post(webhook_url, json=card)
print("Status:", response.status_code, response.text)
