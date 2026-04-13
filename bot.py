import os
import re
import requests
import time
import json
import threading
from datetime import datetime, timedelta

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
NEWS_API_KEY    = os.environ.get("NEWS_API_KEY", "")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

USERS_FILE = "users.json"

AVAILABLE_TOPICS = {
    "ai":        {"label": "🤖 AI & Tech",       "query": "(AI OR Nvidia OR OpenAI OR ChatGPT OR Claude OR LLM OR 'artificial intelligence')"},
    "gaming":    {"label": "🎮 Gaming",           "query": "(Gaming OR Minecraft OR 'PUBG Mobile' OR Steam OR PlayStation OR Xbox)"},
    "politics":  {"label": "🌍 World & Politics", "query": "(Iran OR Lebanon OR Israel OR USA OR 'Middle East' OR conflict OR war OR politics)"},
    "minecraft": {"label": "⛏️ Minecraft",        "query": "Minecraft (update OR mod OR snapshot OR cave OR biome)"},
    "pubg":      {"label": "🔫 PUBG Mobile",      "query": "('PUBG Mobile' OR BGMI OR battlegrounds) (update OR season OR meta OR patch)"},
}

DEFAULT_TOPICS = ["ai", "gaming", "politics"]

# in-memory set of users currently waiting to type their schedule time
AWAITING_SCHEDULE: set = set()

def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# ─── TIME PARSER ──────────────────────────────────────────────────────────────

def parse_schedule_input(text: str):
    """
    Accepts: '10:00PM', '9:30am', '11:00 PM', '23:00', '9PM', '9 AM'
    Returns HH:MM (24h) string, or None if invalid.
    """
    t = text.strip().upper().replace(" ", "")

    # HH:MM AM/PM  e.g. 10:00PM
    m = re.fullmatch(r'(\d{1,2}):(\d{2})(AM|PM)', t)
    if m:
        h, mn, period = int(m.group(1)), int(m.group(2)), m.group(3)
        if not (1 <= h <= 12 and 0 <= mn <= 59):
            return None
        if period == "AM":
            h = 0 if h == 12 else h
        else:
            h = 12 if h == 12 else h + 12
        return f"{h:02d}:{mn:02d}"

    # H AM/PM  e.g. 9PM
    m = re.fullmatch(r'(\d{1,2})(AM|PM)', t)
    if m:
        h, period = int(m.group(1)), m.group(2)
        if not (1 <= h <= 12):
            return None
        if period == "AM":
            h = 0 if h == 12 else h
        else:
            h = 12 if h == 12 else h + 12
        return f"{h:02d}:00"

    # 24h  e.g. 23:00
    m = re.fullmatch(r'(\d{1,2}):(\d{2})', t)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"

    return None

# ─── TELEGRAM HELPERS ─────────────────────────────────────────────────────────

def send_message(chat_id: int, text: str, reply_markup=None):
    if not text:
        return
    url = f"{BASE_URL}/sendMessage"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for i, chunk in enumerate(chunks):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        if reply_markup and i == len(chunks) - 1:
            payload["reply_markup"] = reply_markup
        try:
            requests.post(url, json=payload, timeout=15)
        except Exception as e:
            print(f"[send_message error] {e}")

def answer_callback(callback_query_id: str, text: str = "✅"):
    try:
        requests.post(f"{BASE_URL}/answerCallbackQuery",
                      json={"callback_query_id": callback_query_id, "text": text},
                      timeout=10)
    except Exception as e:
        print(f"[answer_callback error] {e}")

def get_updates(offset: int):
    try:
        res = requests.get(f"{BASE_URL}/getUpdates",
                           params={"offset": offset, "timeout": 30},
                           timeout=35)
        return res.json().get("result", [])
    except Exception as e:
        print(f"[get_updates error] {e}")
        return []

# ─── INLINE KEYBOARD (topics only) ───────────────────────────────────────────

def topics_keyboard(user_topics: list) -> dict:
    buttons = []
    for key, info in AVAILABLE_TOPICS.items():
        tick = "✅ " if key in user_topics else "☑️ "
        buttons.append([{"text": tick + info["label"],
                          "callback_data": f"topic_{key}"}])
    buttons.append([{"text": "💾 حفظ التوبيكس", "callback_data": "topics_save"}])
    return {"inline_keyboard": buttons}

# ─── NEWS & AI ────────────────────────────────────────────────────────────────

