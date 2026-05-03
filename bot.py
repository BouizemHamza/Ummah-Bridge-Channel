import os
import random
import sqlite3
import requests
import html
import datetime
import time

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

from adhkar_data import (
    ADHKAR_LANGUAGES,
    REPEAT_TRANSLATIONS,
    SOURCE_TRANSLATIONS,
    MORNING_ADHKAR,
    EVENING_ADHKAR,
)


# =====================================================
# ENV
# =====================================================

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@UMMAHBRIDGE")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

HADITH_POST_TIME = os.environ.get("HADITH_POST_TIME", "09:00")
QURAN_POST_TIME = os.environ.get("QURAN_POST_TIME", "15:00")
MIXED_POST_TIME = os.environ.get("MIXED_POST_TIME", "21:00")

MORNING_ADHKAR_TIME = os.environ.get("MORNING_ADHKAR_TIME", "06:00")
EVENING_ADHKAR_TIME = os.environ.get("EVENING_ADHKAR_TIME", "18:00")

QURAN_API = "https://api.alquran.cloud/v1"
HADEETH_API = "https://hadeethenc.com/api/v1/hadeeths/one/"
LIST_API = "https://hadeethenc.com/api/v1/hadeeths/list/"

DB = "bot.db"


# =====================================================
# Helpers
# =====================================================

def esc(text):
    return html.escape(str(text or ""))


def line():
    return "\n━━━━━━━━━━━━━━\n"


def now_timestamp():
    return int(time.time())


def is_admin(user_id):
    return user_id == ADMIN_ID


def format_time_from_timestamp(ts):
    if not ts:
        return "غير متوفر"
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def parse_schedule_time(value, fallback="09:00"):
    try:
        value = str(value or fallback).strip()
        hour_text, minute_text = value.split(":")
        hour = int(hour_text)
        minute = int(minute_text)

        if hour < 0 or hour > 23:
            raise ValueError("Invalid hour")

        if minute < 0 or minute > 59:
            raise ValueError("Invalid minute")

        return datetime.time(hour=hour, minute=minute, second=0)

    except Exception:
        fallback_hour, fallback_minute = fallback.split(":")
        return datetime.time(
            hour=int(fallback_hour),
            minute=int(fallback_minute),
            second=0
        )


