import json
import requests
from datetime import datetime, timedelta
import os
import re

flow_url = os.getenv("TEAMS_WEBHOOK")

with open("data/summary_GPT_3.5.json", "r") as f:
    summaries = json.load(f)

today = datetime.utcnow().date()
last_sunday = today - timedelta(days=2)
last_sunday_str = last_sunday.isoformat()

weekly_summary = summaries.get("weekly_summary", {}).get(last_sunday_str, "No weekly summary.")

# Detect headings like **Private Debt Funds:**
heading_pattern = r"\*\*([^:]+):\*\*\s*(.*?)(?=(\*\*[^:]+:\*\*)|$)"
matches = re.findall(heading_pattern, weekly_summary, flags=re.DOTALL)

blocks = []
if matches:
    for heading, body, _ in matches:
        heading = heading.strip()
        body = body.strip()
        
        # Check if body contains multiple sentences separated by newlines
        # Split by newlines first to preserve natural breaks
        paragraphs = [p.strip() for p in body.split('\n') if p.strip()]
        
        if len(paragraphs) > 1:
            # Multiple paragraphs - create main bullet with sub-bullets
            main_bullet = f"<b>{heading}:</b>"
            blocks.append(main_bullet)
            for para in paragraphs:
                blocks.append(f"  - {para}")
        else:
            # Single paragraph - keep as one bullet
            body = body.replace("\n", " ")
            blocks.append(f"<b>{heading}:</b> {body}")
else:
    # No headings → fall back to sentence splitting
    abbreviations = ['Inc.', 'Ltd.', 'Co.', 'Corp.', 'Dr.', 'Mr.', 'Ms.', 'Mrs.', 'Jr.', 'Sr.',
                     'vs.', 'U.S.', 'U.K.', 'EU.', 'Sen.', 'Rep.', 'St.', 'Prof.']
    placeholder = '[DOT]'
    for abbr in abbreviations:
        weekly_summary = weekly_summary.replace(abbr, abbr.replace('.', placeholder))
    sentences = re.split(r'(?<=\.)\s+', weekly_summary.strip())
    sentences = [s.replace(placeholder, '.') for s in sentences if s.strip()]
    blocks = sentences

# Format for Teams card - Markdown bullet list
weekly_summary_for_teams = "\n".join(f"- {block}" for block in blocks if block.strip())

# Format for Email - HTML with nested lists
email_blocks = []
i = 0
while i < len(blocks):
    block = blocks[i]
    # Check if this is a main heading followed by sub-bullets
    if block.startswith("<b>") and not block.endswith("</b>"):
        # Just the heading, sub-bullets follow
        email_blocks.append(f"<li>{block}")
        i += 1
        # Collect sub-bullets
        sub_bullets = []
        while i < len(blocks) and blocks[i].strip().startswith("- "):
            sub_bullets.append(blocks[i].strip()[2:])  # Remove "- " prefix
            i += 1
        if sub_bullets:
            email_blocks.append("<ul>")
            for sub in sub_bullets:
                email_blocks.append(f"<li>{sub}</li>")
            email_blocks.append("</ul>")
        email_blocks.append("</li>")
    else:
        # Regular bullet point
        email_blocks.append(f"<li>{block}</li>")
        i += 1

weekly_summary_for_email = "<ul>" + "".join(email_blocks) + "</ul>"

# Build Teams card body
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

# Email HTML body
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