def fetch_news_for_topics(topic_keys: list) -> list:
    articles = []
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    bad_words = ["nfl", "nba", "draft", "score", "football", "soccer", "baseball",
                 "cricket", "tennis", "golf", "olympics"]

    for key in topic_keys:
        info = AVAILABLE_TOPICS.get(key)
        if not info:
            continue
        params = {
            "apiKey": NEWS_API_KEY,
            "q": info["query"],
            "language": "en",
            "from": one_week_ago,
            "sortBy": "popularity",
            "pageSize": 15,
        }
        try:
            res = requests.get("https://newsapi.org/v2/everything",
                               params=params, timeout=15)
            data = res.json()
            if data.get("status") == "ok":
                for a in data.get("articles", []):
                    title = a.get("title", "")
                    if not any(w in title.lower() for w in bad_words):
                        articles.append({
                            "title":       title,
                            "url":         a.get("url"),
                            "source":      a.get("source", {}).get("name"),
                            "description": a.get("description", ""),
                            "topic":       key,
                        })
        except Exception as e:
            print(f"[fetch_news error] topic={key}: {e}")

    seen, unique = set(), []
    for art in articles:
        t = art["title"].lower()
        if t not in seen:
            seen.add(t)
            unique.append(art)

    return unique[:25]

def ask_gemini(news_list: list, topic_keys: list):
    today = datetime.now().strftime("%A, %d %B %Y")
    news_text = ""
    for i, n in enumerate(news_list, 1):
        news_text += (f"{i}. [{n['topic'].upper()}] TITLE: {n['title']}\n"
                      f"   SOURCE: {n['source']}  |  URL: {n['url']}\n"
                      f"   DESC: {n['description']}\n\n")

    topics_ar = {"ai":"AI والتكنولوجيا","gaming":"جيمنج","politics":"سياسة وعالم",
                 "minecraft":"ماينكرافت","pubg":"ببجي موبايل"}
    topics_label = " / ".join([topics_ar.get(k, k) for k in topic_keys])

    prompt = f"""
أنت خبير تريندات وجن زد مصري. دي أخبار الأسبوع اللي فات في المواضيع دي: {topics_label}

{news_text}

المهمة:
نقي أجمد 5 لـ 7 أخبار. ممنوع أي خبر رياضي.

الأسلوب:
مصري جن زد صايع، مضحوك وشارح في نفس الوقت.

الفورمات المطلوب بالظبط:
[مقدمة روشة جملة أو اتنين]

🔥 *1. [العنوان بالعربي]*
[شرح سطرين بالتفصيل بلهجة مصرية]
🔗 URL_هنا

🔥 *2. ...*

_نشرة تريندات - {today}_ 🤖
"""

    url = (f"https://generativelanguage.googleapis.com/v1beta/"
           f"models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 20000, "temperature": 0.7},
    }

    for attempt in range(1, 4):
        try:
            res = requests.post(url, json=payload,
                                headers={"Content-Type": "application/json"},
                                timeout=60)
            if res.status_code == 200:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"[Gemini attempt {attempt}] {res.status_code}: {res.text[:200]}")
            time.sleep(10)
        except Exception as e:
            print(f"[Gemini error] {e}")
            time.sleep(10)
    return None

def send_digest_to_user(user_id: str, users: dict):
    user    = users[user_id]
    chat_id = user["chat_id"]
    topics  = user.get("topics", DEFAULT_TOPICS)

    send_message(chat_id, "⏳ بجيب الأخبار وبشيلها على Gemini... استنا ثواني 🤙")

    articles = fetch_news_for_topics(topics)
    if not articles:
        send_message(chat_id, "❌ مفيش أخبار لقدرت أجيبها دلوقتي، حاول تاني بعدين.")
        return

    digest = ask_gemini(articles, topics)
    if digest:
        header = "🚀 *خلاصة التريندات من قلب الأحداث*\n━━━━━━━━━━━━━━━━━━━\n\n"
        send_message(chat_id, header + digest)
        users[user_id]["last_sent_date"] = datetime.now().strftime("%Y-%m-%d")
        save_users(users)
    else:
        send_message(chat_id, "❌ Gemini مش شغال دلوقتي، جرب بعدين.")

# ─── COMMAND HANDLERS ─────────────────────────────────────────────────────────

