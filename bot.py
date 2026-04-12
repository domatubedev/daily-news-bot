import os
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

def fetch_real_news():
    articles = []
    queries = ["artificial intelligence", "programming technology", "world news"]
    for q in queries:
        url = "https://newsapi.org/v2/everything"
        params = {
            "apiKey": NEWS_API_KEY,
            "q": q,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 3,
        }
        res = requests.get(url, params=params)
        data = res.json()
        for a in data.get("articles", []):
            if a.get("title") and a.get("url") and "[Removed]" not in a.get("title", ""):
                articles.append({
                    "title": a["title"],
                    "url": a["url"],
                    "source": a.get("source", {}).get("name", ""),
                    "description": a.get("description", "")
                })
    return articles[:9]

def ask_gemini(news_list):
    today = datetime.now().strftime("%A, %d %B %Y")
    
    news_text = ""
    for i, n in enumerate(news_list, 1):
        news_text += f"{i}. {n['title']}\n   Source: {n['source']}\n   URL: {n['url']}\n   Summary: {n['description']}\n\n"

    prompt = f"""
انت صاحبي المصري الجن زد. عندك الأخبار الحقيقية دي من النهارده {today}:

{news_text}

دلوقتي اختار أهم 5 أخبار من اللي فوق واكتبهم بالعربي بأسلوب مصري جن زد مضحك وخفيف مع ايموجي.
لكل خبر حط الـ URL الحقيقي بتاعه من اللي فوق.

الفورمات بالظبط:
🔥 *1. [عنوان مختصر بالعربي]*
[شرح في سطرين بأسلوب جن زد مصري مضحك]
🔗 [اسم المصدر](URL)

لحد 5 أخبار. في الاخر:
_ديلي ترندز بتاعتك — {today}_ 🤖
"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    res = requests.post(url, json=payload, headers=headers, params=params)
    print("Gemini status:", res.status_code)
    data = res.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        print("Gemini error:", data)
        return None

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    res = requests.post(url, json=payload)
    print("Telegram status:", res.status_code)

def main():
    today = datetime.now().strftime("%A, %d %B %Y")
    print("Fetching real news...")
    articles = fetch_real_news()
    print(f"Got {len(articles)} articles")

    print("Asking Gemini to rewrite...")
    digest = ask_gemini(articles)

    if digest:
        header = "📲 *ايه اللي الناس بتتكلم فيه النهارده؟*\n━━━━━━━━━━━━━━━━━━━\n\n"
        send_message(header + digest)
    else:
        send_message("❌ حصل error — شوف الـ logs")

    print("Done!")

if __name__ == "__main__":
    main()
