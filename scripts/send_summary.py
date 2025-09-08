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
    last_saturday = today - timedelta(days=2)
    last_friday = today - timedelta(days=3)
    last_sunday_str = last_sunday.isoformat()
    last_saturday_str = last_saturday.isoformat()
    last_friday_str = last_friday.isoformat()
    weekly_summary = summaries.get("weekly_summary", {}).get(last_sunday_str, "No weekly summary.")
    sunday_summary = summaries.get("daily_summary", {}).get(last_sunday_str, "No Sunday summary.")
    saturday_summary = summaries.get("daily_summary", {}).get(last_saturday_str, "No Saturday summary.")
    friday_summary = summaries.get("daily_summary", {}).get(last_friday_str, "No Friday summary.")
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
            "text": f"**Friday Summary ({last_friday_str})**",
            "weight": "Bolder",
            "size": "Medium",
            "spacing": "Medium"
        }
    )
    card["body"].append(
        {
            "type": "TextBlock",
            "text": friday_summary,
            "wrap": True
        }
    )
    card["body"].append(
        {
            "type": "TextBlock",
            "text": f"**Saturday Summary ({last_saturday_str})**",
            "weight": "Bolder",
            "size": "Medium",
            "spacing": "Medium"
        }
    )
    card["body"].append(
        {
            "type": "TextBlock",
            "text": saturday_summary,
            "wrap": True
        }
    )
    card["body"].append(
        {
            "type": "TextBlock",
            "text": f"**Sunday Summary ({last_sunday_str})**",
            "weight": "Bolder",
            "size": "Medium",
            "spacing": "Medium"
        }
    )
    card["body"].append(
        {
            "type": "TextBlock",
            "text": sunday_summary,
            "wrap": True
        }
    )
    card["body"].append(
        {
            "type": "TextBlock",
            "text": f"**Weekly Summary ({last_sunday_str})**",
            "weight": "Bolder",
            "size": "Medium",
            "spacing": "Medium"
        }
    )
    card["body"].append(
        {
            "type": "TextBlock",
            "text": weekly_summary,
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