def handle_start(chat_id: int, first_name: str, user_id: str, users: dict):
    if user_id not in users:
        users[user_id] = {
            "chat_id":        chat_id,
            "first_name":     first_name,
            "topics":         DEFAULT_TOPICS.copy(),
            "schedule_time":  None,
            "last_sent_date": None,
        }
        save_users(users)
        msg = (f"أهلاً *{first_name}* 👋\n"
               "أنا بوت التريندات المصري 🤖\n\n"
               "هبعتلك خلاصة أهم أخبار الأسبوع في المواضيع اللي تختارها!\n\n"
               "الأوامر المتاحة:\n"
               "• /news — ابعت نشرة دلوقتي 🔥\n"
               "• /topics — اختار مواضيعك 🎯\n"
               "• /schedule — حدد وقت إرسال يومي ⏰\n"
               "• /settings — شوف إعداداتك الحالية ⚙️\n\n"
               "ابدأ بـ /topics عشان تحدد اللي يهمك!")
    else:
        users[user_id]["chat_id"] = chat_id
        save_users(users)
        msg = f"هلا *{first_name}*! أنت عندك أكونت قديم 😎\nاستخدم /news للنشرة الفورية."
    send_message(chat_id, msg)

def handle_news(chat_id: int, user_id: str, users: dict):
    if user_id not in users:
        send_message(chat_id, "أبدأ بـ /start الأول يا بشمهندس 😅")
        return
    threading.Thread(target=send_digest_to_user, args=(user_id, users), daemon=True).start()

def handle_topics(chat_id: int, user_id: str, users: dict):
    if user_id not in users:
        send_message(chat_id, "أبدأ بـ /start الأول 🙏")
        return
    user_topics = users[user_id].get("topics", DEFAULT_TOPICS)
    send_message(chat_id,
                 "اختار المواضيع اللي تحب تاخد أخبارها ✅ = متفعل:",
                 reply_markup=topics_keyboard(user_topics))

def handle_schedule(chat_id: int, user_id: str, users: dict):
    if user_id not in users:
        send_message(chat_id, "أبدأ بـ /start الأول 🙏")
        return
    current = users[user_id].get("schedule_time")
    note = f"\n⏰ وقتك الحالي: *{current} UTC*" if current else "\n🚫 الجدولة مش شغالة دلوقتي."
    AWAITING_SCHEDULE.add(user_id)
    send_message(chat_id,
                 f"اكتب الوقت اللي عايز النشرة توصلك فيه:{note}\n\n"
                 "📝 *الفورمات المقبولة:*\n"
                 "`10:00PM` أو `9:30AM` أو `23:00`\n\n"
                 "⚠️ الوقت بتوقيت *UTC* — مصر = UTC+3\n"
                 "يعني لو عايز 10 مساءً مصري، ابعت `7:00PM`\n\n"
                 "🚫 عشان تلغي الجدولة ابعت: `off`\n"
                 "❌ عشان تلغي الأمر ابعت: /cancel")

def handle_settings(chat_id: int, user_id: str, users: dict):
    if user_id not in users:
        send_message(chat_id, "أبدأ بـ /start الأول 🙏")
        return
    user = users[user_id]
    topics_labels = [AVAILABLE_TOPICS[k]["label"] for k in user.get("topics", []) if k in AVAILABLE_TOPICS]
    sched = user.get("schedule_time") or "مش متفعلة"
    last  = user.get("last_sent_date") or "لسه متبعتلكش حاجة"
    msg = (f"⚙️ *إعداداتك يا {user['first_name']}*\n\n"
           f"🎯 *المواضيع:*\n" + "\n".join(f"  • {l}" for l in topics_labels) + "\n\n"
           f"⏰ *وقت الإرسال:* {sched}\n"
           f"📅 *آخر نشرة:* {last}\n\n"
           "عدّل بـ /topics أو /schedule")
    send_message(chat_id, msg)

# ─── SCHEDULE TEXT INPUT HANDLER ─────────────────────────────────────────────

def handle_schedule_input(chat_id: int, user_id: str, text: str, users: dict):
    AWAITING_SCHEDULE.discard(user_id)

    if text.lower().strip() == "off":
        users[user_id]["schedule_time"] = None
        save_users(users)
        send_message(chat_id, "🚫 الجدولة اتألغت. ابعت /news لما تحب.")
        return

    parsed = parse_schedule_input(text)
    if not parsed:
        send_message(chat_id,
                     "❌ فورمات غلط!\n\n"
                     "جرب مثلاً: `10:00PM` أو `9:30AM` أو `23:00`\n"
                     "ابعت /schedule عشان تجرب تاني.")
        return

    users[user_id]["schedule_time"] = parsed
    save_users(users)
    send_message(chat_id,
                 f"✅ تمام! هبعتلك النشرة كل يوم الساعة *{parsed} UTC* 🎯\n"
                 f"_(اللي ادخلته: `{text.strip()}`)_\n\n"
                 "غيّر في أي وقت بـ /schedule")

