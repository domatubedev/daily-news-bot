import os
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def ask_gemini(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}]
    }
    res = requests.post(url, json=payload, headers=headers, params=params)
    print("Gemini status:", res.status_code)
    data = res.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini error:", data)
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
ابحث دلوقتي على الإنترنت وجيب اكبر 5 ترندات حقيقية بتتداول النهارده {today} في العالم.
خد الترندات من تويتر، يوتيوب، جوجل ترندز، تيك توك — حاجات حقيقية الناس بتتكلم فيها دلوقتي فعلاً.

اكتب كل ترند بالعربي بأسلوب مصري جن زد خفيف ومضحك مع ايموجي كتير.
متكتبش مقدمة — ابدأ مباشرة بالترندات.

الفورمات:
🔥 *1. [اسم الترند الحقيقي]*
[شرح بسيط في سطرين بأسلوب جن زد مصري]

وهكذا لحد 5.

في الاخر:
_ديلي ترندز بتاعتك — {today}_ 🤖
"""

    print("Asking Gemini with Google Search...")
    digest = ask_gemini(prompt)

    if digest:
        header = "📲 *ايه اللي الناس بتتكلم فيه النهارده؟*\n━━━━━━━━━━━━━━━━━━━\n\n"
        send_message(header + digest)
    else:
        send_message("❌ حصل error — شوف الـ logs")

    print("Done!")

if __name__ == "__main__":
    main()
