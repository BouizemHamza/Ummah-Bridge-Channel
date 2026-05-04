import os
import random
import sqlite3
import requests
import html
import datetime
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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

DEFAULT_USER_TIMEZONE = os.environ.get("DEFAULT_USER_TIMEZONE", "Europe/Berlin")

DEFAULT_MORNING_ADHKAR_TIME = os.environ.get(
    "DEFAULT_MORNING_ADHKAR_TIME",
    os.environ.get("MORNING_ADHKAR_TIME", "06:00")
)

DEFAULT_EVENING_ADHKAR_TIME = os.environ.get(
    "DEFAULT_EVENING_ADHKAR_TIME",
    os.environ.get("EVENING_ADHKAR_TIME", "18:00")
)

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


def is_valid_hhmm(value):
    try:
        value = str(value).strip()
        h, m = value.split(":")
        h = int(h)
        m = int(m)
        return 0 <= h <= 23 and 0 <= m <= 59
    except Exception:
        return False


def is_valid_timezone(tz_name):
    try:
        ZoneInfo(str(tz_name).strip())
        return True
    except Exception:
        return False


def safe_timezone(tz_name):
    if is_valid_timezone(tz_name):
        return str(tz_name).strip()
    return DEFAULT_USER_TIMEZONE if is_valid_timezone(DEFAULT_USER_TIMEZONE) else "UTC"


def user_now(tz_name):
    tz = ZoneInfo(safe_timezone(tz_name))
    return datetime.datetime.now(tz)


def user_today_key(tz_name):
    return user_now(tz_name).strftime("%Y-%m-%d")


def user_current_hhmm(tz_name):
    return user_now(tz_name).strftime("%H:%M")


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
        morning_time TEXT DEFAULT '06:00',
        evening_time TEXT DEFAULT '18:00',
        timezone TEXT DEFAULT 'Europe/Berlin',
        last_morning_sent TEXT DEFAULT '',
        last_evening_sent TEXT DEFAULT '',
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

    c.execute("PRAGMA table_info(adhkar_reminders)")
    reminder_cols = [row[1] for row in c.fetchall()]

    if "morning_time" not in reminder_cols:
        c.execute(f"ALTER TABLE adhkar_reminders ADD COLUMN morning_time TEXT DEFAULT '{DEFAULT_MORNING_ADHKAR_TIME}'")
    if "evening_time" not in reminder_cols:
        c.execute(f"ALTER TABLE adhkar_reminders ADD COLUMN evening_time TEXT DEFAULT '{DEFAULT_EVENING_ADHKAR_TIME}'")
    if "timezone" not in reminder_cols:
        c.execute(f"ALTER TABLE adhkar_reminders ADD COLUMN timezone TEXT DEFAULT '{safe_timezone(DEFAULT_USER_TIMEZONE)}'")
    if "last_morning_sent" not in reminder_cols:
        c.execute("ALTER TABLE adhkar_reminders ADD COLUMN last_morning_sent TEXT DEFAULT ''")
    if "last_evening_sent" not in reminder_cols:
        c.execute("ALTER TABLE adhkar_reminders ADD COLUMN last_evening_sent TEXT DEFAULT ''")

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


