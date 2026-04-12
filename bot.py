import os
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def ask_gemini(prompt):
    print(f"API Key present: {'YES' if GEMINI_API_KEY else 'NO'}")
    print(f"API Key length: {len(GEMINI_API_KEY)}")
    print(f"API Key preview: {GEMINI_API_KEY[:8]}..." if GEMINI_API_KEY else "EMPTY")

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    res = requests.post(url, json=payload, headers=headers, params=params)
    print("Gemini status:", res.status_code)
    print("Gemini response:", res.text[:500])
    data = res.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini parse error:", e)
        return None

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    res = requests.post(url, json=payload)
    print("Telegram status:", res.status_code)

def main():
    today = datetime.now().strftime("%A, %d %B %Y")

    prompt = f"""
انت بتكتب رسالة يومية على تيليجرام لصاحبك المصري جن زد اللي عايز يعرف ايه اللي الناس بتتكلم فيه النهارده.

التاريخ النهارده: {today}

المطلوب منك:
1. اجيب اكبر 5 ترندات حقيقية بتتداول دلوقتي في العالم (تيك توك، تويتر، يوتيوب، اخبار فيروسية) — حاجات كل الناس لازم تعرفها
2. اكتب كل حاجة بأسلوب مصري جن زد خفيف ومضحك
3. استخدم ايموجي كتير
4. متكتبش اي مقدمة او كلام زيادة — ابدأ مباشرة بالترندات
5. الرسالة كلها بالعربي

الفورمات يكون كده:
🔥 *1. [اسم الترند]*
[شرح بسيط بأسلوب جن زد مصري في سطرين]

وهكذا لحد 5 ترندات.

في الاخر حط السطر ده:
_ديلي ترندز بتاعتك — {today}_ 🤖
"""

    digest = ask_gemini(prompt)

    if digest:
        header = "📲 *ايه اللي الناس بتتكلم فيه النهارده؟*\n━━━━━━━━━━━━━━━━━━━\n\n"
        send_message(header + digest)
    else:
        send_message("❌ Gemini مردتش — شوف الـ logs في GitHub Actions")

    print("Done!")

if __name__ == "__main__":
    main()
