import json
import requests
from datetime import datetime, timedelta
import os

flow_url = os.getenv("TEAMS_WEBHOOK")

with open("data/summary_GPT_3.5.json", "r") as f:
    summaries = json.load(f)

today = datetime.utcnow().date()
last_sunday = today - timedelta(days=1)
last_sunday_str = last_sunday.isoformat()

weekly_summary = summaries.get("weekly_summary", {}).get(last_sunday_str, "No weekly summary.")

card = {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": [
        {
            "type": "TextBlock",
            "text": f"Weekly Summary ({last_sunday_str})",
            "weight": "Bolder",
            "size": "Medium"
        },
        {
            "type": "TextBlock",
            "text": weekly_summary,
            "wrap": True
        }
    ]
}

response = requests.post(flow_url, json=card)
print("Status:", response.status_code, response.text)