def ensure_adhkar_reminder_row(user_id, chat_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        INSERT OR IGNORE INTO adhkar_reminders(
            user_id,
            chat_id,
            morning,
            evening,
            morning_time,
            evening_time,
            timezone,
            last_morning_sent,
            last_evening_sent,
            created_at
        )
        VALUES (?, ?, 0, 0, ?, ?, ?, '', '', ?)
    """, (
        user_id,
        chat_id,
        DEFAULT_MORNING_ADHKAR_TIME,
        DEFAULT_EVENING_ADHKAR_TIME,
        safe_timezone(DEFAULT_USER_TIMEZONE),
        now_timestamp()
    ))

    c.execute(
        "UPDATE adhkar_reminders SET chat_id=? WHERE user_id=?",
        (chat_id, user_id)
    )

    conn.commit()
    conn.close()


def set_adhkar_reminder(user_id, chat_id, kind, enabled):
    ensure_adhkar_reminder_row(user_id, chat_id)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

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


def set_adhkar_reminder_time(user_id, chat_id, kind, hhmm):
    if not is_valid_hhmm(hhmm):
        return False

    ensure_adhkar_reminder_row(user_id, chat_id)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if kind == "morning":
        c.execute(
            "UPDATE adhkar_reminders SET morning_time=?, chat_id=? WHERE user_id=?",
            (hhmm, chat_id, user_id)
        )
    elif kind == "evening":
        c.execute(
            "UPDATE adhkar_reminders SET evening_time=?, chat_id=? WHERE user_id=?",
            (hhmm, chat_id, user_id)
        )
    else:
        conn.close()
        return False

    conn.commit()
    conn.close()
    return True


def set_user_timezone(user_id, chat_id, timezone_name):
    timezone_name = str(timezone_name).strip()

    if not is_valid_timezone(timezone_name):
        return False

    ensure_adhkar_reminder_row(user_id, chat_id)

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "UPDATE adhkar_reminders SET timezone=?, chat_id=? WHERE user_id=?",
        (timezone_name, chat_id, user_id)
    )
    conn.commit()
    conn.close()
    return True


def get_adhkar_reminder_status(user_id, chat_id=None):
    if chat_id is not None:
        ensure_adhkar_reminder_row(user_id, chat_id)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT morning, evening, morning_time, evening_time, timezone, last_morning_sent, last_evening_sent
        FROM adhkar_reminders
        WHERE user_id=?
    """, (user_id,))

    row = c.fetchone()
    conn.close()

    if not row:
        return {
            "morning": 0,
            "evening": 0,
            "morning_time": DEFAULT_MORNING_ADHKAR_TIME,
            "evening_time": DEFAULT_EVENING_ADHKAR_TIME,
            "timezone": safe_timezone(DEFAULT_USER_TIMEZONE),
            "last_morning_sent": "",
            "last_evening_sent": "",
        }

    return {
        "morning": row[0],
        "evening": row[1],
        "morning_time": row[2] or DEFAULT_MORNING_ADHKAR_TIME,
        "evening_time": row[3] or DEFAULT_EVENING_ADHKAR_TIME,
        "timezone": safe_timezone(row[4] or DEFAULT_USER_TIMEZONE),
        "last_morning_sent": row[5] or "",
        "last_evening_sent": row[6] or "",
    }