# =====================================================
# Database
# =====================================================

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'ar',
        adhkar_lang TEXT DEFAULT 'ar',
        created_at INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS saved(
        user_id INTEGER,
        text TEXT,
        created_at INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS adhkar_reminders(
        user_id INTEGER PRIMARY KEY,
        chat_id INTEGER NOT NULL,
        morning INTEGER DEFAULT 0,
        evening INTEGER DEFAULT 0,
        created_at INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS channel_posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_type TEXT NOT NULL,
        item_id TEXT,
        posted_at INTEGER NOT NULL,
        hour INTEGER NOT NULL,
        source TEXT DEFAULT 'bot'
    )
    """)

    # migrations
    c.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in c.fetchall()]
    if "adhkar_lang" not in user_cols:
        c.execute("ALTER TABLE users ADD COLUMN adhkar_lang TEXT DEFAULT 'ar'")
    if "created_at" not in user_cols:
        c.execute("ALTER TABLE users ADD COLUMN created_at INTEGER DEFAULT 0")

    c.execute("PRAGMA table_info(saved)")
    saved_cols = [row[1] for row in c.fetchall()]
    if "created_at" not in saved_cols:
        c.execute("ALTER TABLE saved ADD COLUMN created_at INTEGER DEFAULT 0")

    c.execute("PRAGMA table_info(channel_posts)")
    post_cols = [row[1] for row in c.fetchall()]
    if "item_id" not in post_cols:
        c.execute("ALTER TABLE channel_posts ADD COLUMN item_id TEXT")
    if "source" not in post_cols:
        c.execute("ALTER TABLE channel_posts ADD COLUMN source TEXT DEFAULT 'bot'")
    if "hour" not in post_cols:
        c.execute("ALTER TABLE channel_posts ADD COLUMN hour INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


def add_user(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "INSERT OR IGNORE INTO users(user_id, created_at, adhkar_lang) VALUES(?, ?, 'ar')",
        (user_id, now_timestamp())
    )

    conn.commit()
    conn.close()


def users_count():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]

    conn.close()
    return count


def get_adhkar_lang(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT adhkar_lang FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()

    conn.close()

    if not row or not row[0]:
        return "ar"

    if row[0] not in ADHKAR_LANGUAGES:
        return "ar"

    return row[0]


def set_adhkar_lang(user_id, lang):
    if lang not in ADHKAR_LANGUAGES:
        lang = "ar"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("UPDATE users SET adhkar_lang=? WHERE user_id=?", (lang, user_id))

    conn.commit()
    conn.close()


def save_hadith(user_id, text):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "INSERT INTO saved(user_id, text, created_at) VALUES (?, ?, ?)",
        (user_id, text, now_timestamp())
    )

    conn.commit()
    conn.close()


def saved_count():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM saved")
    count = c.fetchone()[0]

    conn.close()
    return count


def get_saved_hadiths(user_id, limit=5):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "SELECT text, created_at FROM saved WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )

    rows = c.fetchall()
    conn.close()
    return rows


def set_adhkar_reminder(user_id, chat_id, kind, enabled):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        INSERT OR IGNORE INTO adhkar_reminders(user_id, chat_id, morning, evening, created_at)
        VALUES (?, ?, 0, 0, ?)
    """, (user_id, chat_id, now_timestamp()))

    if kind == "morning":
        c.execute(
            "UPDATE adhkar_reminders SET morning=?, chat_id=? WHERE user_id=?",
            (1 if enabled else 0, chat_id, user_id)
        )

    elif kind == "evening":
        c.execute(
            "UPDATE adhkar_reminders SET evening=?, chat_id=? WHERE user_id=?",
            (1 if enabled else 0, chat_id, user_id)
        )

    conn.commit()
    conn.close()


