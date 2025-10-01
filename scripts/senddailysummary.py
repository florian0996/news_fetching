import json
import requests
from datetime import datetime, timedelta
import os
import re

flow_url = os.getenv("TEAMS_WEBHOOK")

# Load summaries
with open("data/summary_GPT_3.5.json", "r") as f:
    summaries = json.load(f)

today = datetime.utcnow().date()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.isoformat()

# ------------------------
# Daily summary processing
# ------------------------
daily_summary = summaries.get("daily_summary", {}).get(yesterday_str, "No daily summary.")

# List of common abbreviations (extend as needed)
abbreviations = ['Inc.', 'Ltd.', 'Co.', 'Corp.', 'Dr.', 'Mr.', 'Ms.', 'Mrs.', 'Jr.', 'Sr.',
    'vs.', 'U.S.', 'U.K.', 'EU.', 'Sen.', 'Rep.', 'St.', 'Prof.']

# Detect headings like **Private Debt Funds:**
heading_pattern = r"\*\*([^:]+):\*\*\s*(.*?)\s*(?=(\*\*[^:]+:\*\*)|$)"

matches = re.findall(heading_pattern, daily_summary, flags=re.DOTALL)

blocks_teams = []  # For Teams (markdown)
blocks_email = []  # For Email (HTML)

if matches:
    for heading, body, _ in matches:
        heading = heading.strip()
        body = body.strip().replace("\n", " ")
        # Teams uses markdown **
        blocks_teams.append(f"**{heading}:** {body}")
        # Email uses HTML <b>
        blocks_email.append(f"<b>{heading}:</b> {body}")
else:
    # No headings → fall back to sentence splitting
    placeholder = '[DOT]'
    for abbr in abbreviations:
        daily_summary = daily_summary.replace(abbr, abbr.replace('.', placeholder))

    sentences = re.split(r'(?<=\.)\s+', daily_summary.strip())
    sentences = [s.replace(placeholder, '.') for s in sentences if s.strip()]
    blocks_teams = sentences
    blocks_email = sentences
    
# Sentences that should be grouped with the previous one if they start like this
continuation_starts = (
    "This", "Such", "These", "That", "The move"
)

# Group continuation sentences for both formats
grouped_blocks_teams = []
grouped_blocks_email = []
for i, sentence in enumerate(blocks_teams):
    if grouped_blocks_teams and any(sentence.startswith(start) for start in continuation_starts):
        grouped_blocks_teams[-1] += " " + sentence
        grouped_blocks_email[-1] += " " + blocks_email[i]
    else:
        grouped_blocks_teams.append(sentence)
        grouped_blocks_email.append(blocks_email[i])

blocks_teams = grouped_blocks_teams
blocks_email = grouped_blocks_email

# ------------------------
# Teams (Markdown style bullets)
# ------------------------
daily_summary_for_teams = "\n".join(f"- {block}" for block in blocks_teams)

# ------------------------
# Email (HTML unordered list)
# ------------------------
daily_summary_for_email = "<ul>" + "".join(f"<li>{b}</li>" for b in blocks_email) + "</ul>"

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
email_html = f"""{daily_summary_for_email}"""

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
