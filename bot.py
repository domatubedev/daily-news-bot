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
            title = a.get("title", "")
            article_url = a.get("url", "")
            source = a.get("source", {}).get("name", "")
            desc = a.get("description", "")
            if title and "[Removed]" not in title and article_url.startswith("http"):
                articles.append({
                    "title": title,
                    "url": article_url,
                    "source": source,
                    "description": desc or title
                })
    return articles[:9]

def ask_gemini(news_list):
    today = datetime.now().strftime("%A, %d %B %Y")

    news_text = ""
    for i, n in enumerate(news_list, 1):
        news_text += f"{i}. TITLE: {n['title']}\n   SOURCE: {n['source']}\n   URL: {n['url']}\n   DESC: {n['description']}\n\n"

    prompt = f"""
انت صاحبي المصري الجن زد. دي أخبار حقيقية من النهارده {today}:

{news_text}

اختار أهم 5 أخبار واكتبهم بالعربي بأسلوب مصري جن زد مضحك مع ايموجي.

قواعد:
- لا تغير أي معلومة — الأسماء والأحداث لازم تبقى صح بالظبط
- بس غير الأسلوب يبقى مصري خفيف
- الـ URL لكل خبر خده بالظبط من اللي فوق — مش تغير فيه حرف

الفورمات بالظبط ده — مفيش حاجة تانية:
🔥 *1. عنوان بالعربي*
شرح سطرين جن زد
🔗 اسم المصدر: URL_هنا

🔥 *2. عنوان بالعربي*
شرح سطرين جن زد
🔗 اسم المصدر: URL_هنا

وهكذا لحد 5 بس.
_ديلي ترندز بتاعتك — {today}_ 🤖
"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.5}
    }

    try:
        res = requests.post(url, json=payload, headers=headers, params=params, timeout=30)
        print("Gemini status:", res.status_code)
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini error:", e)
        return None

def build_fallback(articles):
    today = datetime.now().strftime("%A, %d %B %Y")
    lines = [f"📲 *أخبار النهارده — {today}*\n━━━━━━━━━━━━━━━━━━━\n"]
    emojis = ["🔥", "💻", "🌍", "🤖", "⚡"]
    for i, a in enumerate(articles[:5]):
        lines.append(f"{emojis[i]} *{a['title']}*\n{a['source']}: {a['url']}\n")
    lines.append(f"_ديلي ترندز بتاعتك — {today}_ 🤖")
    return "\n".join(lines)

def send_message(text):
    # split if too long
    if len(text) > 4000:
        text = text[:4000] + "\n\n_... اتقصر عشان تيليجرام مش بيحب الطول_ 😅"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    res = requests.post(url, json=payload)
    print("Telegram status:", res.status_code)
    if res.status_code != 200:
        # retry without markdown
        payload["parse_mode"] = ""
        res = requests.post(url, json=payload)
        print("Telegram retry status:", res.status_code)

def main():
    print("Fetching real news...")
    articles = fetch_real_news()
    print(f"Got {len(articles)} articles")

    print("Asking Gemini...")
    digest = ask_gemini(articles)

    if digest:
        header = "📲 *ايه اللي الناس بتتكلم فيه النهارده؟*\n━━━━━━━━━━━━━━━━━━━\n\n"
        send_message(header + digest)
        print("Sent Gemini digest!")
    else:
        print("Gemini failed, sending fallback...")
        send_message(build_fallback(articles))
        print("Sent fallback!")

if __name__ == "__main__":
    main()