def get_all_adhkar_reminder_rows():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT
            user_id,
            chat_id,
            morning,
            evening,
            morning_time,
            evening_time,
            timezone,
            last_morning_sent,
            last_evening_sent
        FROM adhkar_reminders
        WHERE morning=1 OR evening=1
    """)

    rows = c.fetchall()
    conn.close()
    return rows


def update_last_adhkar_sent(user_id, kind, date_text):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if kind == "morning":
        c.execute(
            "UPDATE adhkar_reminders SET last_morning_sent=? WHERE user_id=?",
            (date_text, user_id)
        )
    elif kind == "evening":
        c.execute(
            "UPDATE adhkar_reminders SET last_evening_sent=? WHERE user_id=?",
            (date_text, user_id)
        )

    conn.commit()
    conn.close()


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


def adhkar_reminder_menu(user_id, chat_id=None):
    status = get_adhkar_reminder_status(user_id, chat_id)

    morning_status = "✅ مفعل" if status["morning"] else "❌ غير مفعل"
    evening_status = "✅ مفعل" if status["evening"] else "❌ غير مفعل"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🌅 تذكير الصباح: {morning_status}", callback_data="adhkar_toggle_morning")],
        [InlineKeyboardButton(f"🌙 تذكير المساء: {evening_status}", callback_data="adhkar_toggle_evening")],
        [InlineKeyboardButton(f"🕘 وقت الصباح: {status['morning_time']}", callback_data="adhkar_time_morning")],
        [InlineKeyboardButton(f"🕕 وقت المساء: {status['evening_time']}", callback_data="adhkar_time_evening")],
        [InlineKeyboardButton(f"🌍 المنطقة الزمنية: {status['timezone']}", callback_data="adhkar_timezone_menu")],
        [InlineKeyboardButton("⬅️ رجوع للأذكار", callback_data="adhkar_menu")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def time_selection_menu(kind):
    if kind == "morning":
        times = ["04:00", "05:00", "06:00", "07:00", "08:00", "09:00", "10:00"]
    else:
        times = ["16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00"]

    rows = []
    row = []

    for t in times:
        row.append(InlineKeyboardButton(t, callback_data=f"adhkar_settime_{kind}_{t}"))
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton("✍️ أرسل وقتًا مخصصًا", callback_data=f"adhkar_customtime_{kind}")])
    rows.append([InlineKeyboardButton("⬅️ رجوع للتذكير", callback_data="adhkar_reminders")])
    rows.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")])

    return InlineKeyboardMarkup(rows)


def timezone_menu():
    zones = [
        ("🇩🇪 Berlin", "Europe/Berlin"),
        ("🇬🇧 London", "Europe/London"),
        ("🇫🇷 Paris", "Europe/Paris"),
        ("🇪🇸 Madrid", "Europe/Madrid"),
        ("🇹🇷 Istanbul", "Europe/Istanbul"),
        ("🇸🇦 Riyadh", "Asia/Riyadh"),
        ("🇦🇪 Dubai", "Asia/Dubai"),
        ("🇵🇰 Karachi", "Asia/Karachi"),
        ("🇮🇳 Kolkata", "Asia/Kolkata"),
        ("🇮🇩 Jakarta", "Asia/Jakarta"),
        ("🇲🇦 Casablanca", "Africa/Casablanca"),
        ("🇺🇸 New York", "America/New_York"),
        ("🇺🇸 Chicago", "America/Chicago"),
        ("🇺🇸 Los Angeles", "America/Los_Angeles"),
    ]

    rows = []
    row = []

    for label, zone in zones:
        row.append(InlineKeyboardButton(label, callback_data=f"adhkar_settz_{zone}"))
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton("✍️ إرسال منطقة زمنية مخصصة", callback_data="adhkar_custom_timezone")])
    rows.append([InlineKeyboardButton("⬅️ رجوع للتذكير", callback_data="adhkar_reminders")])
    rows.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")])

    return InlineKeyboardMarkup(rows)


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
# Adhkar Render + Repeat Counter
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


def get_repeat_total(item):
    repeat_ar = item.get("repeat", {}).get("ar", "")

    repeat_map = {
        "مرة واحدة": 1,
        "ثلاث مرات": 3,
        "أربع مرات": 4,
        "سبع مرات": 7,
        "عشر مرات": 10,
        "مائة مرة": 100,
        "عشر مرات أو مائة مرة": 10,
    }

    return repeat_map.get(repeat_ar, 1)


def adhkar_navigation(kind, index, total, repeat_total=1):
    buttons = []

    if repeat_total > 1:
        buttons.append([
            InlineKeyboardButton("🔁 عداد التكرار", callback_data=f"adhkar_counter_{kind}_{index}_0")
        ])

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
    repeat_total = get_repeat_total(item)

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

    return text, adhkar_navigation(kind, index, total, repeat_total)


def render_adhkar_counter(kind, index, lang, count):
    lang_pack = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])
    adhkar_list = MORNING_ADHKAR if kind == "morning" else EVENING_ADHKAR

    total_adhkar = len(adhkar_list)

    if index < 0:
        index = 0

    if index >= total_adhkar:
        index = total_adhkar - 1

    item = adhkar_list[index]
    repeat_total = get_repeat_total(item)

    if count < 0:
        count = 0

    if count > repeat_total:
        count = repeat_total

    title = lang_pack["morning_title"] if kind == "morning" else lang_pack["evening_title"]
    repeat_text = get_localized_value(item, "repeat", lang)
    source_text = get_localized_value(item, "source", lang)
    meaning_text = get_meaning(item, lang)
    translation_note = lang_pack.get("translation_note", "")

    progress_bar = "🟩" * count + "⬜" * (repeat_total - count)
    if repeat_total > 20:
        filled = int((count / repeat_total) * 10)
        progress_bar = "🟩" * filled + "⬜" * (10 - filled)

    if lang == "ar":
        text = f"""{title}

<b>{esc(lang_pack["dhikr_word"])} {index + 1}/{total_adhkar}</b>
{line()}
{esc(item["ar"])}
{line()}
🔁 <b>{esc(lang_pack["label_repeat"])}:</b> {esc(repeat_text)}
📚 <b>{esc(lang_pack["label_source"])}:</b> {esc(source_text)}

🔢 <b>عداد التكرار:</b> {count}/{repeat_total}
{progress_bar}
"""
    else:
        text = f"""{title}

<b>{esc(lang_pack["dhikr_word"])} {index + 1}/{total_adhkar}</b>
{line()}
<b>{esc(lang_pack["label_arabic_text"])}:</b>

{esc(item["ar"])}

{line()}
<b>{esc(lang_pack["label_meaning"])}:</b>

