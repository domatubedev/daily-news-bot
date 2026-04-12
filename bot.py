import os
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    res = requests.post(url, json=payload)
    data = res.json()
    print("Gemini status:", res.status_code)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini error:", data)
        return "مفيش ترندات اليوم يسطا 😭"

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

🔥 *2. [اسم الترند]*
[شرح]

وهكذا لحد 5 ترندات.

في الاخر حط السطر ده بالظبط:
_ديلي ترندز بتاعتك — {today}_ 🤖
"""

    print("Asking Gemini...")
    digest = ask_gemini(prompt)

    header = f"📲 *ايه اللي الناس بتتكلم فيه النهارده؟*\n━━━━━━━━━━━━━━━━━━━\n\n"
    full_message = header + digest

    send_message(full_message)
    print("Done!")

if __name__ == "__main__":
    main()
