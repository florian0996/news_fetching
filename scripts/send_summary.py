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


# Weekly summary (only if Monday)
weekly_summary = None
if today.weekday() == 0:
    last_sunday = today - timedelta(days=1)
    last_sunday_str = last_sunday.isoformat()
    weekly_summary = summaries.get("weekly_summary", {}).get(last_sunday_str, "No weekly summary.")
    sunday_summary = summaries.get("daily_summary", {}).get(last_sunday_str, "No Sunday summary.")
    combined_title = f"**Sunday + Weekly Summary ({last_sunday_str})**"
    combined_text = (
    f"<b>Sunday Summary ({last_sunday_str}):</b><br>{sunday_summary}<br><br>"
    f"<b>Weekly Summary ({last_sunday_str}):</b><br>{weekly_summary}"
    )
else:
    # Daily summary
    daily_summary = summaries.get("daily_summary", {}).get(yesterday_str, "No daily summary.")

# Build Adaptive Card (NO wrapper, just the card)
card = {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": []
}

# Add weekly summary if Monday
if weekly_summary is not None:
    card["body"].append(
        {
            "type": "TextBlock",
            "text": f"{combined_title}",
            "weight": "Bolder",
            "size": "Medium",
            "spacing": "Medium"
        }
    )
    card["body"].append(
        {
            "type": "TextBlock",
            "text": combined_text,
            "wrap": True
        }
    )
else: 
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