{esc(meaning_text)}

{line()}
🔁 <b>{esc(lang_pack["label_repeat"])}:</b> {esc(repeat_text)}
📚 <b>{esc(lang_pack["label_source"])}:</b> {esc(source_text)}

🔢 <b>Counter:</b> {count}/{repeat_total}
{progress_bar}
"""

        if translation_note:
            text += f"\n\nℹ️ <i>{esc(translation_note)}</i>"

    buttons = []

    if count < repeat_total:
        buttons.append([
            InlineKeyboardButton("✅ تم التكرار مرة", callback_data=f"adhkar_counter_{kind}_{index}_{count + 1}")
        ])

        if repeat_total >= 10:
            next_10 = min(count + 10, repeat_total)
            buttons.append([
                InlineKeyboardButton("➕ 10", callback_data=f"adhkar_counter_{kind}_{index}_{next_10}")
            ])

    else:
        buttons.append([
            InlineKeyboardButton("✅ اكتمل التكرار", callback_data=f"adhkar_{kind}_{index}")
        ])

        if index < total_adhkar - 1:
            buttons.append([
                InlineKeyboardButton("التالي ➡️", callback_data=f"adhkar_{kind}_{index + 1}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton("✅ أنهيت الأذكار", callback_data=f"adhkar_done_{kind}")
            ])

    buttons.append([
        InlineKeyboardButton("🔄 إعادة العداد", callback_data=f"adhkar_counter_{kind}_{index}_0")
    ])

    buttons.append([
        InlineKeyboardButton("⬅️ رجوع للذكر", callback_data=f"adhkar_{kind}_{index}")
    ])

    buttons.append([
        InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")
    ])

    return text, InlineKeyboardMarkup(buttons)


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
    chat_id = update.message.chat_id

    add_user(user_id)
    ensure_adhkar_reminder_row(user_id, chat_id)

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
        await send_channel_message(context, text, "hadith", hid, "auto_hadith")
        print("✅ Auto hadith sent.")
    except Exception as e:
        print(f"❌ Auto hadith error: {e}")


async def auto_publish_quran(context: ContextTypes.DEFAULT_TYPE):
    try:
        text, ayah_ref = quran_channel_message()
        await send_channel_message(context, text, "quran", ayah_ref, "auto_quran")
        print("✅ Auto quran sent.")
    except Exception as e:
        print(f"❌ Auto quran error: {e}")


async def auto_publish_mixed(context: ContextTypes.DEFAULT_TYPE):
    try:
        text, item_id = mixed_channel_message()
        await send_channel_message(context, text, "mixed", item_id, "auto_mixed")
        print("✅ Auto mixed sent.")
    except Exception as e:
        print(f"❌ Auto mixed error: {e}")


# =====================================================
# Personal Adhkar Reminders With Timezone
# =====================================================

async def send_adhkar_reminder_to_user(context, user_id, chat_id, kind):
    lang = get_adhkar_lang(user_id)
    lang_pack = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])

    if kind == "morning":
        text = lang_pack["reminder_morning"]
        button = lang_pack["start_morning_button"]
        callback = "adhkar_morning_0"
    else:
        text = lang_pack["reminder_evening"]
        button = lang_pack["start_evening_button"]
        callback = "adhkar_evening_0"

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(button, callback_data=callback)]
        ]),
        parse_mode="HTML"
    )


async def check_personal_adhkar_reminders(context: ContextTypes.DEFAULT_TYPE):
    rows = get_all_adhkar_reminder_rows()

    for row in rows:
        user_id = row[0]
        chat_id = row[1]
        morning_enabled = row[2]
        evening_enabled = row[3]
        morning_time = row[4] or DEFAULT_MORNING_ADHKAR_TIME
        evening_time = row[5] or DEFAULT_EVENING_ADHKAR_TIME
        tz_name = safe_timezone(row[6] or DEFAULT_USER_TIMEZONE)
        last_morning_sent = row[7] or ""
        last_evening_sent = row[8] or ""

        local_time = user_current_hhmm(tz_name)
        local_today = user_today_key(tz_name)

        if morning_enabled and morning_time == local_time and last_morning_sent != local_today:
            try:
                await send_adhkar_reminder_to_user(context, user_id, chat_id, "morning")
                update_last_adhkar_sent(user_id, "morning", local_today)
                print(f"✅ Morning reminder sent to {user_id} at {local_time} {tz_name}")
            except Exception as e:
                print(f"❌ Morning reminder error for {user_id}: {e}")

        if evening_enabled and evening_time == local_time and last_evening_sent != local_today:
            try:
                await send_adhkar_reminder_to_user(context, user_id, chat_id, "evening")
                update_last_adhkar_sent(user_id, "evening", local_today)
                print(f"✅ Evening reminder sent to {user_id} at {local_time} {tz_name}")
            except Exception as e:
                print(f"❌ Evening reminder error for {user_id}: {e}")


# =====================================================
# Callback Handler
# =====================================================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    chat_id = q.message.chat_id
    add_user(user_id)
    ensure_adhkar_reminder_row(user_id, chat_id)

    data = q.data

    if data == "home":
        await safe_edit(q, "🌉 <b>Ummah Bridge</b>\n\nاختر من القائمة:", main_menu(user_id))

    elif data == "quran":
        try:
            res = requests.get(f"{QURAN_API}/surah/1/quran-uthmani", timeout=15)
            res.raise_for_status()
            ayat = res.json()["data"]["ayahs"]

            text = "📖 <b>سورة الفاتحة</b>" + line()
            for a in ayat:
                text += f"{esc(a['text'])}\n"

            await safe_edit(q, text, back())
        except Exception as e:
            await safe_edit(q, f"❌ خطأ في جلب القرآن:\n<code>{esc(e)}</code>", back())

    elif data == "hadith":
        await safe_edit(q, "🕊️ <b>قسم الأحاديث</b>", hadith_menu())

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
        await safe_edit(q, "🌍 <b>اختر لغة الأذكار:</b>", adhkar_lang_menu())

    elif data.startswith("adhkar_lang_"):
        lang = data.split("_")[-1]
        set_adhkar_lang(user_id, lang)
        await safe_edit(
            q,
            f"✅ تم تغيير لغة الأذكار إلى: <b>{esc(language_display(lang))}</b>",
            adhkar_main_menu(user_id)
        )

    elif data.startswith("adhkar_counter_"):
        parts = data.split("_")
        kind = parts[2]
        index = int(parts[3])
        count = int(parts[4])
        lang = get_adhkar_lang(user_id)
        text, markup = render_adhkar_counter(kind, index, lang, count)
        await safe_edit(q, text, markup)

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
        await safe_edit(q, lang_pack["done_morning"], adhkar_main_menu(user_id))

    elif data == "adhkar_done_evening":
        lang = get_adhkar_lang(user_id)
        lang_pack = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])
        await safe_edit(q, lang_pack["done_evening"], adhkar_main_menu(user_id))

    elif data == "adhkar_reminders":
        status = get_adhkar_reminder_status(user_id, chat_id)
        local_now = user_now(status["timezone"]).strftime("%Y-%m-%d %H:%M")

        text = f"""⏰ <b>تذكير الأذكار الشخصي</b>

