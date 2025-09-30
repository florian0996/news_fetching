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
            # Multiple paragraphs - store as tuple (heading, list of paragraphs)
            blocks.append(('heading_with_subs', heading, paragraphs))
        else:
            # Single paragraph - keep as one bullet
            body = body.replace("\n", " ")
            blocks.append(('simple', f"<b>{heading}:</b> {body}"))
else:
    # No headings → fall back to sentence splitting
    abbreviations = ['Inc.', 'Ltd.', 'Co.', 'Corp.', 'Dr.', 'Mr.', 'Ms.', 'Mrs.', 'Jr.', 'Sr.',
                     'vs.', 'U.S.', 'U.K.', 'EU.', 'Sen.', 'Rep.', 'St.', 'Prof.']
    placeholder = '[DOT]'
    for abbr in abbreviations:
        weekly_summary = weekly_summary.replace(abbr, abbr.replace('.', placeholder))
    sentences = re.split(r'(?<=\.)\s+', weekly_summary.strip())
    sentences = [s.replace(placeholder, '.') for s in sentences if s.strip()]
    blocks = [('simple', s) for s in sentences]

# Format for Teams card - Markdown bullet list with proper indentation for sub-bullets
teams_lines = []
for block in blocks:
    if block[0] == 'heading_with_subs':
        _, heading, paragraphs = block
        teams_lines.append(f"- **{heading}:**")
        for para in paragraphs:
            # Use 2 spaces for indentation to create sub-bullets in Teams
            teams_lines.append(f"  - {para}")
    else:
        _, content = block
        teams_lines.append(f"- {content}")

weekly_summary_for_teams = "\n".join(teams_lines)

# Format for Email - HTML with nested lists
email_parts = []
for block in blocks:
    if block[0] == 'heading_with_subs':
        _, heading, paragraphs = block
        email_parts.append(f"<li><b>{heading}:</b><ul>")
        for para in paragraphs:
            email_parts.append(f"<li>{para}</li>")
        email_parts.append("</ul></li>")
    else:
        _, content = block
        email_parts.append(f"<li>{content}</li>")

weekly_summary_for_email = "<ul>" + "".join(email_parts) + "</ul>"

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
