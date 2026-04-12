import os
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
NEWS_API_KEY = os.environ["NEWS_API_KEY"]

def fetch_news(category, query):
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": 5,
        "q": query,
    }
    res = requests.get(url, params=params)
    data = res.json()
    return data.get("articles", [])

def format_articles(articles, emoji):
    lines = []
    for i, a in enumerate(articles[:5], 1):
        title = a.get("title", "No title")
        url = a.get("url", "")
        lines.append(f"{emoji} *{i}. {title}*\n[Read more]({url})")
    return "\n\n".join(lines)

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    res = requests.post(url, json=payload)
    print("Sent:", res.status_code, res.text)

def main():
    today = datetime.now().strftime("%A, %d %B %Y")

    tech_articles = fetch_news("technology", "technology AI software")
    politics_articles = fetch_news("politics", "politics world government")

    tech_section = format_articles(tech_articles, "💻")
    politics_section = format_articles(politics_articles, "🌍")

    message = f"""📰 *Your Daily Digest — {today}*
━━━━━━━━━━━━━━━━━━━

*🔬 TECH*
{tech_section}

━━━━━━━━━━━━━━━━━━━

*🏛 POLITICS*
{politics_section}

━━━━━━━━━━━━━━━━━━━
_Sent automatically at 9PM Cairo time_ 🤖"""

    send_message(message)

if __name__ == "__main__":
    main()
