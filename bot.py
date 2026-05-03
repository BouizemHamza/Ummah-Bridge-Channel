import os
import random
import time
import sqlite3
import requests
import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import BadRequest

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@UMMAHBRIDGE")

QURAN_API = "https://api.alquran.cloud/v1"
HADEETH_ENC_LIST_API = "https://hadeethenc.com/api/v1/hadeeths/list/"
HADEETH_ENC_ONE_API = "https://hadeethenc.com/api/v1/hadeeths/one/"
FAWAZ_BASE = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions"
DB_NAME = "bot.db"

TOPIC_KEYWORDS = {
    "topic_faith": "faith",
    "topic_prayer": "prayer",
    "topic_charity": "charity",
    "topic_fasting": "fasting",
    "topic_hajj": "hajj",
    "topic_manners": "manners",
}


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS saved_hadiths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lang TEXT NOT NULL,
            hadith_text TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_subscribers (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            lang TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_hadith(user_id, lang, hadith_text):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO saved_hadiths (user_id, lang, hadith_text, created_at) VALUES (?, ?, ?, ?)",
        (user_id, lang, hadith_text, int(time.time()))
    )
    conn.commit()
    conn.close()


def get_saved_hadiths(user_id, limit=5):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT hadith_text FROM saved_hadiths WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]


def subscribe_daily(user_id, chat_id, lang):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO daily_subscribers (user_id, chat_id, lang, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, chat_id, lang, int(time.time())))
    conn.commit()
    conn.close()


