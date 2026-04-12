import os
import requests
import time
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

# trusted tech/AI sources only
TECH_SOURCES = "the-verge,techcrunch,wired,ars-technica,hacker-news,engadget"

def fetch_real_news():
    articles = []
    queries = [
        ("AI LLM model release", TECH_SOURCES),
        ("programming developer tools github", TECH_SOURCES),
        ("artificial intelligence breakthrough", TECH_SOURCES),
    ]
    for q, sources in queries:
        url = "https://newsapi.org/v2/everything"
        params = {
            "apiKey": NEWS_API_KEY,
            "q": q,
            "sources": sources,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 3,
        }
        res = requests.get(url, params=params)
        data = res.json()
        print(f"Query '{q}': status={data.get('status')}, total={data.get('totalResults')}")
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

def ask_gemini(news_list, retries=4, delay=15):
    today = datetime.now().strftime("%A, %d %B %Y")

    news_text = ""
    for i, n in enumerate(news_list, 1):
        news_text += f"{i}. TITLE: {n['title']}\n   SOURCE: {n['source']}\n   URL: {n['url']}\n   DESC: {n['description']}\n\n"

    prompt = f"""
انت صاحبي المصري الجن زد. دي أخبار تقنية وAI حقيقية من النهارده {today}:

{news_text}

اختار أهم 5 أخبار واكتبهم بالعربي بأسلوب مصري جن زد مضحك مع ايموجي.

قواعد:
- أخبار تقنية وAI وكودينج بس — لو لقيت خبر رياضي أو سياسي تجاهله
- لا تغير أي معلومة — الأسماء والأحداث لازم تبقى صح بالظبط
- الـ URL لكل خبر خده بالظبط من اللي فوق — مش تغير فيه حرف

الفورمات:
[مقدمة مصرية خفيفة سطر واحد بس]

🔥 *1. عنوان بالعربي*
شرح سطرين جن زد
🔗 اسم المصدر: URL_هنا

وهكذا لحد 5.
_ديلي ترندز بتاعتك — {today}_ 🤖
"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 10000, "temperature": 0.5}
    }

    for attempt in range(1, retries + 1):
        try:
            print(f"Gemini attempt {attempt}/{retries}...")
            res = requests.post(url, json=payload, headers=headers, params=params, timeout=60)
            print(f"Gemini status: {res.status_code}")
            if res.status_code == 503:
                print(f"503 - waiting {delay}s...")
                time.sleep(delay)
                continue
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Gemini error attempt {attempt}: {e}")
            time.sleep(delay)

    return None

def build_fallback(articles):
    today = datetime.now().strftime("%A, %d %B %Y")
    lines = [f"📲 *أخبار التك النهارده — {today}*\n━━━━━━━━━━━━━━━━━━━\n"]
    emojis = ["🔥", "💻", "🤖", "⚡", "🚀"]
    for i, a in enumerate(articles[:5]):
        lines.append(f"{emojis[i]} *{a['title']}*\n{a['source']}: {a['url']}\n")
    lines.append(f"_ديلي ترندز بتاعتك — {today}_ 🤖")
    return "\n".join(lines)

def send_message(text):
    if len(text) > 4096:
        text = text[:4096] + "\n\n_... اتقصر_ 😅"
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
        payload["parse_mode"] = ""
        res = requests.post(url, json=payload)
        print("Telegram retry status:", res.status_code)

def main():
    print("Fetching tech/AI news...")
    articles = fetch_real_news()
    print(f"Got {len(articles)} articles")

    if not articles:
        send_message("❌ مفيش أخبار اتجبت النهارده — شوف الـ logs")
        return

    print("Asking Gemini...")
    digest = ask_gemini(articles)

    if digest:
        header = "📲 *ايه اللي الناس بتتكلم فيه النهارده؟*\n━━━━━━━━━━━━━━━━━━━\n\n"
        send_message(header + digest)
        print("Sent!")
    else:
        print("Gemini failed, fallback...")
        send_message(build_fallback(articles))

if __name__ == "__main__":
    main()