🌅 تذكير الصباح: {"✅ مفعل" if status["morning"] else "❌ غير مفعل"}
🕘 وقت الصباح: <code>{esc(status["morning_time"])}</code>

🌙 تذكير المساء: {"✅ مفعل" if status["evening"] else "❌ غير مفعل"}
🕕 وقت المساء: <code>{esc(status["evening_time"])}</code>

🌍 المنطقة الزمنية:
<code>{esc(status["timezone"])}</code>

🕒 الوقت الحالي حسب منطقتك:
<code>{esc(local_now)}</code>

✅ التذكير سيصل حسب منطقتك الزمنية، وليس حسب توقيت Railway.
"""

        await safe_edit(q, text, adhkar_reminder_menu(user_id, chat_id))

    elif data == "adhkar_toggle_morning":
        status = get_adhkar_reminder_status(user_id, chat_id)
        new_value = 0 if status["morning"] else 1
        set_adhkar_reminder(user_id, chat_id, "morning", new_value)
        await q.answer("تم تحديث تذكير الصباح ✅", show_alert=True)
        await safe_edit(q, "⏰ <b>تم تحديث إعدادات التذكير.</b>", adhkar_reminder_menu(user_id, chat_id))

    elif data == "adhkar_toggle_evening":
        status = get_adhkar_reminder_status(user_id, chat_id)
        new_value = 0 if status["evening"] else 1
        set_adhkar_reminder(user_id, chat_id, "evening", new_value)
        await q.answer("تم تحديث تذكير المساء ✅", show_alert=True)
        await safe_edit(q, "⏰ <b>تم تحديث إعدادات التذكير.</b>", adhkar_reminder_menu(user_id, chat_id))

    elif data == "adhkar_time_morning":
        await safe_edit(
            q,
            "🌅 <b>اختر وقت تذكير الصباح:</b>\n\nأو اختر إرسال وقت مخصص مثل <code>06:30</code>.",
            time_selection_menu("morning")
        )

    elif data == "adhkar_time_evening":
        await safe_edit(
            q,
            "🌙 <b>اختر وقت تذكير المساء:</b>\n\nأو اختر إرسال وقت مخصص مثل <code>19:30</code>.",
            time_selection_menu("evening")
        )

    elif data.startswith("adhkar_settime_"):
        parts = data.split("_")
        kind = parts[2]
        selected_time = parts[3]
        ok = set_adhkar_reminder_time(user_id, chat_id, kind, selected_time)

        if ok:
            await q.answer("تم حفظ الوقت ✅", show_alert=True)
            await safe_edit(
                q,
                f"✅ تم تغيير وقت التذكير إلى: <code>{esc(selected_time)}</code>",
                adhkar_reminder_menu(user_id, chat_id)
            )
        else:
            await q.answer("وقت غير صحيح", show_alert=True)

    elif data.startswith("adhkar_customtime_"):
        kind = data.split("_")[-1]
        context.user_data["waiting_adhkar_custom_time"] = kind
        example = "06:30" if kind == "morning" else "19:30"

        await safe_edit(
            q,
            f"✍️ أرسل الوقت الآن بهذه الصيغة:\n\n<code>{example}</code>\n\nمثال صحيح: <code>07:15</code>",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ رجوع للتذكير", callback_data="adhkar_reminders")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
            ])
        )

    elif data == "adhkar_timezone_menu":
        status = get_adhkar_reminder_status(user_id, chat_id)
        local_now = user_now(status["timezone"]).strftime("%Y-%m-%d %H:%M")

        await safe_edit(
            q,
            f"""🌍 <b>اختر منطقتك الزمنية</b>

