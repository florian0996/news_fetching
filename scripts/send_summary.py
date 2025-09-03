import json
import requests
from datetime import datetime, timedelta
import os

webhook_url = os.getenv("TEAMS_WEBHOOK")

with open("data/summary_GPT_3.5.json", "r") as f:
    summaries = json.load(f)

today = datetime.utcnow().date()
today_str = today.isoformat()

message_parts = []

# Daily summary
if today_str in summaries.get("daily_summaries", {}):
    message_parts.append(f"**Daily Summary ({today_str})**\n{summaries['daily_summaries'][today_str]}")

# Weekly summary (only Monday)
if today.weekday() == 0:
    last_sunday = today - timedelta(days=1)
    last_sunday_str = last_sunday.isoformat()
    if last_sunday_str in summaries.get("weekly_summaries", {}):
        message_parts.append(f"**Weekly Summary ({last_sunday_str})**\n{summaries['weekly_summaries'][last_sunday_str]}")

if message_parts:
    payload = {"text": "\n\n".join(message_parts)}
    response = requests.post(webhook_url, json=payload)
    print("Status:", response.status_code, response.text)
else:
    print("No summary for today.")
