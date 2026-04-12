import os
import requests
import time
from datetime import datetime, timedelta

# تأكد من إضافة الـ Secrets دي في GitHub أو كمتغيرات بيئة
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

def fetch_real_news():
    articles = []
    days_back = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    
    # 1. كلمات بحث محددة جداً (Strict Queries)
    # ضفنا "NOT sports" عشان نهرب من وجع الدماغ ده
    queries = [
        "(AI OR Nvidia OR OpenAI OR ChatGPT) AND (breakthrough OR release) -sports",
        "(Minecraft OR 'PUBG Mobile') AND (update OR leaks OR season) -sports",
        "(Iran OR Israel OR Lebanon OR US Army OR war OR conflict) -football -nfl"
    ]
    
    for q in queries:
        url = "https://newsapi.org/v2/everything"
        params = {
            "apiKey": NEWS_API_KEY,
            "q": q,
            "language": "en",
            "from": days_back,
            "sortBy": "relevancy", # غيرنا لـ relevancy عشان نضمن إنه يلتزم بكلمات البحث بتاعتك
            "pageSize": 15,
        }
        
        try:
            res = requests.get(url, params=params)
            data = res.json()
            if data.get("status") == "ok":
                for a in data.get("articles", []):
                    title = a.get("title", "").lower()
                    # فلتر إضافي بالبايثون عشان نقتل أي خبر رياضي تماماً
                    bad_words = ["nfl", "draft", "football", "match", "score", "player"]
                    if not any(word in title for word in bad_words):
                        articles.append({
                            "title": a.get("title"),
                            "url": a.get("url"),
                            "source": a.get("source", {}).get("name"),
                            "description": a.get("description", "")
                        })
        except Exception as e:
            print(f"Error: {e}")

    # مسح المكرر
    seen_titles = set()
    unique_articles = []
    for art in articles:
        if art['title'].lower() not in seen_titles:
            unique_articles.append(art)
            seen_titles.add(art['title'].lower())
            
    # رجع أهم 10
    return unique_articles[:10]
def ask_gemini(news_list, retries=3, delay=10):
    today = datetime.now().strftime("%A, %d %B %Y")
    news_text = ""
    for i, n in enumerate(news_list, 1):
        news_text += f"{i}. TITLE: {n['title']}\n   SOURCE: {n['source']}\n   URL: {n['url']}\n   DESC: {n['description']}\n\n"

    prompt = f"""
أنت خبير تريندات وجن زد مصري صايع. دي أخبار العالم (تك، جيمنج، وحروب) النهاردة {today}:

{news_text}

المهمة:
نقي أهم 5 أخبار "خبطات" (The Hits). لو في خبر حرب كبير أو تحديث Minecraft/PUBG قالب الدنيا، لازم يطلع فوق.

القواعد:
- اخلط بين المجالات (تك، جيمنج، سياسة).
- الأسلوب: مصري جن زد، روش، بيفهم في الأصول (أخبار الحروب تتوصف بجدية مع لمحة صياعة من غير تريقة).
- الأسماء والـ URLs لازم تكون صح 100%.

الفورمات:
[مقدمة مصرية روشة سطر واحد عن هبد العالم النهاردة]

🔥 *1. [عنوان بالعربي]*
[شرح سطرين جن زد يوضح ليه الخبر ده مهم]
🔗 المصدر: URL_هنا

_نشرة هبد بليل - {today}_ 🤖
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.7}
    }

    for attempt in range(1, retries + 1):
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            time.sleep(delay)
        except:
            time.sleep(delay)
    return None

def send_message(text):
    if not text: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    res = requests.post(url, json=payload)
    if res.status_code != 200:
        print(f"Telegram Error: {res.status_code}")
        print(f"Response: {res.text}") # ده هيقولك بالظبط ليه تليجرام رفض الرسالة

def main():
    print("Fetching the hits...")
    articles = fetch_real_news()
    
    if not articles:
        print("No news found.")
        return

    print("Asking Gemini to wrap it up...")
    digest = ask_gemini(articles)

    if digest:
        header = "🌍 *الخلاصة والزتونة اللي فاتتكم النهاردة*\n━━━━━━━━━━━━━━━━━━━\n\n"
        send_message(header + digest)
        print("Done!")
    else:
        # Fallback بسيط لو Gemini هنج
        fallback = "⚠️ حصل مشكلة في تجميع النشرة، بس دي أهم العناوين:\n\n"
        for a in articles[:5]:
            fallback += f"• {a['title']}\n"
        send_message(fallback)

if __name__ == "__main__":
    main()