# ─── CALLBACK QUERY HANDLER ───────────────────────────────────────────────────

def handle_callback(query: dict, users: dict):
    data    = query["data"]
    chat_id = query["message"]["chat"]["id"]
    user_id = str(query["from"]["id"])
    cb_id   = query["id"]

    if user_id not in users:
        answer_callback(cb_id, "أبدأ بـ /start الأول!")
        return

    if data.startswith("topic_"):
        key = data[6:]
        if key in AVAILABLE_TOPICS:
            topics = users[user_id].get("topics", DEFAULT_TOPICS.copy())
            if key in topics:
                topics.remove(key)
                answer_callback(cb_id, f"شيلت {AVAILABLE_TOPICS[key]['label']}")
            else:
                topics.append(key)
                answer_callback(cb_id, f"ضفت {AVAILABLE_TOPICS[key]['label']}")
            users[user_id]["topics"] = topics
            save_users(users)
            try:
                requests.post(f"{BASE_URL}/editMessageReplyMarkup", json={
                    "chat_id": chat_id,
                    "message_id": query["message"]["message_id"],
                    "reply_markup": topics_keyboard(topics),
                }, timeout=10)
            except Exception:
                pass

    elif data == "topics_save":
        topics = users[user_id].get("topics", [])
        if not topics:
            answer_callback(cb_id, "اختار موضوع واحد على الأقل!")
            return
        answer_callback(cb_id, "✅ اتحفظ!")
        labels = [AVAILABLE_TOPICS[k]["label"] for k in topics if k in AVAILABLE_TOPICS]
        send_message(chat_id,
                     "✅ *اتحفظت مواضيعك:*\n" + "\n".join(f"• {l}" for l in labels) +
                     "\n\nدلوقتي ابعت /news للنشرة 🔥")

# ─── SCHEDULER THREAD ─────────────────────────────────────────────────────────

def scheduler_loop():
    while True:
        try:
            now          = datetime.utcnow()
            current_time = now.strftime("%H:%M")
            today_str    = now.strftime("%Y-%m-%d")
            users        = load_users()

            for uid, user in users.items():
                sched = user.get("schedule_time")
                if not sched or sched != current_time:
                    continue
                if user.get("last_sent_date") == today_str:
                    continue
                print(f"[scheduler] Sending to {uid} ({user.get('first_name')})")
                threading.Thread(target=send_digest_to_user, args=(uid, users), daemon=True).start()

        except Exception as e:
            print(f"[scheduler error] {e}")

        time.sleep(60)

# ─── MAIN POLLING LOOP ────────────────────────────────────────────────────────

def main():
    print("🤖 Bot started — polling for updates...")
    threading.Thread(target=scheduler_loop, daemon=True).start()

    offset = 0
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            users  = load_users()

            if "callback_query" in update:
                handle_callback(update["callback_query"], users)
                continue

            msg = update.get("message")
            if not msg:
                continue

            chat_id    = msg["chat"]["id"]
            user_id    = str(msg["from"]["id"])
            first_name = msg["from"].get("first_name", "صديقي")
            text       = msg.get("text", "").strip()

            # /cancel exits schedule-awaiting state
            if text.startswith("/cancel"):
                AWAITING_SCHEDULE.discard(user_id)
                send_message(chat_id, "❌ اتلغت العملية.")
                continue

            # if user is mid-schedule flow, any non-command = time input
            if user_id in AWAITING_SCHEDULE and not text.startswith("/"):
                handle_schedule_input(chat_id, user_id, text, users)
                continue

            if text.startswith("/start"):
                handle_start(chat_id, first_name, user_id, users)
            elif text.startswith("/news"):
                handle_news(chat_id, user_id, users)
            elif text.startswith("/topics"):
                handle_topics(chat_id, user_id, users)
            elif text.startswith("/schedule"):
                handle_schedule(chat_id, user_id, users)
            elif text.startswith("/settings"):
                handle_settings(chat_id, user_id, users)
            else:
                send_message(chat_id,
                             "مش فاهم الأمر ده 😅\n"
                             "الأوامر المتاحة:\n"
                             "/news | /topics | /schedule | /settings")

        time.sleep(1)

if __name__ == "__main__":
    main()
