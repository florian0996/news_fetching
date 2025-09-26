import json
import requests
from datetime import datetime, timedelta
import os
import re

flow_url = os.getenv("TEAMS_WEBHOOK")  # your flow trigger URL

# Load summaries
with open("data/summary_GPT_3.5.json", "r") as f:
    summaries = json.load(f)

today = datetime.utcnow().date()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.isoformat()
import re

# ------------------------
# Daily summary processing
# ------------------------
daily_summary = summaries.get("daily_summary", {}).get(yesterday_str, "No daily summary.")

# List of common abbreviations (extend as needed)
abbreviations = ['Inc.', 'Ltd.', 'Co.', 'Corp.', 'Dr.', 'Mr.', 'Ms.', 'Mrs.', 'Jr.', 'Sr.',
    'vs.', 'U.S.', 'U.K.', 'EU.', 'Sen.', 'Rep.', 'St.', 'Prof.']

# Detect headings like **Private Debt Funds:**
heading_pattern = r"(\*\*[^:]+:\*\*)"

if re.search(heading_pattern, daily_summary):
    # Split into sections on headings
    sections = re.split(rf"(?={heading_pattern})", daily_summary)

    # Clean up and keep only non-empty blocks
    blocks = [s.strip() for s in sections if s.strip()]
else:
    # No headings → fall back to sentence splitting
    # Replace periods in abbreviations with a placeholder
    placeholder = '[DOT]'
    for abbr in abbreviations:
        daily_summary = daily_summary.replace(abbr, abbr.replace('.', placeholder))

    sentences = re.split(r'(?<=\.)\s+', daily_summary.strip())
    sentences = [s.replace(placeholder, '.') for s in sentences if s.strip()]
    blocks = sentences

# ------------------------
# Teams (Markdown style bullets)
# ------------------------
daily_summary_for_teams = "\n".join(f"- {block}" for block in blocks)

# ------------------------
# Email (HTML unordered list)
# ------------------------
# Convert Markdown-style bold (**text**) to HTML bold
blocks_html = [re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", b) for b in blocks]
daily_summary_for_email = "<ul>" + "".join(f"<li>{b}</li>" for b in blocks_html) + "</ul>"

# ------------------------
# Load company news
# ------------------------
with open("data/news_filtered_for_companies_of_interest.json", "r") as f:
    company_news = json.load(f)

company_articles = company_news.get(yesterday_str, {}).get("articles", [])

# ------------------------
# Teams card
# ------------------------
teams_body = [
    {
        "type": "TextBlock",
        "text": f"**Daily Summary ({yesterday_str})**",
        "weight": "Bolder",
        "size": "Medium"
    },
    {
        "type": "TextBlock",
        "text": daily_summary_for_teams,
        "wrap": True
    }
]

if company_articles:
    teams_body.append({
        "type": "TextBlock",
        "text": "**Companies of Interest in the News:**",
        "weight": "Bolder",
        "spacing": "Medium"
    })
    teams_body.extend(
        {
            "type": "TextBlock",
            "text": f"- [{article['title']}]({article['url']})",
            "wrap": True
        }
        for article in company_articles
    )

teams_card = {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": teams_body
}

# ------------------------
# Email HTML body
# ------------------------
email_html = f"""
<h2>Daily Summary ({yesterday_str})</h2>
{daily_summary_for_email}
"""

if company_articles:
    email_html += """
    <h3>Companies of Interest in the News:</h3>
    <ul>
    """
    for article in company_articles:
        email_html += f'<li><a href="{article["url"]}">{article["title"]}</a></li>'
    email_html += "</ul>"

email_subject = f"Daily Summary ({yesterday_str})"

# ------------------------
# Send to Flow
# ------------------------
payload = {
    "card": teams_card,
    "emailBody": email_html,
    "emailSubject": email_subject
}

response = requests.post(flow_url, json=payload)
print("Status:", response.status_code, response.text)