المنطقة الحالية:
<code>{esc(status["timezone"])}</code>

الوقت الحالي حسبها:
<code>{esc(local_now)}</code>

اختر من القائمة أو أرسل منطقة زمنية مخصصة.
""",
            timezone_menu()
        )

    elif data.startswith("adhkar_settz_"):
        tz_name = data.replace("adhkar_settz_", "", 1)
        ok = set_user_timezone(user_id, chat_id, tz_name)

        if ok:
            await q.answer("تم حفظ المنطقة الزمنية ✅", show_alert=True)
            local_now = user_now(tz_name).strftime("%Y-%m-%d %H:%M")
            await safe_edit(
                q,
                f"""✅ تم تغيير المنطقة الزمنية إلى:
<code>{esc(tz_name)}</code>

🕒 الوقت الحالي حسبها:
<code>{esc(local_now)}</code>
""",
                adhkar_reminder_menu(user_id, chat_id)
            )
        else:
            await q.answer("منطقة زمنية غير صحيحة", show_alert=True)

    elif data == "adhkar_custom_timezone":
        context.user_data["waiting_adhkar_custom_timezone"] = True

        await safe_edit(
            q,
            """✍️ أرسل المنطقة الزمنية الآن بهذه الصيغة:

<code>Europe/Berlin</code>
<code>Asia/Riyadh</code>
<code>Africa/Casablanca</code>
<code>America/New_York</code>

استخدم اسمًا صحيحًا من IANA Time Zone.
""",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ رجوع للتذكير", callback_data="adhkar_reminders")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
            ])
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

🤲 يحتوي البوت على أذكار الصباح والمساء بلغات متعددة مع عداد تكرار.
⏰ ويمكن لكل مستخدم اختيار وقت التذكير والمنطقة الزمنية الخاصة به.

🌍 القناة:
{esc(CHANNEL_ID)}
""",
            back()
        )

    elif data == "admin":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return
        await safe_edit(q, "🛠️ <b>لوحة الإدارة</b>\n\nاختر إجراء:", admin_menu())

    elif data == "admin_post_hadith":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return
        text, hid = hadith_channel_message()
        await send_channel_message(context, text, "hadith", hid, "admin_manual_hadith")
        await safe_edit(q, "✅ <b>تم نشر حديث في القناة.</b>", admin_menu())

    elif data == "admin_post_quran":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return
        text, ayah_ref = quran_channel_message()
        await send_channel_message(context, text, "quran", ayah_ref, "admin_manual_quran")
        await safe_edit(q, "✅ <b>تم نشر آية في القناة.</b>", admin_menu())

    elif data == "admin_post_mixed":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return
        text, item_id = mixed_channel_message()
        await send_channel_message(context, text, "mixed", item_id, "admin_manual_mixed")
        await safe_edit(q, "✅ <b>تم نشر آية + حديث في القناة.</b>", admin_menu())

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

