import json
import requests
from datetime import datetime, timedelta, timezone
import os

# Webhook URL for your Teams workflow
webhook_url = os.getenv("TEAMS_WEBHOOK")

# Load the summaries JSON
with open("data/summary_GPT_3.5.json", "r") as f:
    summaries = json.load(f)

# Use timezone-aware UTC datetime
today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.isoformat()

# Initialize variables
card_body = []
daily_summary = None
weekend_summary = None
weekly_summary = None

# Monday → weekend + weekly summary
if today.weekday() == 0:
    # Friday, Saturday, Sunday
    friday = today - timedelta(days=3)
    saturday = today - timedelta(days=2)
    sunday = today - timedelta(days=1)

    weekend_texts = []
    for d in [friday, saturday, sunday]:
        d_str = d.isoformat()
        if d_str in summaries.get("daily_summary", {}):
            weekend_texts.append(f"**{d_str}:** {summaries['daily_summary'][d_str]}")
        else:
            weekend_texts.append(f"**{d_str}:** No summary.")

    weekend_summary = "\n\n".join(weekend_texts)
    card_body.append({
        "type": "TextBlock",
        "text": f"**Weekend Summary ({friday} → {sunday})**",
        "weight": "Bolder",
        "size": "Medium"
    })
    card_body.append({
        "type": "TextBlock",
        "text": weekend_summary,
        "wrap": True
    })

    # Weekly summary (last Sunday)
    last_sunday_str = sunday.isoformat()
    weekly_summary = summaries.get("weekly_summary", {}).get(last_sunday_str, "No weekly summary.")
    card_body.append({
        "type": "TextBlock",
        "text": f"**Weekly Summary ({last_sunday_str})**",
        "weight": "Bolder",
        "size": "Medium",
        "spacing": "Medium"
    })
    card_body.append({
        "type": "TextBlock",
        "text": weekly_summary,
        "wrap": True
    })

else:
    # Normal day → yesterday only
    daily_summary = summaries.get("daily_summary", {}).get(yesterday_str, "No daily summary.")
    card_body.append({
        "type": "TextBlock",
        "text": f"**Daily Summary ({yesterday_str})**",
        "weight": "Bolder",
        "size": "Medium"
    })
    card_body.append({
        "type": "TextBlock",
        "text": daily_summary,
        "wrap": True
    })

# Build the AdaptiveCard JSON (only the "content" part)
card_content = {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": card_body
}

# Build the payload to send to your Teams workflow
payload = {
    "card": card_content,  # only the AdaptiveCard JSON
    "daily_summary": daily_summary,
    "weekend_summary": weekend_summary,
    "weekly_summary": weekly_summary
}

# Debug: print payload in workflow logs
print("Payload being sent to Teams workflow:")
print(json.dumps(payload, indent=2))

# Send the payload
response = requests.post(webhook_url, json=payload)
print("HTTP Status:", response.status_code)
print("Response body:", response.text)
