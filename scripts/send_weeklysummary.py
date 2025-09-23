import json
import requests
from datetime import datetime, timedelta
import os
import re

flow_url = os.getenv("TEAMS_WEBHOOK")

with open("data/summary_GPT_3.5.json", "r") as f:
    summaries = json.load(f)

today = datetime.utcnow().date()
last_sunday = today - timedelta(days=1)
last_sunday_str = last_sunday.isoformat()

weekly_summary = summaries.get("weekly_summary", {}).get(last_sunday_str, "No weekly summary.")

# Split weekly summary into sentences
sentences = re.split(r'(?<=\.)\s+', weekly_summary.strip())

# Format for Teams card - Markdown bullet list
weekly_summary_for_teams = "\n".join(f"- {sentence}" for sentence in sentences if sentence.strip())

# Format for Email - HTML bullet list
weekly_summary_for_email = "<ul>" + "".join(f"<li>{sentence}</li>" for sentence in sentences if sentence.strip()) + "</ul>"

# Build Teams card body (like daily summary style)
teams_body = [
    {
        "type": "TextBlock",
        "text": f"**Weekly Summary ({last_sunday_str})**",
        "weight": "Bolder",
        "size": "Medium"
    },
    {
        "type": "TextBlock",
        "text": weekly_summary_for_teams,
        "wrap": True
    }
]

teams_card = {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": teams_body
}

# Email HTML body (like daily summary format)
email_html = f"""
<h2>Weekly Summary ({last_sunday_str})</h2>
{weekly_summary_for_email}
"""

email_subject = f"Weekly Summary ({last_sunday_str})"

payload = {
    "card": teams_card,
    "emailBody": email_html,
    "emailSubject": email_subject
}

response = requests.post(flow_url, json=payload)
print("Status:", response.status_code, response.text)
