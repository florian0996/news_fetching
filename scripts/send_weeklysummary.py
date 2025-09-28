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

# List of common abbreviations (extend as needed)
abbreviations = ['Inc.', 'Ltd.', 'Co.', 'Corp.', 'Dr.', 'Mr.', 'Ms.', 'Mrs.', 'Jr.', 'Sr.',
    'vs.', 'U.S.', 'U.K.', 'EU.', 'Sen.', 'Rep.', 'St.', 'Prof.']


# Detect headings like **Private Debt Funds:**
heading_pattern = r"\*\*([^:]+):\*\*\s*(.*?)\s*(?=(\*\*[^:]+:\*\*)|$)"

matches = re.findall(heading_pattern, daily_summary, flags=re.DOTALL)

blocks = []
if matches:
    for heading, body, _ in matches:
        heading = heading.strip()
        body = body.strip().replace("\n", " ")
        # Use HTML bold tags instead of Markdown **
        blocks.append(f"<b>{heading}:</b> {body}")
else:
    # No headings → fall back to sentence splitting
    placeholder = '[DOT]'
    for abbr in abbreviations:
        weekly_summary = weekly_summary.replace(abbr, abbr.replace('.', placeholder))

    sentences = re.split(r'(?<=\.)\s+', daily_summary.strip())
    sentences = [s.replace(placeholder, '.') for s in sentences if s.strip()]
    blocks = sentences

# Sentences that should be grouped with the previous one if they start like this
continuation_starts = (
    "This", "Such", "These", "That", "The move"
)

# Group continuation sentences
grouped_blocks = []
for sentence in blocks:
    if grouped_blocks and any(sentence.startswith(start) for start in continuation_starts):
        grouped_blocks[-1] += " " + sentence
    else:
        grouped_blocks.append(sentence)

blocks = grouped_blocks

# Format for Teams card - Markdown bullet list
weekly_summary_for_teams = "\n".join(f"- {block}" for block in blocks if block.strip())

# Format for Email - HTML bullet list
weekly_summary_for_email = "<ul>" + "".join(f"<li>{sentence}</li>" for block in blocks if block.strip()) + "</ul>"

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