🔁 <b>ميزة عداد التكرار:</b> مفعلة
⏰ <b>التذكير الشخصي:</b> مفعّل
🌍 <b>المنطقة الزمنية لكل مستخدم:</b> مفعّلة

⏰ <b>الأوقات الافتراضية للمستخدم الجديد:</b>
• صباح: <code>{esc(DEFAULT_MORNING_ADHKAR_TIME)}</code>
• مساء: <code>{esc(DEFAULT_EVENING_ADHKAR_TIME)}</code>
• Timezone: <code>{esc(safe_timezone(DEFAULT_USER_TIMEZONE))}</code>

🌐 <b>القناة:</b> {esc(CHANNEL_ID)}
""",
            admin_menu()
        )

    elif data == "admin_custom_post":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return
        context.user_data["waiting_custom_post"] = True
        await safe_edit(q, "✍️ <b>أرسل الآن الرسالة التي تريد نشرها في القناة.</b>", admin_back())


# =====================================================
# Text Handler
# =====================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    add_user(user_id)
    ensure_adhkar_reminder_row(user_id, chat_id)

    if context.user_data.get("waiting_adhkar_custom_time"):
        kind = context.user_data.get("waiting_adhkar_custom_time")
        text = update.message.text.strip()

        if not is_valid_hhmm(text):
            await update.message.reply_text(
                "❌ الوقت غير صحيح.\n\nأرسله بهذه الصيغة فقط:\n<code>07:30</code>",
                parse_mode="HTML"
            )
            return

        context.user_data["waiting_adhkar_custom_time"] = None
        ok = set_adhkar_reminder_time(user_id, chat_id, kind, text)

        if ok:
            await update.message.reply_text(
                f"✅ تم حفظ وقت التذكير: <code>{esc(text)}</code>",
                reply_markup=adhkar_reminder_menu(user_id, chat_id),
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("❌ حدث خطأ أثناء حفظ الوقت.")

        return

    if context.user_data.get("waiting_adhkar_custom_timezone"):
        timezone_name = update.message.text.strip()

        if not is_valid_timezone(timezone_name):
            await update.message.reply_text(
                """❌ المنطقة الزمنية غير صحيحة.

أرسل اسمًا صحيحًا مثل:
<code>Europe/Berlin</code>
<code>Asia/Riyadh</code>
<code>Africa/Casablanca</code>
<code>America/New_York</code>
""",
                parse_mode="HTML"
            )
            return

        context.user_data["waiting_adhkar_custom_timezone"] = False
        set_user_timezone(user_id, chat_id, timezone_name)
        local_now = user_now(timezone_name).strftime("%Y-%m-%d %H:%M")

        await update.message.reply_text(
            f"""✅ تم حفظ المنطقة الزمنية:
<code>{esc(timezone_name)}</code>

🕒 الوقت الحالي حسبها:
<code>{esc(local_now)}</code>
""",
            reply_markup=adhkar_reminder_menu(user_id, chat_id),
            parse_mode="HTML"
        )
        return

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

    app.job_queue.run_repeating(
        check_personal_adhkar_reminders,
        interval=60,
        first=10
    )

    print("Bot running with personal adhkar reminder times + user timezones...")
    print(f"Hadith post time: {HADITH_POST_TIME}")
    print(f"Quran post time: {QURAN_POST_TIME}")
    print(f"Mixed post time: {MIXED_POST_TIME}")
    print(f"Default morning adhkar time: {DEFAULT_MORNING_ADHKAR_TIME}")
    print(f"Default evening adhkar time: {DEFAULT_EVENING_ADHKAR_TIME}")
    print(f"Default user timezone: {safe_timezone(DEFAULT_USER_TIMEZONE)}")
    print("Personal reminders checker: every 60 seconds")

    app.run_polling()


if __name__ == "__main__":
    main()