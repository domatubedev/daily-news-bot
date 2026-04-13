import os
import requests
import time
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

def fetch_real_news():
    articles = []
    # البحث في آخر 7 أيام لضمان وجود "تريندات الأسبوع"
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # استعلامات بحث قوية وشاملة مع استبعاد الرياضة تماماً
    queries = [
        "(AI OR Nvidia OR OpenAI OR ChatGPT OR Claude OR LLM) -sports -football",
        "(Minecraft OR 'PUBG Mobile' OR Gaming) -sports",
        "(Iran OR Lebanon OR Israel OR USA OR 'Middle East' OR conflict OR war) -NFL -FIFA"
    ]
    
    for q in queries:
        url = "https://newsapi.org/v2/everything"
        params = {
            "apiKey": NEWS_API_KEY,
            "q": q,
            "language": "en",
            "from": one_week_ago,
            "sortBy": "popularity", # عشان نجيب أهم أخبار الأسبوع
            "pageSize": 30, # بنسحب كمية أكبر عشان نضمن نلاقي "Hits"
        }
        
        try:
            res = requests.get(url, params=params)
            data = res.json()
            if data.get("status") == "ok":
                for a in data.get("articles", []):
                    title = a.get("title", "")
                    # فلترة يدوية إضافية لقتل أخبار الرياضة
                    bad_words = ["nfl", "draft", "match", "score", "football", "soccer", "baseball"]
                    if not any(word in title.lower() for word in bad_words):
                        articles.append({
                            "title": title,
                            "url": a.get("url"),
                            "source": a.get("source", {}).get("name"),
                            "description": a.get("description", "")
                        })
        except Exception as e:
            print(f"Error fetching news: {e}")

    # مسح المكرر
    seen_titles = set()
    unique_articles = []
    for art in articles:
        if art['title'].lower() not in seen_titles:
            unique_articles.append(art)
            seen_titles.add(art['title'].lower())
            
    # بنرجع أهم 20 خبر لـ Gemini عشان يختار منهم أقوى 5 أو 7
    return unique_articles[:20]

def ask_gemini(news_list, retries=3, delay=10):
    today = datetime.now().strftime("%A, %d %B %Y")
    news_text = ""
    for i, n in enumerate(news_list, 1):
        news_text += f"{i}. TITLE: {n['title']}\n   SOURCE: {n['source']}\n   URL: {n['url']}\n   DESC: {n['description']}\n\n"

    prompt = f"""
أنت خبير تريندات وجن زد مصري. دي خلاصة أهم أخبار الأسبوع اللي فات (تك، جيمنج، سياسة):

{news_text}

المهمة:
نقي "أجمد" 5 لـ 7 أخبار حصلوا في الأسبوع كله. ركز على Minecraft، PUBG، أخبار الحروب (إيران/لبنان)، والـ AI.
ممنوع نهائياً أي خبر رياضي.

الأسلوب:
مصري جن زد صايع، بيجيب الزتونة من غير رغي كتير، بس بيدي كل خبر حقه في الشرح.

الفورمات:
[مقدمة روشة عن أحداث الأسبوع]

🔥 *1. [العنوان بالعربي]*
[شرح سطرين بالتفصيل الممل بلهجة مصرية روشة]
🔗 المصدر: URL_هنا

_نشرة تريندات الأسبوع - {today}_ 🤖
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 20000, # زيادة عدد التوكنز عشان النشرة تبقى طويلة ودسمة
            "temperature": 0.7
        }
    }

    for attempt in range(1, retries + 1):
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            print(f"Gemini Attempt {attempt} failed: {res.text}")
            time.sleep(delay)
        except Exception as e:
            print(f"Gemini Error: {e}")
            time.sleep(delay)
    return None

def send_message(text):
    if not text: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # تقسيم الرسالة لو طويلة جداً عشان تليجرام بيقبل لحد 4096 حرف
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    else:
        chunks = [text]

    for chunk in chunks:
        payload = {
            "chat_id": CHAT_ID,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        requests.post(url, json=payload)

def main():
    print("Fetching weekly hits (No sports allowed)...")
    articles = fetch_real_news()
    
    if not articles:
        print("No articles found.")
        return

    print(f"Found {len(articles)} potential hits. Asking Gemini...")
    digest = ask_gemini(articles)

    if digest:
        header = "🚀 *خلاصة الأسبوع: من قلب الأحداث والتريندات*\n━━━━━━━━━━━━━━━━━━━\n\n"
        send_message(header + digest)
        print("Message sent successfully!")
    else:
        print("Failed to generate digest.")

if __name__ == "__main__":
    main()