def unsubscribe_daily(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM daily_subscribers WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def get_daily_subscribers():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id, chat_id, lang FROM daily_subscribers")
    rows = cur.fetchall()
    conn.close()
    return rows


async def safe_edit(query, text, markup=None):
    try:
        await query.edit_message_text(text=text, reply_markup=markup)
    except BadRequest:
        await query.message.reply_text(text=text, reply_markup=markup)


def back_btn(lang):
    if lang == "ar":
        return [[InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]]
    if lang == "de":
        return [[InlineKeyboardButton("⬅️ Zurück", callback_data="back_main")]]
    return [[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]


def hadith_action_buttons(lang):
    if lang == "ar":
        return [
            [InlineKeyboardButton("❤️ حفظ الحديث", callback_data="save_current_hadith")],
            [InlineKeyboardButton("🔄 حديث آخر", callback_data="hadith_random")],
            [InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]
        ]
    if lang == "de":
        return [
            [InlineKeyboardButton("❤️ Hadith speichern", callback_data="save_current_hadith")],
            [InlineKeyboardButton("🔄 Weiterer Hadith", callback_data="hadith_random")],
            [InlineKeyboardButton("⬅️ Zurück", callback_data="back_main")]
        ]
    return [
        [InlineKeyboardButton("❤️ Save Hadith", callback_data="save_current_hadith")],
        [InlineKeyboardButton("🔄 Another Hadith", callback_data="hadith_random")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ]


def daily_menu(lang):
    if lang == "ar":
        return [
            [InlineKeyboardButton("✅ الاشتراك في الرسالة اليومية", callback_data="daily_subscribe")],
            [InlineKeyboardButton("❌ إلغاء الاشتراك", callback_data="daily_unsubscribe")],
            [InlineKeyboardButton("🧪 تجربة رسالة الآن", callback_data="daily_test")],
            [InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]
        ]
    if lang == "de":
        return [
            [InlineKeyboardButton("✅ Tägliche Nachricht abonnieren", callback_data="daily_subscribe")],
            [InlineKeyboardButton("❌ Abonnement beenden", callback_data="daily_unsubscribe")],
            [InlineKeyboardButton("🧪 Jetzt testen", callback_data="daily_test")],
            [InlineKeyboardButton("⬅️ Zurück", callback_data="back_main")]
        ]
    return [
        [InlineKeyboardButton("✅ Subscribe to daily message", callback_data="daily_subscribe")],
        [InlineKeyboardButton("❌ Unsubscribe", callback_data="daily_unsubscribe")],
        [InlineKeyboardButton("🧪 Test message now", callback_data="daily_test")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ]


def hadith_menu(lang):
    if lang == "ar":
        return [
            [InlineKeyboardButton("🔄 حديث عربي", callback_data="hadith_random")],
            [InlineKeyboardButton("📚 تصفح الأبواب", callback_data="browse_topics")],
            [InlineKeyboardButton("❤️ محفوظاتي", callback_data="saved_hadiths")],
            [InlineKeyboardButton("⬅️ رجوع", callback_data="back_main")]
        ]

    if lang == "de":
        return [
            [InlineKeyboardButton("🔄 Hadith auf Deutsch", callback_data="hadith_random")],
            [InlineKeyboardButton("📚 Themen durchsuchen", callback_data="browse_topics")],
            [InlineKeyboardButton("❤️ Gespeicherte Hadithe", callback_data="saved_hadiths")],
            [InlineKeyboardButton("⬅️ Zurück", callback_data="back_main")]
        ]

    return [
        [InlineKeyboardButton("📘 Sahih Bukhari", callback_data="bukhari")],
        [InlineKeyboardButton("📗 Sahih Muslim", callback_data="muslim")],
        [InlineKeyboardButton("🔄 Random Hadith", callback_data="hadith_random")],
        [InlineKeyboardButton("🔍 Search Hadiths", callback_data="search_hadith")],
        [InlineKeyboardButton("📚 Browse Topics", callback_data="browse_topics")],
        [InlineKeyboardButton("❤️ Saved Hadiths", callback_data="saved_hadiths")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
    ]


def topic_menu(lang):
    if lang == "ar":
        return [
            [InlineKeyboardButton("🕌 الإيمان", callback_data="topic_faith")],
            [InlineKeyboardButton("🙏 الصلاة", callback_data="topic_prayer")],
            [InlineKeyboardButton("💰 الصدقة", callback_data="topic_charity")],
            [InlineKeyboardButton("🌙 الصيام", callback_data="topic_fasting")],
            [InlineKeyboardButton("🕋 الحج", callback_data="topic_hajj")],
            [InlineKeyboardButton("🤝 الأخلاق", callback_data="topic_manners")],
            [InlineKeyboardButton("⬅️ رجوع", callback_data="hadith")]
        ]
    if lang == "de":
        return [
            [InlineKeyboardButton("🕌 Glaube", callback_data="topic_faith")],
            [InlineKeyboardButton("🙏 Gebet", callback_data="topic_prayer")],
            [InlineKeyboardButton("💰 Spende", callback_data="topic_charity")],
            [InlineKeyboardButton("🌙 Fasten", callback_data="topic_fasting")],
            [InlineKeyboardButton("🕋 Hadsch", callback_data="topic_hajj")],
            [InlineKeyboardButton("🤝 Moral", callback_data="topic_manners")],
            [InlineKeyboardButton("⬅️ Zurück", callback_data="hadith")]
        ]
    return [
        [InlineKeyboardButton("🕌 Faith", callback_data="topic_faith")],
        [InlineKeyboardButton("🙏 Prayer", callback_data="topic_prayer")],
        [InlineKeyboardButton("💰 Charity", callback_data="topic_charity")],
        [InlineKeyboardButton("🌙 Fasting", callback_data="topic_fasting")],
        [InlineKeyboardButton("🕋 Hajj", callback_data="topic_hajj")],
        [InlineKeyboardButton("🤝 Manners", callback_data="topic_manners")],
        [InlineKeyboardButton("⬅️ Back", callback_data="hadith")]
    ]


def get_fatiha(lang):
    try:
        response = requests.get(f"{QURAN_API}/surah/1/quran-uthmani", timeout=10)
        response.raise_for_status()
        ayat = response.json()["data"]["ayahs"]

        title = "📖 سورة الفاتحة" if lang == "ar" else "📖 Al-Fatiha"
        text = title + "\n\n"

        for ayah in ayat:
            text += f"{ayah['numberInSurah']}. {ayah['text']}\n"

        return text
    except Exception as e:
        return f"خطأ في جلب القرآن:\n{e}"


def get_random_hadeethenc_id():
    response = requests.get(
        HADEETH_ENC_LIST_API,
        params={
            "language": "ar",
            "category_id": 1,
            "page": random.randint(1, 5),
            "per_page": 10
        },
        timeout=15
    )
    response.raise_for_status()
    hadiths = response.json().get("data", [])
    if not hadiths:
        return None
    return random.choice(hadiths).get("id")


def get_hadeethenc_by_id(hadith_id, lang):
    response = requests.get(
        HADEETH_ENC_ONE_API,
        params={"language": lang, "id": hadith_id},
        timeout=15
    )
    response.raise_for_status()
    data = response.json()

    return {
        "text": (data.get("hadeeth") or data.get("title") or "").strip(),
        "attribution": data.get("attribution", "HadeethEnc"),
        "grade": data.get("grade", ""),
        "reference": data.get("reference", "")
    }


def fetch_hadeethenc_hadith(lang):
    try:
        hadith_id = get_random_hadeethenc_id()
        if not hadith_id:
            return "لم يتم العثور على حديث." if lang == "ar" else "Kein Hadith gefunden."

        h = get_hadeethenc_by_id(hadith_id, lang)

        if not h["text"]:
            return "لم يتم العثور على نص الحديث. جرّب حديثًا آخر." if lang == "ar" else "Hadith-Text wurde nicht gefunden."

        if lang == "ar":
            ref_line = f"\n📖 المرجع: {h['reference']}" if h["reference"] else ""
            return f"""🕊️ حديث نبوي

━━━━━━━━━━━━━━

{h["text"]}

━━━━━━━━━━━━━━

📚 المصدر: {h["attribution"]}
✅ الدرجة: {h["grade"]}
🔢 HadeethEnc ID: {hadith_id}{ref_line}

🌐 المصدر التقني: HadeethEnc
"""

        ref_line = f"\n📖 Referenz: {h['reference']}" if h["reference"] else ""
        return f"""🕊️ Hadith auf Deutsch

━━━━━━━━━━━━━━

{h["text"]}

━━━━━━━━━━━━━━

📚 Quelle: {h["attribution"]}
✅ Einstufung: {h["grade"]}
🔢 HadeethEnc ID: {hadith_id}{ref_line}

🌐 Technische Quelle: HadeethEnc
"""

    except Exception as e:
        if lang == "ar":
            return f"حدث خطأ أثناء جلب الحديث:\n{e}\n\nـ {int(time.time())}"
        return f"Fehler beim Laden des Hadith:\n{e}\n\nـ {int(time.time())}"


def fetch_fawaz_hadith(book):
    edition = "eng-bukhari" if book == "bukhari" else "eng-muslim"
    title = "Sahih Bukhari" if book == "bukhari" else "Sahih Muslim"

    try:
        response = requests.get(f"{FAWAZ_BASE}/{edition}.json", timeout=20)
        response.raise_for_status()
        hadith = random.choice(response.json()["hadiths"])

        number = hadith.get("hadithnumber", "")
        text = hadith.get("text", "")

        return f"""🕊️ Hadith

📚 Source: {title}
🔢 Hadith number: {number}

━━━━━━━━━━━━━━

{text}

🌐 Technical source: fawazahmed0 Hadith API
"""
    except Exception as e:
        return f"Could not fetch hadith:\n{e}\n\nـ {int(time.time())}"


def search_fawaz_hadith(keyword, lang):
    try:
        results = []

        for edition, title in [("eng-bukhari", "Sahih Bukhari"), ("eng-muslim", "Sahih Muslim")]:
            response = requests.get(f"{FAWAZ_BASE}/{edition}.json", timeout=20)
            response.raise_for_status()

            for hadith in response.json().get("hadiths", []):
                text = hadith.get("text", "")
                if keyword.lower() in text.lower():
                    results.append((hadith, title))

        if not results:
            if lang == "ar":
                return "لم أجد نتيجة. جرّب البحث بالإنجليزية مثل: mercy, prayer, intention."
            if lang == "de":
                return "Kein Ergebnis gefunden. Versuche englische Wörter wie: mercy, prayer, intention."
            return "No result found. Try: mercy, prayer, intention."

        hadith, title = random.choice(results)
        number = hadith.get("hadithnumber", "")
        text = hadith.get("text", "")

        if lang == "ar":
            return f"""🕊️ حديث نبوي

📚 المصدر: {title}
🔢 رقم الحديث: {number}
📖 النص المتوفر حاليًا: English

━━━━━━━━━━━━━━

{text}

🌐 المصدر التقني: fawazahmed0 Hadith API
"""

        if lang == "de":
            return f"""🕊️ Hadith

📚 Quelle: {title}
🔢 Hadith-Nummer: {number}
📖 Der verfügbare Text ist derzeit Englisch

━━━━━━━━━━━━━━

{text}

🌐 Technische Quelle: fawazahmed0 Hadith API
"""

        return f"""🕊️ Hadith

📚 Source: {title}
🔢 Hadith number: {number}

━━━━━━━━━━━━━━

{text}

🌐 Technical source: fawazahmed0 Hadith API
"""
    except Exception as e:
        return f"حدث خطأ أثناء البحث:\n{e}\n\nـ {int(time.time())}"


def build_channel_message():
    try:
        hadith_id = get_random_hadeethenc_id()
        if not hadith_id:
            return "تعذر جلب حديث اليوم."

        ar = get_hadeethenc_by_id(hadith_id, "ar")
        en = get_hadeethenc_by_id(hadith_id, "en")
        de = get_hadeethenc_by_id(hadith_id, "de")

        return f"""📩 رسالة اليوم | Daily Message | Tägliche Nachricht

🕊️ نفس الحديث بثلاث لغات
Same Hadith in Three Languages

━━━━━━━━━━━━━━

🇸🇦 العربية:

{ar["text"]}

━━━━━━━━━━━━━━

🇬🇧 English:

{en["text"]}

━━━━━━━━━━━━━━

🇩🇪 Deutsch:

{de["text"]}

━━━━━━━━━━━━━━

📚 المصدر: {ar["attribution"]}
✅ الدرجة: {ar["grade"]}
🔢 HadeethEnc ID: {hadith_id}

🌍 {CHANNEL_ID}
"""
    except Exception as e:
        return f"تعذر بناء رسالة القناة:\n{e}"


def get_daily_user_message(lang):
    if lang == "ar":
        return "📩 رسالتك اليومية من Ummah Bridge\n\n" + fetch_hadeethenc_hadith("ar")
    if lang == "de":
        return "📩 Deine tägliche Nachricht von Ummah Bridge\n\n" + fetch_hadeethenc_hadith("de")
    return "📩 Your daily message from Ummah Bridge\n\n" + fetch_fawaz_hadith(random.choice(["bukhari", "muslim"]))


async def send_daily_user_messages(context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_daily_subscribers()

    for user_id, chat_id, lang in subscribers:
        try:
            text = get_daily_user_message(lang)
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            print(f"Daily user message error for user {user_id}: {e}")


async def publish_daily_channel(context: ContextTypes.DEFAULT_TYPE):
    try:
        text = build_channel_message()
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
    except Exception as e:
        print(f"Channel publish error: {e}")


async def test_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = build_channel_message()
    await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
    await update.message.reply_text("✅ تم نشر رسالة اختبار في القناة.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")]
    ]

    await update.message.reply_text(
        "اختر اللغة / Choose language / Sprache wählen:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_main_menu(query, lang):
    if lang == "ar":
        text = "مرحبًا بك في Ummah Bridge\n\nاختر قسمًا:"
        buttons = [
            [InlineKeyboardButton("📖 القرآن", callback_data="quran")],
            [InlineKeyboardButton("🕊️ الأحاديث", callback_data="hadith")],
            [InlineKeyboardButton("📩 الرسالة اليومية", callback_data="daily_menu")],
            [InlineKeyboardButton("⚙️ تغيير اللغة", callback_data="change_language")]
        ]
    elif lang == "de":
        text = "Willkommen bei Ummah Bridge\n\nWähle einen Bereich:"
        buttons = [
            [InlineKeyboardButton("📖 Quran", callback_data="quran")],
            [InlineKeyboardButton("🕊️ Hadith", callback_data="hadith")],
            [InlineKeyboardButton("📩 Tägliche Nachricht", callback_data="daily_menu")],
            [InlineKeyboardButton("⚙️ Sprache ändern", callback_data="change_language")]
        ]
    else:
        text = "Welcome to Ummah Bridge\n\nChoose a section:"
        buttons = [
            [InlineKeyboardButton("📖 Quran", callback_data="quran")],
            [InlineKeyboardButton("🕊️ Hadith", callback_data="hadith")],
            [InlineKeyboardButton("📩 Daily Message", callback_data="daily_menu")],
            [InlineKeyboardButton("⚙️ Change language", callback_data="change_language")]
        ]

    await safe_edit(query, text, InlineKeyboardMarkup(buttons))


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    lang = context.user_data.get("lang", "ar")
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if data.startswith("lang_"):
        lang = data.split("_")[1]
        context.user_data["lang"] = lang
        context.user_data["waiting_for_search"] = False
        await show_main_menu(query, lang)

    elif data == "quran":
        await safe_edit(query, get_fatiha(lang), InlineKeyboardMarkup(back_btn(lang)))

    elif data == "hadith":
        await safe_edit(query, "اختر / Choose / Wähle:", InlineKeyboardMarkup(hadith_menu(lang)))

    elif data == "daily_menu":
        if lang == "ar":
            text = "📩 الرسالة اليومية\n\nستصلك رسالة يومية تلقائيًا ما دام البوت يعمل."
        elif lang == "de":
            text = "📩 Tägliche Nachricht\n\nDu erhältst täglich eine Nachricht, solange der Bot läuft."
        else:
            text = "📩 Daily Message\n\nYou will receive a daily message as long as the bot is running."

        await safe_edit(query, text, InlineKeyboardMarkup(daily_menu(lang)))

    elif data == "daily_subscribe":
        subscribe_daily(user_id, chat_id, lang)
        text = "✅ تم الاشتراك في الرسالة اليومية." if lang == "ar" else "✅ Du hast die tägliche Nachricht abonniert." if lang == "de" else "✅ You subscribed to the daily message."
        await safe_edit(query, text, InlineKeyboardMarkup(back_btn(lang)))

    elif data == "daily_unsubscribe":
        unsubscribe_daily(user_id)
        text = "❌ تم إلغاء الاشتراك في الرسالة اليومية." if lang == "ar" else "❌ Du hast die tägliche Nachricht abbestellt." if lang == "de" else "❌ You unsubscribed from the daily message."
        await safe_edit(query, text, InlineKeyboardMarkup(back_btn(lang)))

    elif data == "daily_test":
        text = get_daily_user_message(lang)
        await safe_edit(query, text, InlineKeyboardMarkup(back_btn(lang)))

    elif data == "browse_topics":
        text = "📚 اختر بابًا:" if lang == "ar" else "📚 Wähle ein Thema:" if lang == "de" else "📚 Choose a topic:"
        await safe_edit(query, text, InlineKeyboardMarkup(topic_menu(lang)))

    elif data.startswith("topic_"):
        keyword = TOPIC_KEYWORDS.get(data, "faith")

        if lang in ["ar", "de"]:
            text = fetch_hadeethenc_hadith(lang)
        else:
            text = search_fawaz_hadith(keyword, lang)

        context.user_data["current_hadith"] = text
        await safe_edit(query, text, InlineKeyboardMarkup(hadith_action_buttons(lang)))

    elif data == "search_hadith":
        context.user_data["waiting_for_search"] = True

        if lang == "ar":
            text = "🔍 البحث الحالي يعتمد على النص الإنجليزي. اكتب كلمة مثل: mercy, prayer, intention."
        elif lang == "de":
            text = "🔍 Die Suche verwendet derzeit englische Begriffe, z. B.: mercy, prayer, intention."
        else:
            text = "🔍 Type a keyword: mercy, prayer, intention."

        await safe_edit(query, text, InlineKeyboardMarkup(back_btn(lang)))

    elif data == "bukhari":
        text = fetch_fawaz_hadith("bukhari")
        context.user_data["current_hadith"] = text
        await safe_edit(query, text, InlineKeyboardMarkup(hadith_action_buttons(lang)))

    elif data == "muslim":
        text = fetch_fawaz_hadith("muslim")
        context.user_data["current_hadith"] = text
        await safe_edit(query, text, InlineKeyboardMarkup(hadith_action_buttons(lang)))

    elif data == "hadith_random":
        if lang in ["ar", "de"]:
            text = fetch_hadeethenc_hadith(lang)
        else:
            text = fetch_fawaz_hadith(random.choice(["bukhari", "muslim"]))

        context.user_data["current_hadith"] = text
        await safe_edit(query, text, InlineKeyboardMarkup(hadith_action_buttons(lang)))

    elif data == "save_current_hadith":
        current_hadith = context.user_data.get("current_hadith")

        if not current_hadith:
            msg = "لا يوجد حديث لحفظه الآن." if lang == "ar" else "Es gibt aktuell keinen Hadith zum Speichern." if lang == "de" else "There is no hadith to save right now."
            await safe_edit(query, msg, InlineKeyboardMarkup(back_btn(lang)))
            return

        save_hadith(user_id, lang, current_hadith)
        msg = "✅ تم حفظ الحديث بنجاح." if lang == "ar" else "✅ Hadith wurde gespeichert." if lang == "de" else "✅ Hadith saved successfully."
        await query.message.reply_text(msg)

    elif data == "saved_hadiths":
        saved = get_saved_hadiths(user_id, limit=5)

        if not saved:
            text = "لا توجد أحاديث محفوظة بعد." if lang == "ar" else "Noch keine Hadithe gespeichert." if lang == "de" else "No saved hadiths yet."
        else:
            text = "❤️ آخر الأحاديث المحفوظة:\n\n" if lang == "ar" else "❤️ Zuletzt gespeicherte Hadithe:\n\n" if lang == "de" else "❤️ Latest saved hadiths:\n\n"
            for i, hadith in enumerate(saved, start=1):
                text += f"#{i}\n{hadith[:900]}\n\n━━━━━━━━━━━━━━\n\n"

        await safe_edit(query, text, InlineKeyboardMarkup(back_btn(lang)))

    elif data == "change_language":
        keyboard = [
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")]
        ]
        await safe_edit(query, "اختر اللغة / Choose language / Sprache wählen:", InlineKeyboardMarkup(keyboard))

    elif data == "back_main":
        context.user_data["waiting_for_search"] = False
        await show_main_menu(query, lang)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_search"):
        return

    lang = context.user_data.get("lang", "ar")
    keyword = update.message.text.strip()
    context.user_data["waiting_for_search"] = False

    await update.message.reply_text(
        "🔍 جاري البحث..." if lang == "ar" else "🔍 Suche läuft..." if lang == "de" else "🔍 Searching..."
    )

    text = search_fawaz_hadith(keyword, lang)
    context.user_data["current_hadith"] = text

    await update.message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(hadith_action_buttons(lang))
    )


def main():
    print("BOT_TOKEN exists:", bool(TOKEN))
    print("CHANNEL_ID exists:", bool(CHANNEL_ID))

    if not TOKEN:
        print("❌ BOT_TOKEN not found. Make sure it is set in Railway Variables.")
        return

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test_channel", test_channel))
    app.add_handler(CallbackQueryHandler(handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.job_queue.run_daily(
        send_daily_user_messages,
        time=datetime.time(hour=9, minute=0, second=0)
    )

    app.job_queue.run_daily(
        publish_daily_channel,
        time=datetime.time(hour=9, minute=5, second=0)
    )

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()