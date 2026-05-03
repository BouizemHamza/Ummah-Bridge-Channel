import os
import random
import time
import sqlite3
import requests
import datetime
import html

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


def esc(text):
    return html.escape(str(text or ""))


def line():
    return "\n━━━━━━━━━━━━━━\n"


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
        await query.edit_message_text(
            text=text,
            reply_markup=markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except BadRequest:
        await query.message.reply_text(
            text=text,
            reply_markup=markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )


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

        title = "📖 <b>سورة الفاتحة</b>" if lang == "ar" else "📖 <b>Al-Fatiha</b>"
        text = title + line()

        for ayah in ayat:
            text += f"<b>{ayah['numberInSurah']}.</b> {esc(ayah['text'])}\n"

        text += line()
        text += "🌐 <i>AlQuran Cloud API</i>"

        return text
    except Exception as e:
        return f"❌ خطأ في جلب القرآن:\n<code>{esc(e)}</code>"


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


def format_hadeethenc_hadith(hadith_id, h, lang):
    if lang == "ar":
        ref_line = f"\n📖 <b>المرجع:</b> {esc(h['reference'])}" if h["reference"] else ""
        return f"""🕊️ <b>حديث نبوي</b>{line()}
{esc(h["text"])}
{line()}
📚 <b>المصدر:</b> {esc(h["attribution"])}
✅ <b>الدرجة:</b> {esc(h["grade"])}
🔢 <b>HadeethEnc ID:</b> <code>{esc(hadith_id)}</code>{ref_line}

🌐 <i>المصدر التقني: HadeethEnc</i>
"""

    if lang == "de":
        ref_line = f"\n📖 <b>Referenz:</b> {esc(h['reference'])}" if h["reference"] else ""
        return f"""🕊️ <b>Hadith auf Deutsch</b>{line()}
{esc(h["text"])}
{line()}
📚 <b>Quelle:</b> {esc(h["attribution"])}
✅ <b>Einstufung:</b> {esc(h["grade"])}
🔢 <b>HadeethEnc ID:</b> <code>{esc(hadith_id)}</code>{ref_line}

🌐 <i>Technische Quelle: HadeethEnc</i>
"""

    ref_line = f"\n📖 <b>Reference:</b> {esc(h['reference'])}" if h["reference"] else ""
    return f"""🕊️ <b>Hadith</b>{line()}
{esc(h["text"])}
{line()}
📚 <b>Source:</b> {esc(h["attribution"])}
✅ <b>Grade:</b> {esc(h["grade"])}
🔢 <b>HadeethEnc ID:</b> <code>{esc(hadith_id)}</code>{ref_line}

🌐 <i>Technical source: HadeethEnc</i>
"""


def fetch_hadeethenc_hadith(lang):
    try:
        hadith_id = get_random_hadeethenc_id()
        if not hadith_id:
            return "❌ لم يتم العثور على حديث." if lang == "ar" else "❌ Kein Hadith gefunden."

        h = get_hadeethenc_by_id(hadith_id, lang)

        if not h["text"]:
            return "❌ لم يتم العثور على نص الحديث. جرّب حديثًا آخر." if lang == "ar" else "❌ Hadith-Text wurde nicht gefunden."

        return format_hadeethenc_hadith(hadith_id, h, lang)

    except Exception as e:
        if lang == "ar":
            return f"❌ حدث خطأ أثناء جلب الحديث:\n<code>{esc(e)}</code>\n\nـ {int(time.time())}"
        return f"❌ Fehler beim Laden des Hadith:\n<code>{esc(e)}</code>\n\nـ {int(time.time())}"


def fetch_fawaz_hadith(book):
    edition = "eng-bukhari" if book == "bukhari" else "eng-muslim"
    title = "Sahih Bukhari" if book == "bukhari" else "Sahih Muslim"

    try:
        response = requests.get(f"{FAWAZ_BASE}/{edition}.json", timeout=20)
        response.raise_for_status()
        hadith = random.choice(response.json()["hadiths"])

        number = hadith.get("hadithnumber", "")
        text = hadith.get("text", "")

        return f"""🕊️ <b>Hadith</b>{line()}
📚 <b>Source:</b> {esc(title)}
🔢 <b>Hadith number:</b> <code>{esc(number)}</code>
{line()}
{esc(text)}

🌐 <i>Technical source: fawazahmed0 Hadith API</i>
"""
    except Exception as e:
        return f"❌ Could not fetch hadith:\n<code>{esc(e)}</code>\n\nـ {int(time.time())}"


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
                return "❌ لم أجد نتيجة. جرّب البحث بالإنجليزية مثل: <code>mercy</code>, <code>prayer</code>, <code>intention</code>."
            if lang == "de":
                return "❌ Kein Ergebnis gefunden. Versuche englische Wörter wie: <code>mercy</code>, <code>prayer</code>, <code>intention</code>."
            return "❌ No result found. Try: <code>mercy</code>, <code>prayer</code>, <code>intention</code>."

        hadith, title = random.choice(results)
        number = hadith.get("hadithnumber", "")
        text = hadith.get("text", "")

        if lang == "ar":
            return f"""🕊️ <b>حديث نبوي</b>{line()}
📚 <b>المصدر:</b> {esc(title)}
🔢 <b>رقم الحديث:</b> <code>{esc(number)}</code>
📖 <b>النص المتوفر حاليًا:</b> English
{line()}
{esc(text)}

🌐 <i>المصدر التقني: fawazahmed0 Hadith API</i>
"""

        if lang == "de":
            return f"""🕊️ <b>Hadith</b>{line()}
📚 <b>Quelle:</b> {esc(title)}
🔢 <b>Hadith-Nummer:</b> <code>{esc(number)}</code>
📖 <b>Der verfügbare Text ist derzeit Englisch</b>
{line()}
{esc(text)}

🌐 <i>Technische Quelle: fawazahmed0 Hadith API</i>
"""

        return f"""🕊️ <b>Hadith</b>{line()}
📚 <b>Source:</b> {esc(title)}
🔢 <b>Hadith number:</b> <code>{esc(number)}</code>
{line()}
{esc(text)}

🌐 <i>Technical source: fawazahmed0 Hadith API</i>
"""
    except Exception as e:
        return f"❌ حدث خطأ أثناء البحث:\n<code>{esc(e)}</code>\n\nـ {int(time.time())}"


def build_channel_message():
    try:
        hadith_id = get_random_hadeethenc_id()
        if not hadith_id:
            return "❌ تعذر جلب حديث اليوم."

        ar = get_hadeethenc_by_id(hadith_id, "ar")
        en = get_hadeethenc_by_id(hadith_id, "en")
        de = get_hadeethenc_by_id(hadith_id, "de")

        return f"""📩 <b>رسالة اليوم | Daily Message | Tägliche Nachricht</b>

🕊️ <b>نفس الحديث بثلاث لغات</b>
<i>Same Hadith in Three Languages</i>
{line()}
🇸🇦 <b>العربية</b>

{esc(ar["text"])}
{line()}
🇬🇧 <b>English</b>

{esc(en["text"])}
{line()}
🇩🇪 <b>Deutsch</b>

{esc(de["text"])}
{line()}
📚 <b>المصدر:</b> {esc(ar["attribution"])}
✅ <b>الدرجة:</b> {esc(ar["grade"])}
🔢 <b>HadeethEnc ID:</b> <code>{esc(hadith_id)}</code>

🌍 {esc(CHANNEL_ID)}
"""
    except Exception as e:
        return f"❌ تعذر بناء رسالة القناة:\n<code>{esc(e)}</code>"


def get_daily_user_message(lang):
    if lang == "ar":
        return "📩 <b>رسالتك اليومية من Ummah Bridge</b>\n\n" + fetch_hadeethenc_hadith("ar")
    if lang == "de":
        return "📩 <b>Deine tägliche Nachricht von Ummah Bridge</b>\n\n" + fetch_hadeethenc_hadith("de")
    return "📩 <b>Your daily message from Ummah Bridge</b>\n\n" + fetch_fawaz_hadith(random.choice(["bukhari", "muslim"]))


async def send_daily_user_messages(context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_daily_subscribers()

    for user_id, chat_id, lang in subscribers:
        try:
            text = get_daily_user_message(lang)
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            print(f"Daily user message error for user {user_id}: {e}")


async def publish_daily_channel(context: ContextTypes.DEFAULT_TYPE):
    try:
        text = build_channel_message()
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        print(f"Channel publish error: {e}")


async def test_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = build_channel_message()
    await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML", disable_web_page_preview=True)
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
        text = "🌉 <b>مرحبًا بك في Ummah Bridge</b>\n\nاختر قسمًا:"
        buttons = [
            [InlineKeyboardButton("📖 القرآن", callback_data="quran")],
            [InlineKeyboardButton("🕊️ الأحاديث", callback_data="hadith")],
            [InlineKeyboardButton("📩 الرسالة اليومية", callback_data="daily_menu")],
            [InlineKeyboardButton("⚙️ تغيير اللغة", callback_data="change_language")]
        ]
    elif lang == "de":
        text = "🌉 <b>Willkommen bei Ummah Bridge</b>\n\nWähle einen Bereich:"
        buttons = [
            [InlineKeyboardButton("📖 Quran", callback_data="quran")],
            [InlineKeyboardButton("🕊️ Hadith", callback_data="hadith")],
            [InlineKeyboardButton("📩 Tägliche Nachricht", callback_data="daily_menu")],
            [InlineKeyboardButton("⚙️ Sprache ändern", callback_data="change_language")]
        ]
    else:
        text = "🌉 <b>Welcome to Ummah Bridge</b>\n\nChoose a section:"
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
        await safe_edit(query, "🕊️ <b>اختر / Choose / Wähle:</b>", InlineKeyboardMarkup(hadith_menu(lang)))

    elif data == "daily_menu":
        if lang == "ar":
            text = "📩 <b>الرسالة اليومية</b>\n\nستصلك رسالة يومية تلقائيًا ما دام البوت يعمل."
        elif lang == "de":
            text = "📩 <b>Tägliche Nachricht</b>\n\nDu erhältst täglich eine Nachricht, solange der Bot läuft."
        else:
            text = "📩 <b>Daily Message</b>\n\nYou will receive a daily message as long as the bot is running."

        await safe_edit(query, text, InlineKeyboardMarkup(daily_menu(lang)))

    elif data == "daily_subscribe":
        subscribe_daily(user_id, chat_id, lang)
        text = "✅ <b>تم الاشتراك في الرسالة اليومية.</b>" if lang == "ar" else "✅ <b>Du hast die tägliche Nachricht abonniert.</b>" if lang == "de" else "✅ <b>You subscribed to the daily message.</b>"
        await safe_edit(query, text, InlineKeyboardMarkup(back_btn(lang)))

    elif data == "daily_unsubscribe":
        unsubscribe_daily(user_id)
        text = "❌ <b>تم إلغاء الاشتراك في الرسالة اليومية.</b>" if lang == "ar" else "❌ <b>Du hast die tägliche Nachricht abbestellt.</b>" if lang == "de" else "❌ <b>You unsubscribed from the daily message.</b>"
        await safe_edit(query, text, InlineKeyboardMarkup(back_btn(lang)))

    elif data == "daily_test":
        text = get_daily_user_message(lang)
        await safe_edit(query, text, InlineKeyboardMarkup(back_btn(lang)))

    elif data == "browse_topics":
        text = "📚 <b>اختر بابًا:</b>" if lang == "ar" else "📚 <b>Wähle ein Thema:</b>" if lang == "de" else "📚 <b>Choose a topic:</b>"
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
            text = "🔍 البحث الحالي يعتمد على النص الإنجليزي.\nاكتب كلمة مثل: <code>mercy</code>, <code>prayer</code>, <code>intention</code>."
        elif lang == "de":
            text = "🔍 Die Suche verwendet derzeit englische Begriffe.\nZum Beispiel: <code>mercy</code>, <code>prayer</code>, <code>intention</code>."
        else:
            text = "🔍 Type a keyword:\n<code>mercy</code>, <code>prayer</code>, <code>intention</code>."

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
            msg = "❌ لا يوجد حديث لحفظه الآن." if lang == "ar" else "❌ Es gibt aktuell keinen Hadith zum Speichern." if lang == "de" else "❌ There is no hadith to save right now."
            await safe_edit(query, msg, InlineKeyboardMarkup(back_btn(lang)))
            return

        save_hadith(user_id, lang, current_hadith)
        msg = "✅ <b>تم حفظ الحديث بنجاح.</b>" if lang == "ar" else "✅ <b>Hadith wurde gespeichert.</b>" if lang == "de" else "✅ <b>Hadith saved successfully.</b>"
        await query.message.reply_text(msg, parse_mode="HTML")

    elif data == "saved_hadiths":
        saved = get_saved_hadiths(user_id, limit=5)

        if not saved:
            text = "❤️ لا توجد أحاديث محفوظة بعد." if lang == "ar" else "❤️ Noch keine Hadithe gespeichert." if lang == "de" else "❤️ No saved hadiths yet."
        else:
            text = "❤️ <b>آخر الأحاديث المحفوظة:</b>\n\n" if lang == "ar" else "❤️ <b>Zuletzt gespeicherte Hadithe:</b>\n\n" if lang == "de" else "❤️ <b>Latest saved hadiths:</b>\n\n"
            for i, hadith in enumerate(saved, start=1):
                text += f"<b>#{i}</b>\n{hadith[:900]}\n\n━━━━━━━━━━━━━━\n\n"

        await safe_edit(query, text, InlineKeyboardMarkup(back_btn(lang)))

    elif data == "change_language":
        keyboard = [
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")]
        ]
        await safe_edit(query, "🌍 <b>اختر اللغة / Choose language / Sprache wählen:</b>", InlineKeyboardMarkup(keyboard))

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
        reply_markup=InlineKeyboardMarkup(hadith_action_buttons(lang)),
        parse_mode="HTML",
        disable_web_page_preview=True
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