def get_adhkar_reminder_status(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT morning, evening FROM adhkar_reminders WHERE user_id=?", (user_id,))
    row = c.fetchone()

    conn.close()

    if not row:
        return 0, 0

    return row[0], row[1]


def get_adhkar_subscribers(kind):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if kind == "morning":
        c.execute("SELECT user_id, chat_id FROM adhkar_reminders WHERE morning=1")
    else:
        c.execute("SELECT user_id, chat_id FROM adhkar_reminders WHERE evening=1")

    rows = c.fetchall()
    conn.close()
    return rows


def log_channel_post(post_type="hadith", item_id=None, source="bot"):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    ts = now_timestamp()
    hour = datetime.datetime.now().hour

    c.execute(
        """
        INSERT INTO channel_posts(post_type, item_id, posted_at, hour, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        (post_type, str(item_id or ""), ts, hour, source)
    )

    conn.commit()
    conn.close()


def channel_posts_count():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM channel_posts")
    count = c.fetchone()[0]

    conn.close()
    return count


def channel_posts_count_by_type(post_type):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM channel_posts WHERE post_type=?", (post_type,))
    count = c.fetchone()[0]

    conn.close()
    return count


# =====================================================
# Quran / Hadith APIs
# =====================================================

def get_random_hadith_id():
    response = requests.get(
        LIST_API,
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


def get_hadith_by_id(hadith_id, lang):
    response = requests.get(
        HADEETH_API,
        params={
            "language": lang,
            "id": hadith_id
        },
        timeout=15
    )
    response.raise_for_status()

    data = response.json()

    return {
        "text": data.get("hadeeth", "") or data.get("title", ""),
        "attribution": data.get("attribution", "HadeethEnc"),
        "grade": data.get("grade", ""),
    }


def random_hadith(lang="ar"):
    try:
        hid = get_random_hadith_id()

        if not hid:
            return "❌ لم يتم العثور على حديث."

        h = get_hadith_by_id(hid, lang)

        return f"""🕊️ <b>حديث نبوي</b>{line()}
{esc(h["text"])}
{line()}
📚 <b>المصدر:</b> {esc(h["attribution"])}
✅ <b>الدرجة:</b> {esc(h["grade"])}
🔢 <b>ID:</b> <code>{esc(hid)}</code>
"""

    except Exception as e:
        return f"❌ خطأ في جلب الحديث:\n<code>{esc(e)}</code>"


def hadith_channel_message():
    try:
        hid = get_random_hadith_id()

        if not hid:
            return "❌ تعذر جلب حديث اليوم.", None

        ar = get_hadith_by_id(hid, "ar")
        en = get_hadith_by_id(hid, "en")
        de = get_hadith_by_id(hid, "de")

        text = f"""📩 <b>حديث اليوم | Hadith of the Day | Hadith des Tages</b>

🕊️ <b>نفس الحديث بثلاث لغات</b>
<i>Same Hadith in Three Languages</i>

━━━━━━━━━━━━━━

🇸🇦 <b>العربية</b>

{esc(ar["text"])}

━━━━━━━━━━━━━━

🇬🇧 <b>English</b>

{esc(en["text"])}

━━━━━━━━━━━━━━

🇩🇪 <b>Deutsch</b>

{esc(de["text"])}

━━━━━━━━━━━━━━

📚 <b>المصدر:</b> {esc(ar["attribution"])}
✅ <b>الدرجة:</b> {esc(ar["grade"])}
🔢 <b>HadeethEnc ID:</b> <code>{esc(hid)}</code>

🌍 {esc(CHANNEL_ID)}
"""

        return text, hid

    except Exception as e:
        return f"❌ خطأ في بناء رسالة الحديث:\n<code>{esc(e)}</code>", None


def get_ayah_by_number(number, edition):
    response = requests.get(
        f"{QURAN_API}/ayah/{number}/{edition}",
        timeout=15
    )
    response.raise_for_status()

    data = response.json()["data"]

    return {
        "text": data.get("text", ""),
        "surah_name": data.get("surah", {}).get("name", ""),
        "surah_english": data.get("surah", {}).get("englishName", ""),
        "surah_number": data.get("surah", {}).get("number", ""),
        "ayah_number": data.get("numberInSurah", ""),
    }


def quran_channel_message():
    try:
        number = random.randint(1, 6236)

        ar = get_ayah_by_number(number, "quran-uthmani")
        en = get_ayah_by_number(number, "en.sahih")
        de = get_ayah_by_number(number, "de.aburida")

        ayah_ref = f"{ar['surah_number']}:{ar['ayah_number']}"

        text = f"""📖 <b>آية اليوم | Ayah of the Day | Vers des Tages</b>

━━━━━━━━━━━━━━

🇸🇦 <b>العربية</b>

{esc(ar["text"])}

━━━━━━━━━━━━━━

🇬🇧 <b>English</b>

{esc(en["text"])}

━━━━━━━━━━━━━━

🇩🇪 <b>Deutsch</b>

{esc(de["text"])}

━━━━━━━━━━━━━━

📖 <b>السورة:</b> {esc(ar["surah_name"])} | {esc(en["surah_english"])}
🔢 <b>الآية:</b> <code>{esc(ayah_ref)}</code>

🌍 {esc(CHANNEL_ID)}
"""

        return text, ayah_ref

    except Exception as e:
        return f"❌ خطأ في بناء رسالة الآية:\n<code>{esc(e)}</code>", None


def mixed_channel_message():
    quran_text, ayah_ref = quran_channel_message()
    hadith_text, hid = hadith_channel_message()

    return f"""📩 <b>رسالة إيمانية | Faith Reminder</b>

{quran_text}

━━━━━━━━━━━━━━

{hadith_text}
""", f"ayah:{ayah_ref}|hadith:{hid}"


# =====================================================
# UI Menus
# =====================================================

def language_display(lang):
    item = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])
    return f"{item['flag']} {item['name']}"


def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton("📖 القرآن", callback_data="quran")],
        [InlineKeyboardButton("🕊️ الأحاديث", callback_data="hadith")],
        [InlineKeyboardButton("🤲 الأذكار", callback_data="adhkar_menu")],
        [InlineKeyboardButton("ℹ️ عن المشروع", callback_data="about")],
        [InlineKeyboardButton("🌐 القناة الرسمية", url="https://t.me/UMMAHBRIDGE")]
    ]

    if is_admin(user_id):
        buttons.append([InlineKeyboardButton("🛠️ لوحة الإدارة", callback_data="admin")])

    return InlineKeyboardMarkup(buttons)


def hadith_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 حديث عشوائي", callback_data="random")],
        [InlineKeyboardButton("❤️ حفظ الحديث", callback_data="save")],
        [InlineKeyboardButton("📚 محفوظاتي", callback_data="saved")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def adhkar_main_menu(user_id):
    lang = get_adhkar_lang(user_id)

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌅 أذكار الصباح", callback_data="adhkar_morning_0")],
        [InlineKeyboardButton("🌙 أذكار المساء", callback_data="adhkar_evening_0")],
        [InlineKeyboardButton(f"🌍 لغة الأذكار: {language_display(lang)}", callback_data="adhkar_lang_menu")],
        [InlineKeyboardButton("⏰ تذكير الأذكار", callback_data="adhkar_reminders")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def adhkar_lang_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇸🇦 العربية", callback_data="adhkar_lang_ar"),
            InlineKeyboardButton("🇬🇧 English", callback_data="adhkar_lang_en"),
        ],
        [
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data="adhkar_lang_de"),
            InlineKeyboardButton("🇫🇷 Français", callback_data="adhkar_lang_fr"),
        ],
        [
            InlineKeyboardButton("🇪🇸 Español", callback_data="adhkar_lang_es"),
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="adhkar_lang_tr"),
        ],
        [
            InlineKeyboardButton("🇮🇩 Indonesia", callback_data="adhkar_lang_id"),
            InlineKeyboardButton("🇺🇷 اردو", callback_data="adhkar_lang_ur"),
        ],
        [
            InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="adhkar_lang_hi"),
        ],
        [InlineKeyboardButton("⬅️ رجوع للأذكار", callback_data="adhkar_menu")]
    ])


def adhkar_reminder_menu(user_id):
    morning, evening = get_adhkar_reminder_status(user_id)

    morning_status = "✅ مفعل" if morning else "❌ غير مفعل"
    evening_status = "✅ مفعل" if evening else "❌ غير مفعل"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🌅 تذكير الصباح: {morning_status}", callback_data="adhkar_toggle_morning")],
        [InlineKeyboardButton(f"🌙 تذكير المساء: {evening_status}", callback_data="adhkar_toggle_evening")],
        [InlineKeyboardButton("⬅️ رجوع للأذكار", callback_data="adhkar_menu")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def adhkar_navigation(kind, index, total):
    buttons = []
    row = []

    if index > 0:
        row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"adhkar_{kind}_{index - 1}"))

    if index < total - 1:
        row.append(InlineKeyboardButton("التالي ➡️", callback_data=f"adhkar_{kind}_{index + 1}"))

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("✅ أنهيت الأذكار", callback_data=f"adhkar_done_{kind}")])
    buttons.append([InlineKeyboardButton("⬅️ رجوع للأذكار", callback_data="adhkar_menu")])
    buttons.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")])

    return InlineKeyboardMarkup(buttons)


def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕊️ نشر حديث الآن", callback_data="admin_post_hadith")],
        [InlineKeyboardButton("📖 نشر آية الآن", callback_data="admin_post_quran")],
        [InlineKeyboardButton("📩 نشر آية + حديث", callback_data="admin_post_mixed")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("✍️ إرسال رسالة مخصصة للقناة", callback_data="admin_custom_post")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def admin_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ رجوع للوحة الإدارة", callback_data="admin")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


# =====================================================
# Adhkar Render
# =====================================================

def get_localized_value(item, field, lang):
    data = item.get(field, {})

    if lang in data:
        return data[lang]

    arabic_value = data.get("ar", "")

    if field == "repeat":
        translations = REPEAT_TRANSLATIONS.get(arabic_value)
        if translations:
            return translations.get(lang, translations.get("en", arabic_value))

    if field == "source":
        translations = SOURCE_TRANSLATIONS.get(arabic_value)
        if translations:
            return translations.get(lang, translations.get("en", arabic_value))

    if "en" in data and lang != "ar":
        return data["en"]

    return arabic_value


def get_meaning(item, lang):
    if lang == "ar":
        return ""

    meanings = item.get("meanings", {})

    if lang in meanings:
        return meanings[lang]

    return ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["en"])["missing"]


def render_adhkar(kind, index, lang):
    lang_pack = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])
    adhkar_list = MORNING_ADHKAR if kind == "morning" else EVENING_ADHKAR

    total = len(adhkar_list)

    if index < 0:
        index = 0

    if index >= total:
        index = total - 1

    item = adhkar_list[index]
    title = lang_pack["morning_title"] if kind == "morning" else lang_pack["evening_title"]

    repeat_text = get_localized_value(item, "repeat", lang)
    source_text = get_localized_value(item, "source", lang)
    meaning_text = get_meaning(item, lang)
    translation_note = lang_pack.get("translation_note", "")

    if lang == "ar":
        text = f"""{title}

<b>{esc(lang_pack["dhikr_word"])} {index + 1}/{total}</b>
{line()}
{esc(item["ar"])}
{line()}
🔁 <b>{esc(lang_pack["label_repeat"])}:</b> {esc(repeat_text)}
📚 <b>{esc(lang_pack["label_source"])}:</b> {esc(source_text)}
"""
    else:
        text = f"""{title}

<b>{esc(lang_pack["dhikr_word"])} {index + 1}/{total}</b>
{line()}
<b>{esc(lang_pack["label_arabic_text"])}:</b>

{esc(item["ar"])}

{line()}
<b>{esc(lang_pack["label_meaning"])}:</b>

{esc(meaning_text)}

{line()}
🔁 <b>{esc(lang_pack["label_repeat"])}:</b> {esc(repeat_text)}
📚 <b>{esc(lang_pack["label_source"])}:</b> {esc(source_text)}
"""

        if translation_note:
            text += f"\n\nℹ️ <i>{esc(translation_note)}</i>"

    return text, adhkar_navigation(kind, index, total)


# =====================================================
# Send Helpers
# =====================================================

async def safe_edit(q, text, markup=None):
    try:
        await q.edit_message_text(
            text=text,
            reply_markup=markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except BadRequest:
        await q.message.reply_text(
            text=text,
            reply_markup=markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )


async def send_channel_message(context, text, post_type, item_id, source):
    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    log_channel_post(post_type, item_id, source)


# =====================================================
# Commands
# =====================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)

    await update.message.reply_text(
        "🌉 <b>مرحبًا بك في Ummah Bridge</b>\n\nاختر من القائمة:",
        reply_markup=main_menu(user_id),
        parse_mode="HTML"
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)

    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر خاص بالمشرف فقط.")
        return

    await update.message.reply_text(
        "🛠️ <b>لوحة الإدارة</b>\n\nاختر إجراء:",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


async def test_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر خاص بالمشرف فقط.")
        return

    text, hid = hadith_channel_message()

    await send_channel_message(
        context=context,
        text=text,
        post_type="hadith",
        item_id=hid,
        source="test_command"
    )

    await update.message.reply_text("✅ تم نشر رسالة اختبار في القناة.")


# =====================================================
# Automatic Channel Posts
# =====================================================

async def auto_publish_hadith(context: ContextTypes.DEFAULT_TYPE):
    try:
        text, hid = hadith_channel_message()

        await send_channel_message(
            context=context,
            text=text,
            post_type="hadith",
            item_id=hid,
            source="auto_hadith"
        )

        print("✅ Auto hadith sent.")

    except Exception as e:
        print(f"❌ Auto hadith error: {e}")


async def auto_publish_quran(context: ContextTypes.DEFAULT_TYPE):
    try:
        text, ayah_ref = quran_channel_message()

        await send_channel_message(
            context=context,
            text=text,
            post_type="quran",
            item_id=ayah_ref,
            source="auto_quran"
        )

        print("✅ Auto quran sent.")

    except Exception as e:
        print(f"❌ Auto quran error: {e}")


async def auto_publish_mixed(context: ContextTypes.DEFAULT_TYPE):
    try:
        text, item_id = mixed_channel_message()

        await send_channel_message(
            context=context,
            text=text,
            post_type="mixed",
            item_id=item_id,
            source="auto_mixed"
        )

        print("✅ Auto mixed sent.")

    except Exception as e:
        print(f"❌ Auto mixed error: {e}")


# =====================================================
# Adhkar Reminders
# =====================================================

async def send_morning_adhkar_reminders(context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_adhkar_subscribers("morning")

    for user_id, chat_id in subscribers:
        lang = get_adhkar_lang(user_id)
        lang_pack = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=lang_pack["reminder_morning"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        lang_pack["start_morning_button"],
                        callback_data="adhkar_morning_0"
                    )]
                ]),
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Morning adhkar reminder error for {user_id}: {e}")


async def send_evening_adhkar_reminders(context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_adhkar_subscribers("evening")

    for user_id, chat_id in subscribers:
        lang = get_adhkar_lang(user_id)
        lang_pack = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=lang_pack["reminder_evening"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        lang_pack["start_evening_button"],
                        callback_data="adhkar_evening_0"
                    )]
                ]),
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Evening adhkar reminder error for {user_id}: {e}")


# =====================================================
# Callback Handler
# =====================================================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    chat_id = q.message.chat_id
    add_user(user_id)

    data = q.data

    if data == "home":
        await safe_edit(
            q,
            "🌉 <b>Ummah Bridge</b>\n\nاختر من القائمة:",
            main_menu(user_id)
        )

    elif data == "quran":
        try:
            res = requests.get(
                f"{QURAN_API}/surah/1/quran-uthmani",
                timeout=15
            )
            res.raise_for_status()

            ayat = res.json()["data"]["ayahs"]

            text = "📖 <b>سورة الفاتحة</b>" + line()

            for a in ayat:
                text += f"{esc(a['text'])}\n"

            await safe_edit(q, text, back())

        except Exception as e:
            await safe_edit(
                q,
                f"❌ خطأ في جلب القرآن:\n<code>{esc(e)}</code>",
                back()
            )

    elif data == "hadith":
        await safe_edit(
            q,
            "🕊️ <b>قسم الأحاديث</b>",
            hadith_menu()
        )

    elif data == "random":
        h = random_hadith("ar")
        context.user_data["last"] = h

        await safe_edit(q, h, hadith_menu())

    elif data == "save":
        h = context.user_data.get("last")

        if not h:
            await q.answer("لا يوجد حديث لحفظه", show_alert=True)
            return

        save_hadith(user_id, h)
        await q.answer("تم الحفظ ✅", show_alert=True)

    elif data == "saved":
        rows = get_saved_hadiths(user_id)

        if not rows:
            text = "❤️ لا توجد محفوظات بعد."
        else:
            text = "❤️ <b>محفوظاتك:</b>\n\n"

            for i, row in enumerate(rows, 1):
                text += (
                    f"<b>#{i}</b>\n"
                    f"🕒 {esc(format_time_from_timestamp(row[1]))}\n"
                    f"{esc(row[0][:500])}\n\n"
                    f"━━━━━━━━━━━━━━\n\n"
                )

        await safe_edit(q, text, back())

    elif data == "adhkar_menu":
        lang = get_adhkar_lang(user_id)

        await safe_edit(
            q,
            f"🤲 <b>قسم الأذكار</b>\n\n"
            f"🌍 اللغة الحالية: <b>{esc(language_display(lang))}</b>\n\n"
            f"اختر ما تريد قراءته:",
            adhkar_main_menu(user_id)
        )

    elif data == "adhkar_lang_menu":
        await safe_edit(
            q,
            "🌍 <b>اختر لغة الأذكار:</b>",
            adhkar_lang_menu()
        )

    elif data.startswith("adhkar_lang_"):
        lang = data.split("_")[-1]
        set_adhkar_lang(user_id, lang)

        await safe_edit(
            q,
            f"✅ تم تغيير لغة الأذكار إلى: <b>{esc(language_display(lang))}</b>",
            adhkar_main_menu(user_id)
        )

    elif data.startswith("adhkar_morning_"):
        index = int(data.split("_")[-1])
        lang = get_adhkar_lang(user_id)

        text, markup = render_adhkar("morning", index, lang)

        await safe_edit(q, text, markup)

    elif data.startswith("adhkar_evening_"):
        index = int(data.split("_")[-1])
        lang = get_adhkar_lang(user_id)

        text, markup = render_adhkar("evening", index, lang)

        await safe_edit(q, text, markup)

    elif data == "adhkar_done_morning":
        lang = get_adhkar_lang(user_id)
        lang_pack = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])

        await safe_edit(
            q,
            lang_pack["done_morning"],
            adhkar_main_menu(user_id)
        )

    elif data == "adhkar_done_evening":
        lang = get_adhkar_lang(user_id)
        lang_pack = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])

        await safe_edit(
            q,
            lang_pack["done_evening"],
            adhkar_main_menu(user_id)
        )

    elif data == "adhkar_reminders":
        morning, evening = get_adhkar_reminder_status(user_id)

        text = f"""⏰ <b>تذكير الأذكار</b>

🌅 تذكير الصباح: {"✅ مفعل" if morning else "❌ غير مفعل"}
🌙 تذكير المساء: {"✅ مفعل" if evening else "❌ غير مفعل"}

🕘 وقت الصباح الحالي: <code>{esc(MORNING_ADHKAR_TIME)}</code>
🕕 وقت المساء الحالي: <code>{esc(EVENING_ADHKAR_TIME)}</code>
"""

        await safe_edit(
            q,
            text,
            adhkar_reminder_menu(user_id)
        )

    elif data == "adhkar_toggle_morning":
        morning, evening = get_adhkar_reminder_status(user_id)
        new_value = 0 if morning else 1

        set_adhkar_reminder(
            user_id=user_id,
            chat_id=chat_id,
            kind="morning",
            enabled=new_value
        )

        await q.answer("تم تحديث تذكير الصباح ✅", show_alert=True)

        await safe_edit(
            q,
            "⏰ <b>تم تحديث إعدادات التذكير.</b>",
            adhkar_reminder_menu(user_id)
        )

    elif data == "adhkar_toggle_evening":
        morning, evening = get_adhkar_reminder_status(user_id)
        new_value = 0 if evening else 1

        set_adhkar_reminder(
            user_id=user_id,
            chat_id=chat_id,
            kind="evening",
            enabled=new_value
        )

        await q.answer("تم تحديث تذكير المساء ✅", show_alert=True)

        await safe_edit(
            q,
            "⏰ <b>تم تحديث إعدادات التذكير.</b>",
            adhkar_reminder_menu(user_id)
        )

    elif data == "about":
        await safe_edit(
            q,
            f"""ℹ️ <b>Ummah Bridge</b>

مشروع دعوي للتعريف بالإسلام عبر الإنترنت.

📖 المصدر:
القرآن الكريم والسنة النبوية.

🚫 لا نقدّم فتاوى.
🚫 لا نقدّم آراء شخصية.
✅ ننشر نصوصًا موثقة ومترجمة.

🤲 يحتوي البوت على أذكار الصباح والمساء بلغات متعددة.

🌍 القناة:
{esc(CHANNEL_ID)}
""",
            back()
        )

    elif data == "admin":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        await safe_edit(
            q,
            "🛠️ <b>لوحة الإدارة</b>\n\nاختر إجراء:",
            admin_menu()
        )

    elif data == "admin_post_hadith":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        text, hid = hadith_channel_message()

        await send_channel_message(
            context=context,
            text=text,
            post_type="hadith",
            item_id=hid,
            source="admin_manual_hadith"
        )

        await safe_edit(
            q,
            "✅ <b>تم نشر حديث في القناة.</b>",
            admin_menu()
        )

    elif data == "admin_post_quran":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        text, ayah_ref = quran_channel_message()

        await send_channel_message(
            context=context,
            text=text,
            post_type="quran",
            item_id=ayah_ref,
            source="admin_manual_quran"
        )

        await safe_edit(
            q,
            "✅ <b>تم نشر آية في القناة.</b>",
            admin_menu()
        )

    elif data == "admin_post_mixed":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        text, item_id = mixed_channel_message()

        await send_channel_message(
            context=context,
            text=text,
            post_type="mixed",
            item_id=item_id,
            source="admin_manual_mixed"
        )

        await safe_edit(
            q,
            "✅ <b>تم نشر آية + حديث في القناة.</b>",
            admin_menu()
        )

    elif data == "admin_stats":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        morning_count = len(get_adhkar_subscribers("morning"))
        evening_count = len(get_adhkar_subscribers("evening"))

        await safe_edit(
            q,
            f"""📊 <b>لوحة إحصائيات Ummah Bridge</b>

👥 <b>عدد المستخدمين:</b> {users_count()}
❤️ <b>عدد الأحاديث المحفوظة:</b> {saved_count()}

📢 <b>إجمالي منشورات القناة:</b> {channel_posts_count()}
🕊️ <b>منشورات الحديث:</b> {channel_posts_count_by_type("hadith")}
📖 <b>منشورات القرآن:</b> {channel_posts_count_by_type("quran")}
📩 <b>منشورات آية + حديث:</b> {channel_posts_count_by_type("mixed")}

🤲 <b>مشتركو تذكير الصباح:</b> {morning_count}
🤲 <b>مشتركو تذكير المساء:</b> {evening_count}

🌍 <b>لغات الأذكار:</b>
العربية، الإنجليزية، الألمانية، الفرنسية، الإسبانية، التركية، الإندونيسية، الأردية، الهندية.

⏰ <b>أوقات الأذكار:</b>
• صباح: <code>{esc(MORNING_ADHKAR_TIME)}</code>
• مساء: <code>{esc(EVENING_ADHKAR_TIME)}</code>

🌐 <b>القناة:</b> {esc(CHANNEL_ID)}
""",
            admin_menu()
        )

    elif data == "admin_custom_post":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        context.user_data["waiting_custom_post"] = True

        await safe_edit(
            q,
            "✍️ <b>أرسل الآن الرسالة التي تريد نشرها في القناة.</b>",
            admin_back()
        )


# =====================================================
# Text Handler
# =====================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)

    if context.user_data.get("waiting_custom_post"):
        if not is_admin(user_id):
            return

        context.user_data["waiting_custom_post"] = False
        text = update.message.text

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=esc(text),
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        log_channel_post(
            post_type="custom",
            item_id="",
            source="admin_custom"
        )

        await update.message.reply_text(
            "✅ تم نشر الرسالة المخصصة في القناة.",
            reply_markup=admin_menu()
        )


# =====================================================
# Main
# =====================================================

def main():
    if not TOKEN:
        print("❌ BOT_TOKEN missing")
        return

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("test_channel", test_channel))
    app.add_handler(CallbackQueryHandler(handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.job_queue.run_daily(
        auto_publish_hadith,
        time=parse_schedule_time(HADITH_POST_TIME, "09:00")
    )

    app.job_queue.run_daily(
        auto_publish_quran,
        time=parse_schedule_time(QURAN_POST_TIME, "15:00")
    )

    app.job_queue.run_daily(
        auto_publish_mixed,
        time=parse_schedule_time(MIXED_POST_TIME, "21:00")
    )

    app.job_queue.run_daily(
        send_morning_adhkar_reminders,
        time=parse_schedule_time(MORNING_ADHKAR_TIME, "06:00")
    )

    app.job_queue.run_daily(
        send_evening_adhkar_reminders,
        time=parse_schedule_time(EVENING_ADHKAR_TIME, "18:00")
    )

    print("Bot running with external adhkar_data.py...")
    print(f"Hadith post time: {HADITH_POST_TIME}")
    print(f"Quran post time: {QURAN_POST_TIME}")
    print(f"Mixed post time: {MIXED_POST_TIME}")
    print(f"Morning adhkar reminder: {MORNING_ADHKAR_TIME}")
    print(f"Evening adhkar reminder: {EVENING_ADHKAR_TIME}")

    app.run_polling()


if __name__ == "__main__":
    main()