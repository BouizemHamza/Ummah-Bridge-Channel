# bot.py
# Ummah Bridge Bot
# Features:
# - Telegram channel posting: Hadith, Quran Ayah, Dua
# - Admin approval before automatic posts
# - WhatsApp channel button
# - Morning/evening adhkar with multilingual support from adhkar_data.py
# - Personal adhkar reminder time + timezone per user
# - Adhkar completion + streaks
# - Manual Islamic quiz from admin panel, answered inside the bot

import os
import random
import sqlite3
import requests
import html
import datetime
import time
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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

from learn_islam_data import LEARN_ISLAM_TOPICS


# =====================================================
# ENV
# =====================================================

TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Ummahbridgebot").replace("@", "").strip()

CHANNEL_ID = os.environ.get("CHANNEL_ID", "@UMMAHBRIDGE")
WHATSAPP_CHANNEL_URL = os.environ.get("WHATSAPP_CHANNEL_URL", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

HADITH_POST_TIME = os.environ.get("HADITH_POST_TIME", "09:00")
QURAN_POST_TIME = os.environ.get("QURAN_POST_TIME", "15:00")
DUA_POST_TIME = os.environ.get("DUA_POST_TIME", "12:00")

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

    if is_valid_timezone(DEFAULT_USER_TIMEZONE):
        return DEFAULT_USER_TIMEZONE

    return "UTC"


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
        bot_lang TEXT DEFAULT 'ar',
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
    CREATE TABLE IF NOT EXISTS adhkar_completions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        completed_date TEXT NOT NULL,
        completed_at INTEGER NOT NULL,
        timezone TEXT DEFAULT '',
        UNIQUE(user_id, kind, completed_date)
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS pending_channel_posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_type TEXT NOT NULL,
        item_id TEXT,
        text TEXT NOT NULL,
        source TEXT DEFAULT 'auto',
        created_at INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS quiz_answers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        quiz_id TEXT NOT NULL,
        selected INTEGER NOT NULL,
        correct INTEGER NOT NULL,
        answered_at INTEGER NOT NULL,
        UNIQUE(user_id, quiz_id)
    )
    """)

    c.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in c.fetchall()]
    if "bot_lang" not in user_cols:
        c.execute("ALTER TABLE users ADD COLUMN bot_lang TEXT DEFAULT 'ar'")
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
        c.execute(
            f"ALTER TABLE adhkar_reminders ADD COLUMN morning_time TEXT DEFAULT '{DEFAULT_MORNING_ADHKAR_TIME}'"
        )
    if "evening_time" not in reminder_cols:
        c.execute(
            f"ALTER TABLE adhkar_reminders ADD COLUMN evening_time TEXT DEFAULT '{DEFAULT_EVENING_ADHKAR_TIME}'"
        )
    if "timezone" not in reminder_cols:
        c.execute(
            f"ALTER TABLE adhkar_reminders ADD COLUMN timezone TEXT DEFAULT '{safe_timezone(DEFAULT_USER_TIMEZONE)}'"
        )
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


def get_bot_lang(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT bot_lang FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return "ar"

    if row[0] not in BOT_TEXTS:
        return "ar"

    return row[0]


def set_bot_lang(user_id, lang):
    if lang not in BOT_TEXTS:
        lang = "ar"

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE users SET bot_lang=? WHERE user_id=?", (lang, user_id))
    conn.commit()
    conn.close()

    if lang in ADHKAR_LANGUAGES:
        set_adhkar_lang(user_id, lang)


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
# Pending Channel Posts
# =====================================================

def create_pending_channel_post(post_type, text, item_id=None, source="auto"):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO pending_channel_posts(post_type, item_id, text, source, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (post_type, str(item_id or ""), text, source, now_timestamp())
    )

    pending_id = c.lastrowid

    conn.commit()
    conn.close()

    return pending_id


def get_pending_channel_post(pending_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        """
        SELECT id, post_type, item_id, text, source, created_at
        FROM pending_channel_posts
        WHERE id=?
        """,
        (pending_id,)
    )

    row = c.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "post_type": row[1],
        "item_id": row[2],
        "text": row[3],
        "source": row[4],
        "created_at": row[5],
    }


def delete_pending_channel_post(pending_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM pending_channel_posts WHERE id=?", (pending_id,))
    conn.commit()
    conn.close()


def pending_channel_posts_count():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM pending_channel_posts")
    count = c.fetchone()[0]
    conn.close()
    return count


def pending_type_title(post_type):
    titles = {
        "hadith": "🕊️ حديث اليوم",
        "quran": "📖 آية اليوم",
        "dua": "🤲 دعاء اليوم",
        "custom": "✍️ رسالة مخصصة",
    }
    return titles.get(post_type, post_type)


def pending_approval_keyboard(pending_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ انشر الآن", callback_data=f"pending_publish_{pending_id}")],
        [InlineKeyboardButton("🔄 غيّر المحتوى", callback_data=f"pending_regen_{pending_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data=f"pending_cancel_{pending_id}")],
    ])


async def send_pending_preview(context, post_type, text, item_id=None, source="auto"):
    if not ADMIN_ID:
        await send_channel_message(context, text, post_type, item_id, source)
        return

    pending_id = create_pending_channel_post(post_type, text, item_id, source)

    preview = f"""📋 <b>معاينة منشور القناة</b>

النوع: <b>{esc(pending_type_title(post_type))}</b>
Pending ID: <code>{pending_id}</code>

هل تريد نشر هذا المحتوى في القناة؟

━━━━━━━━━━━━━━

{text}
"""

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=preview,
        reply_markup=pending_approval_keyboard(pending_id),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


def generate_channel_post_by_type(post_type):
    if post_type == "hadith":
        text, item_id = hadith_channel_message()
        return text, item_id

    if post_type == "quran":
        text, item_id = quran_channel_message()
        return text, item_id

    if post_type == "dua":
        text, item_id = dua_channel_message()
        return text, item_id

    return "❌ نوع منشور غير معروف.", ""


# =====================================================
# Adhkar Completion + Streak
# =====================================================

def get_completion_dates(user_id, kind):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        """
        SELECT completed_date
        FROM adhkar_completions
        WHERE user_id=? AND kind=?
        ORDER BY completed_date ASC
        """,
        (user_id, kind)
    )

    rows = c.fetchall()
    conn.close()

    dates = []

    for row in rows:
        try:
            dates.append(datetime.date.fromisoformat(row[0]))
        except Exception:
            pass

    return dates


def calculate_current_streak(dates, today_date):
    if not dates:
        return 0

    date_set = set(dates)

    if today_date not in date_set:
        return 0

    streak = 0
    current = today_date

    while current in date_set:
        streak += 1
        current = current - datetime.timedelta(days=1)

    return streak


def calculate_best_streak(dates):
    if not dates:
        return 0

    unique_dates = sorted(set(dates))

    best = 1
    current_streak = 1

    for i in range(1, len(unique_dates)):
        previous = unique_dates[i - 1]
        current = unique_dates[i]

        if current == previous + datetime.timedelta(days=1):
            current_streak += 1
        else:
            current_streak = 1

        if current_streak > best:
            best = current_streak

    return best


def get_adhkar_completion_stats(user_id, chat_id, kind):
    status = get_adhkar_reminder_status(user_id, chat_id)
    tz_name = status["timezone"]

    today_text = user_today_key(tz_name)
    today_date = datetime.date.fromisoformat(today_text)

    dates = get_completion_dates(user_id, kind)

    total = len(dates)
    current_streak = calculate_current_streak(dates, today_date)
    best_streak = calculate_best_streak(dates)

    return {
        "total": total,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "today": today_text,
        "timezone": tz_name,
    }


def record_adhkar_completion(user_id, chat_id, kind):
    status = get_adhkar_reminder_status(user_id, chat_id)
    tz_name = status["timezone"]

    today_text = user_today_key(tz_name)
    completed_at = now_timestamp()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        """
        INSERT OR IGNORE INTO adhkar_completions(
            user_id,
            kind,
            completed_date,
            completed_at,
            timezone
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, kind, today_text, completed_at, tz_name)
    )

    inserted = c.rowcount == 1

    conn.commit()
    conn.close()

    stats = get_adhkar_completion_stats(user_id, chat_id, kind)
    stats["inserted"] = inserted

    return stats


def adhkar_completions_count():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM adhkar_completions")
    count = c.fetchone()[0]
    conn.close()
    return count


def render_completion_message(kind, stats):
    if kind == "morning":
        title = "🌅 أذكار الصباح"
    else:
        title = "🌙 أذكار المساء"

    if stats["inserted"]:
        opening = f"✅ <b>تم تسجيل إنجازك اليومي</b>\n\n{title}"
    else:
        opening = f"ℹ️ <b>تم تسجيل هذا الإنجاز مسبقًا اليوم</b>\n\n{title}"

    return f"""{opening}

📅 <b>تاريخ اليوم:</b> <code>{esc(stats["today"])}</code>
🌍 <b>المنطقة الزمنية:</b> <code>{esc(stats["timezone"])}</code>

🔥 <b>سلسلتك الحالية:</b> {stats["current_streak"]} يوم
🏆 <b>أفضل سلسلة:</b> {stats["best_streak"]} يوم
📊 <b>إجمالي مرات الإكمال:</b> {stats["total"]}
"""


def render_user_adhkar_stats(user_id, chat_id):
    morning = get_adhkar_completion_stats(user_id, chat_id, "morning")
    evening = get_adhkar_completion_stats(user_id, chat_id, "evening")

    return f"""📊 <b>إحصائيات الأذكار</b>

🌅 <b>أذكار الصباح</b>
✅ المكتملة: {morning["total"]}
🔥 السلسلة الحالية: {morning["current_streak"]} يوم
🏆 أفضل سلسلة: {morning["best_streak"]} يوم

━━━━━━━━━━━━━━

🌙 <b>أذكار المساء</b>
✅ المكتملة: {evening["total"]}
🔥 السلسلة الحالية: {evening["current_streak"]} يوم
🏆 أفضل سلسلة: {evening["best_streak"]} يوم

━━━━━━━━━━━━━━

🌍 <b>المنطقة الزمنية:</b>
<code>{esc(morning["timezone"])}</code>

📅 <b>تاريخ اليوم حسب منطقتك:</b>
<code>{esc(morning["today"])}</code>
"""


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


# =====================================================
# Dua of the Day
# =====================================================

DAILY_DUAS = [
    {
        "id": "quran_2_201",
        "ar": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ.",
        "en": "Our Lord, grant us good in this world and good in the Hereafter, and protect us from the punishment of the Fire.",
        "de": "Unser Herr, gib uns Gutes im Diesseits und Gutes im Jenseits und bewahre uns vor der Strafe des Feuers.",
        "source": "القرآن الكريم 2:201",
    },
    {
        "id": "quran_3_8",
        "ar": "رَبَّنَا لَا تُزِغْ قُلُوبَنَا بَعْدَ إِذْ هَدَيْتَنَا وَهَبْ لَنَا مِنْ لَدُنْكَ رَحْمَةً إِنَّكَ أَنْتَ الْوَهَّابُ.",
        "en": "Our Lord, do not let our hearts deviate after You have guided us, and grant us mercy from Yourself. Indeed, You are the Bestower.",
        "de": "Unser Herr, lass unsere Herzen nicht abweichen, nachdem Du uns rechtgeleitet hast, und schenke uns Barmherzigkeit von Dir.",
        "source": "القرآن الكريم 3:8",
    },
    {
        "id": "quran_7_23",
        "ar": "رَبَّنَا ظَلَمْنَا أَنْفُسَنَا وَإِنْ لَمْ تَغْفِرْ لَنَا وَتَرْحَمْنَا لَنَكُونَنَّ مِنَ الْخَاسِرِينَ.",
        "en": "Our Lord, we have wronged ourselves. If You do not forgive us and have mercy on us, we will surely be among the losers.",
        "de": "Unser Herr, wir haben uns selbst Unrecht getan. Wenn Du uns nicht vergibst und Dich unser erbarmst, werden wir zu den Verlierern gehören.",
        "source": "القرآن الكريم 7:23",
    },
    {
        "id": "quran_20_114",
        "ar": "رَبِّ زِدْنِي عِلْمًا.",
        "en": "My Lord, increase me in knowledge.",
        "de": "Mein Herr, mehre mein Wissen.",
        "source": "القرآن الكريم 20:114",
    },
    {
        "id": "quran_25_74",
        "ar": "رَبَّنَا هَبْ لَنَا مِنْ أَزْوَاجِنَا وَذُرِّيَّاتِنَا قُرَّةَ أَعْيُنٍ وَاجْعَلْنَا لِلْمُتَّقِينَ إِمَامًا.",
        "en": "Our Lord, grant us from our spouses and offspring comfort to our eyes, and make us leaders for the righteous.",
        "de": "Unser Herr, schenke uns an unseren Ehepartnern und Nachkommen Freude und mache uns zu Vorbildern für die Gottesfürchtigen.",
        "source": "القرآن الكريم 25:74",
    },
    {
        "id": "dua_forgiveness",
        "ar": "اللَّهُمَّ إِنَّكَ عَفُوٌّ تُحِبُّ الْعَفْوَ فَاعْفُ عَنِّي.",
        "en": "O Allah, You are Pardoning and You love pardon, so pardon me.",
        "de": "O Allah, Du bist vergebend und liebst die Vergebung, so vergib mir.",
        "source": "دعاء مأثور",
    },
]


def dua_channel_message():
    try:
        dua = random.choice(DAILY_DUAS)

        text = f"""🤲 <b>دعاء اليوم | Dua of the Day | Bittgebet des Tages</b>

━━━━━━━━━━━━━━

🇸🇦 <b>العربية</b>

{esc(dua["ar"])}

━━━━━━━━━━━━━━

🇬🇧 <b>English</b>

{esc(dua["en"])}

━━━━━━━━━━━━━━

🇩🇪 <b>Deutsch</b>

{esc(dua["de"])}

━━━━━━━━━━━━━━

📚 <b>المصدر:</b> {esc(dua["source"])}
🔢 <b>Dua ID:</b> <code>{esc(dua["id"])}</code>

🌍 {esc(CHANNEL_ID)}
"""

        return text, dua["id"]

    except Exception as e:
        return f"❌ خطأ في بناء رسالة الدعاء:\n<code>{esc(e)}</code>", None


# =====================================================
# Islamic Quiz
# =====================================================

DAILY_QUIZZES = [
    {
        "id": "q001",
        "question": "ما أول سورة في القرآن الكريم؟",
        "choices": ["البقرة", "الفاتحة", "الإخلاص", "الناس"],
        "correct": 1,
        "explanation": "أول سورة في ترتيب المصحف هي سورة الفاتحة.",
    },
    {
        "id": "q002",
        "question": "كم عدد أركان الإسلام؟",
        "choices": ["ثلاثة", "أربعة", "خمسة", "ستة"],
        "correct": 2,
        "explanation": "أركان الإسلام خمسة: الشهادتان، الصلاة، الزكاة، الصوم، والحج.",
    },
    {
        "id": "q003",
        "question": "ما الشهر الذي يصومه المسلمون؟",
        "choices": ["محرم", "رجب", "رمضان", "شوال"],
        "correct": 2,
        "explanation": "فرض الله صيام شهر رمضان على المسلمين.",
    },
    {
        "id": "q004",
        "question": "ما قبلة المسلمين في الصلاة؟",
        "choices": ["المسجد النبوي", "المسجد الأقصى", "الكعبة", "غار حراء"],
        "correct": 2,
        "explanation": "قبلة المسلمين هي الكعبة المشرفة في مكة.",
    },
    {
        "id": "q005",
        "question": "من هو خاتم الأنبياء والمرسلين؟",
        "choices": ["موسى عليه السلام", "عيسى عليه السلام", "إبراهيم عليه السلام", "محمد ﷺ"],
        "correct": 3,
        "explanation": "النبي محمد ﷺ هو خاتم الأنبياء والمرسلين.",
    },
    {
        "id": "q006",
        "question": "كم عدد الصلوات المفروضة في اليوم والليلة؟",
        "choices": ["ثلاث", "أربع", "خمس", "ست"],
        "correct": 2,
        "explanation": "الصلوات المفروضة خمس صلوات في اليوم والليلة.",
    },
    {
        "id": "q007",
        "question": "ما أطول سورة في القرآن؟",
        "choices": ["آل عمران", "البقرة", "النساء", "المائدة"],
        "correct": 1,
        "explanation": "أطول سورة في القرآن الكريم هي سورة البقرة.",
    },
    {
        "id": "q008",
        "question": "ما أول ركن من أركان الإسلام؟",
        "choices": ["الصلاة", "الزكاة", "الشهادتان", "الحج"],
        "correct": 2,
        "explanation": "أول ركن من أركان الإسلام هو شهادة أن لا إله إلا الله وأن محمدًا رسول الله.",
    },
]


def get_quiz_by_id(quiz_id):
    for quiz in DAILY_QUIZZES:
        if quiz["id"] == quiz_id:
            return quiz
    return None


def random_quiz():
    return random.choice(DAILY_QUIZZES)


def quiz_start_url(quiz_id):
    return f"https://t.me/{BOT_USERNAME}?start=quiz_{quiz_id}"


def quiz_channel_message(quiz=None):
    quiz = quiz or random_quiz()
    letters = ["A", "B", "C", "D"]

    choices_text = ""
    for i, choice in enumerate(quiz["choices"]):
        choices_text += f"{letters[i]}) {esc(choice)}\n"

    text = f"""🧠 <b>سؤال إسلامي</b>

{esc(quiz["question"])}

{choices_text}
━━━━━━━━━━━━━━

اضغط الزر للإجابة داخل البوت ومعرفة النتيجة.
🌍 {esc(CHANNEL_ID)}
"""

    return text, quiz["id"]


def quiz_channel_keyboard(quiz_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 أجب في البوت", url=quiz_start_url(quiz_id))]
    ])


def render_quiz_question(quiz):
    letters = ["A", "B", "C", "D"]
    buttons = []

    for i, choice in enumerate(quiz["choices"]):
        buttons.append([
            InlineKeyboardButton(
                f"{letters[i]}) {choice}",
                callback_data=f"quiz_answer_{quiz['id']}_{i}"
            )
        ])

    buttons.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")])

    text = f"""🧠 <b>سؤال إسلامي</b>

{esc(quiz["question"])}

اختر الإجابة:
"""

    return text, InlineKeyboardMarkup(buttons)


def record_quiz_answer(user_id, quiz_id, selected, correct):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        """
        INSERT OR IGNORE INTO quiz_answers(
            user_id,
            quiz_id,
            selected,
            correct,
            answered_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, quiz_id, selected, 1 if correct else 0, now_timestamp())
    )

    inserted = c.rowcount == 1

    conn.commit()
    conn.close()

    return inserted


def quiz_answers_count():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM quiz_answers")
    count = c.fetchone()[0]
    conn.close()
    return count


def quiz_correct_answers_count():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM quiz_answers WHERE correct=1")
    count = c.fetchone()[0]
    conn.close()
    return count


# =====================================================
# UI Menus
# =====================================================

def language_display(lang):
    item = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])
    return f"{item['flag']} {item['name']}"


BOT_TEXTS = {
    "ar": {
        "welcome": "🌉 <b>مرحبًا بك في Ummah Bridge</b>\n\nاختر من القائمة أسفل الشاشة:",
        "choose": "اختر من القائمة",
        "quran": "📖 القرآن",
        "hadith": "🕊️ الأحاديث",
        "adhkar": "🤲 الأذكار",
        "quiz": "🧠 سؤال إسلامي",
        "learn": "🧭 تعلم الإسلام",
        "bot_language": "🌍 لغة البوت",
        "about": "ℹ️ عن المشروع",
        "telegram": "🌐 Telegram",
        "whatsapp": "🟢 WhatsApp",
        "home": "🏠 القائمة الرئيسية",
        "admin": "🛠️ لوحة الإدارة",
        "learn_title": "🧭 <b>تعلم الإسلام</b>\n\nاختر درسًا:",
        "language_title": "🌍 <b>اختر لغة البوت:</b>",
        "language_saved": "✅ تم تغيير لغة البوت إلى:",
        "unknown": "استخدم القائمة أسفل الشاشة أو اضغط /start.",
    },
    "en": {
        "welcome": "🌉 <b>Welcome to Ummah Bridge</b>\n\nChoose from the menu below:",
        "choose": "Choose from the menu",
        "quran": "📖 Quran",
        "hadith": "🕊️ Hadiths",
        "adhkar": "🤲 Adhkar",
        "quiz": "🧠 Islamic Quiz",
        "learn": "🧭 Learn Islam",
        "bot_language": "🌍 Bot Language",
        "about": "ℹ️ About",
        "telegram": "🌐 Telegram",
        "whatsapp": "🟢 WhatsApp",
        "home": "🏠 Main Menu",
        "admin": "🛠️ Admin Panel",
        "learn_title": "🧭 <b>Learn Islam</b>\n\nChoose a lesson:",
        "language_title": "🌍 <b>Choose bot language:</b>",
        "language_saved": "✅ Bot language changed to:",
        "unknown": "Use the menu below or press /start.",
    },
    "de": {
        "welcome": "🌉 <b>Willkommen bei Ummah Bridge</b>\n\nWähle aus dem Menü unten:",
        "choose": "Aus dem Menü wählen",
        "quran": "📖 Quran",
        "hadith": "🕊️ Hadithe",
        "adhkar": "🤲 Adhkar",
        "quiz": "🧠 Islamisches Quiz",
        "learn": "🧭 Islam lernen",
        "bot_language": "🌍 Bot-Sprache",
        "about": "ℹ️ Über das Projekt",
        "telegram": "🌐 Telegram",
        "whatsapp": "🟢 WhatsApp",
        "home": "🏠 Hauptmenü",
        "admin": "🛠️ Admin-Bereich",
        "learn_title": "🧭 <b>Islam lernen</b>\n\nWähle eine Lektion:",
        "language_title": "🌍 <b>Bot-Sprache wählen:</b>",
        "language_saved": "✅ Bot-Sprache geändert zu:",
        "unknown": "Nutze das Menü unten oder drücke /start.",
    },
    "fr": {
        "welcome": "🌉 <b>Bienvenue sur Ummah Bridge</b>\n\nChoisissez dans le menu ci-dessous:",
        "choose": "Choisir dans le menu",
        "quran": "📖 Coran",
        "hadith": "🕊️ Hadiths",
        "adhkar": "🤲 Adhkar",
        "quiz": "🧠 Quiz islamique",
        "learn": "🧭 Apprendre l’islam",
        "bot_language": "🌍 Langue du bot",
        "about": "ℹ️ À propos",
        "telegram": "🌐 Telegram",
        "whatsapp": "🟢 WhatsApp",
        "home": "🏠 Menu principal",
        "admin": "🛠️ Administration",
        "learn_title": "🧭 <b>Apprendre l’islam</b>\n\nChoisissez une courte leçon:",
        "language_title": "🌍 <b>Choisissez la langue du bot:</b>",
        "language_saved": "✅ Langue du bot changée en:",
        "unknown": "Utilisez le menu ci-dessous ou appuyez sur /start.",
    },
    "es": {
        "welcome": "🌉 <b>Bienvenido a Ummah Bridge</b>\n\nElige en el menú de abajo:",
        "choose": "Elige del menú",
        "quran": "📖 Corán",
        "hadith": "🕊️ Hadices",
        "adhkar": "🤲 Adhkar",
        "quiz": "🧠 Quiz islámico",
        "learn": "🧭 Aprender Islam",
        "bot_language": "🌍 Idioma del bot",
        "about": "ℹ️ Acerca de",
        "telegram": "🌐 Telegram",
        "whatsapp": "🟢 WhatsApp",
        "home": "🏠 Menú principal",
        "admin": "🛠️ Administración",
        "learn_title": "🧭 <b>Aprender Islam</b>\n\nElige una lección corta:",
        "language_title": "🌍 <b>Elige el idioma del bot:</b>",
        "language_saved": "✅ Idioma del bot cambiado a:",
        "unknown": "Usa el menú de abajo o pulsa /start.",
    },
    "tr": {
        "welcome": "🌉 <b>Ummah Bridge'e hoş geldiniz</b>\n\nAşağıdaki menüden seçin:",
        "choose": "Menüden seçin",
        "quran": "📖 Kur’an",
        "hadith": "🕊️ Hadisler",
        "adhkar": "🤲 Zikirler",
        "quiz": "🧠 İslami soru",
        "learn": "🧭 İslamı öğren",
        "bot_language": "🌍 Bot dili",
        "about": "ℹ️ Hakkında",
        "telegram": "🌐 Telegram",
        "whatsapp": "🟢 WhatsApp",
        "home": "🏠 Ana menü",
        "admin": "🛠️ Yönetim paneli",
        "learn_title": "🧭 <b>İslamı öğren</b>\n\nKısa bir ders seçin:",
        "language_title": "🌍 <b>Bot dilini seçin:</b>",
        "language_saved": "✅ Bot dili değiştirildi:",
        "unknown": "Aşağıdaki menüyü kullanın veya /start yazın.",
    },
    "id": {
        "welcome": "🌉 <b>Selamat datang di Ummah Bridge</b>\n\nPilih dari menu di bawah:",
        "choose": "Pilih dari menu",
        "quran": "📖 Quran",
        "hadith": "🕊️ Hadis",
        "adhkar": "🤲 Adhkar",
        "quiz": "🧠 Kuis Islam",
        "learn": "🧭 Belajar Islam",
        "bot_language": "🌍 Bahasa bot",
        "about": "ℹ️ Tentang",
        "telegram": "🌐 Telegram",
        "whatsapp": "🟢 WhatsApp",
        "home": "🏠 Menu utama",
        "admin": "🛠️ Panel admin",
        "learn_title": "🧭 <b>Belajar Islam</b>\n\nPilih pelajaran singkat:",
        "language_title": "🌍 <b>Pilih bahasa bot:</b>",
        "language_saved": "✅ Bahasa bot diubah ke:",
        "unknown": "Gunakan menu di bawah atau tekan /start.",
    },
    "ur": {
        "welcome": "🌉 <b>Ummah Bridge میں خوش آمدید</b>\n\nنیچے مینو سے منتخب کریں:",
        "choose": "مینو سے منتخب کریں",
        "quran": "📖 قرآن",
        "hadith": "🕊️ احادیث",
        "adhkar": "🤲 اذکار",
        "quiz": "🧠 اسلامی سوال",
        "learn": "🧭 اسلام سیکھیں",
        "bot_language": "🌍 بوٹ کی زبان",
        "about": "ℹ️ تعارف",
        "telegram": "🌐 Telegram",
        "whatsapp": "🟢 WhatsApp",
        "home": "🏠 مین مینو",
        "admin": "🛠️ ایڈمن پینل",
        "learn_title": "🧭 <b>اسلام سیکھیں</b>\n\nایک مختصر سبق منتخب کریں:",
        "language_title": "🌍 <b>بوٹ کی زبان منتخب کریں:</b>",
        "language_saved": "✅ بوٹ کی زبان تبدیل ہو گئی:",
        "unknown": "نیچے مینو استعمال کریں یا /start دبائیں.",
    },
    "hi": {
        "welcome": "🌉 <b>Ummah Bridge में आपका स्वागत है</b>\n\nनीचे मेनू से चुनें:",
        "choose": "मेनू से चुनें",
        "quran": "📖 कुरआन",
        "hadith": "🕊️ हदीस",
        "adhkar": "🤲 अज़कार",
        "quiz": "🧠 इस्लामी प्रश्न",
        "learn": "🧭 इस्लाम सीखें",
        "bot_language": "🌍 बॉट भाषा",
        "about": "ℹ️ परिचय",
        "telegram": "🌐 Telegram",
        "whatsapp": "🟢 WhatsApp",
        "home": "🏠 मुख्य मेनू",
        "admin": "🛠️ एडमिन पैनल",
        "learn_title": "🧭 <b>इस्लाम सीखें</b>\n\nएक छोटा पाठ चुनें:",
        "language_title": "🌍 <b>बॉट भाषा चुनें:</b>",
        "language_saved": "✅ बॉट भाषा बदल गई:",
        "unknown": "नीचे मेनू उपयोग करें या /start दबाएँ.",
    },
}


# Learn Islam content is stored in learn_islam_data.py
# It supports levels: summary, medium, detailed, sources.
def t(user_id, key):
    lang = get_bot_lang(user_id)
    return BOT_TEXTS.get(lang, BOT_TEXTS["ar"]).get(key, BOT_TEXTS["ar"].get(key, key))


def bot_lang_name(lang):
    names = {
        "ar": "🇸🇦 العربية",
        "en": "🇬🇧 English",
        "de": "🇩🇪 Deutsch",
        "fr": "🇫🇷 Français",
        "es": "🇪🇸 Español",
        "tr": "🇹🇷 Türkçe",
        "id": "🇮🇩 Indonesia",
        "ur": "🇺🇷 اردو",
        "hi": "🇮🇳 हिन्दी",
    }
    return names.get(lang, lang)


def reply_main_menu(user_id):
    rows = [
        [KeyboardButton(t(user_id, "quran")), KeyboardButton(t(user_id, "hadith"))],
        [KeyboardButton(t(user_id, "adhkar")), KeyboardButton(t(user_id, "quiz"))],
        [KeyboardButton(t(user_id, "learn")), KeyboardButton(t(user_id, "bot_language"))],
        [KeyboardButton(t(user_id, "about"))],
        [KeyboardButton(t(user_id, "telegram")), KeyboardButton(t(user_id, "whatsapp"))],
        [KeyboardButton(t(user_id, "home"))],
    ]

    if is_admin(user_id):
        rows.append([KeyboardButton(t(user_id, "admin"))])

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder=BOT_TEXTS.get(get_bot_lang(user_id), BOT_TEXTS["ar"]).get("choose", "Choose")
    )


def is_menu_text(text, key):
    text = (text or "").strip()
    for pack in BOT_TEXTS.values():
        if text == pack.get(key):
            return True
    legacy = {
        "quran": ["📖 القرآن"],
        "hadith": ["🕊️ الأحاديث"],
        "adhkar": ["🤲 الأذكار"],
        "quiz": ["🧠 سؤال إسلامي"],
        "learn": ["🧭 تعلم الإسلام"],
        "bot_language": ["🌍 تغيير اللغة", "🌍 لغة البوت"],
        "about": ["ℹ️ عن المشروع"],
        "telegram": ["🌐 Telegram"],
        "whatsapp": ["🟢 WhatsApp"],
        "home": ["🏠 القائمة الرئيسية", "القائمة الرئيسية", "/menu"],
        "admin": ["🛠️ لوحة الإدارة"],
    }
    return text in legacy.get(key, [])


def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton(t(user_id, "quran"), callback_data="quran")],
        [InlineKeyboardButton(t(user_id, "hadith"), callback_data="hadith")],
        [InlineKeyboardButton(t(user_id, "adhkar"), callback_data="adhkar_menu")],
        [InlineKeyboardButton(t(user_id, "learn"), callback_data="learn_islam")],
        [InlineKeyboardButton(t(user_id, "bot_language"), callback_data="bot_language_menu")],
        [InlineKeyboardButton(t(user_id, "about"), callback_data="about")],
        [InlineKeyboardButton(t(user_id, "telegram"), url="https://t.me/UMMAHBRIDGE")]
    ]

    if WHATSAPP_CHANNEL_URL:
        buttons.append([InlineKeyboardButton(t(user_id, "whatsapp"), url=WHATSAPP_CHANNEL_URL)])

    if is_admin(user_id):
        buttons.append([InlineKeyboardButton(t(user_id, "admin"), callback_data="admin")])

    return InlineKeyboardMarkup(buttons)


def bot_language_menu(user_id):
    rows = [
        [
            InlineKeyboardButton("🇸🇦 العربية", callback_data="botlang_ar"),
            InlineKeyboardButton("🇬🇧 English", callback_data="botlang_en"),
        ],
        [
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data="botlang_de"),
            InlineKeyboardButton("🇫🇷 Français", callback_data="botlang_fr"),
        ],
        [
            InlineKeyboardButton("🇪🇸 Español", callback_data="botlang_es"),
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="botlang_tr"),
        ],
        [
            InlineKeyboardButton("🇮🇩 Indonesia", callback_data="botlang_id"),
            InlineKeyboardButton("🇺🇷 اردو", callback_data="botlang_ur"),
        ],
        [
            InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="botlang_hi"),
        ],
        [InlineKeyboardButton(t(user_id, "home"), callback_data="home")]
    ]
    return InlineKeyboardMarkup(rows)


def learn_topic_label(topic, lang):
    topic_data = LEARN_ISLAM_TOPICS.get(topic, {})
    labels = topic_data.get("title", {})
    return labels.get(lang) or labels.get("en") or labels.get("ar") or topic


def learn_islam_menu(user_id):
    lang = get_bot_lang(user_id)
    rows = []

    for topic in LEARN_ISLAM_TOPICS.keys():
        rows.append([
            InlineKeyboardButton(
                learn_topic_label(topic, lang),
                callback_data=f"learn_topic_{topic}"
            )
        ])

    rows.append([InlineKeyboardButton(t(user_id, "home"), callback_data="home")])
    return InlineKeyboardMarkup(rows)


def learn_level_label(level, lang):
    labels = {
        "summary": {
            "ar": "⚡ ملخص سريع",
            "en": "⚡ Quick summary",
            "de": "⚡ Kurze Zusammenfassung",
            "fr": "⚡ Résumé rapide",
            "es": "⚡ Resumen rápido",
            "tr": "⚡ Kısa özet",
            "id": "⚡ Ringkasan singkat",
            "ur": "⚡ مختصر خلاصہ",
            "hi": "⚡ संक्षिप्त सार",
        },
        "medium": {
            "ar": "📖 شرح متوسط",
            "en": "📖 Medium explanation",
            "de": "📖 Mittlere Erklärung",
            "fr": "📖 Explication moyenne",
            "es": "📖 Explicación media",
            "tr": "📖 Orta açıklama",
            "id": "📖 Penjelasan sedang",
            "ur": "📖 درمیانی شرح",
            "hi": "📖 मध्यम व्याख्या",
        },
        "detailed": {
            "ar": "📚 شرح مفصل",
            "en": "📚 Detailed explanation",
            "de": "📚 Ausführliche Erklärung",
            "fr": "📚 Explication détaillée",
            "es": "📚 Explicación detallada",
            "tr": "📚 Detaylı açıklama",
            "id": "📚 Penjelasan rinci",
            "ur": "📚 تفصیلی شرح",
            "hi": "📚 विस्तृत व्याख्या",
        },
        "sources": {
            "ar": "📚 المصادر",
            "en": "📚 Sources",
            "de": "📚 Quellen",
            "fr": "📚 Sources",
            "es": "📚 Fuentes",
            "tr": "📚 Kaynaklar",
            "id": "📚 Sumber",
            "ur": "📚 مصادر",
            "hi": "📚 स्रोत",
        },
    }

    return labels.get(level, {}).get(lang) or labels.get(level, {}).get("en") or level


def learn_level_menu(user_id, topic):
    lang = get_bot_lang(user_id)
    topic_title = learn_topic_label(topic, lang)

    rows = [
        [InlineKeyboardButton(learn_level_label("summary", lang), callback_data=f"learn_page_{topic}_summary_0")],
        [InlineKeyboardButton(learn_level_label("medium", lang), callback_data=f"learn_page_{topic}_medium_0")],
        [InlineKeyboardButton(learn_level_label("detailed", lang), callback_data=f"learn_page_{topic}_detailed_0")],
        [InlineKeyboardButton(learn_level_label("sources", lang), callback_data=f"learn_page_{topic}_sources_0")],
        [InlineKeyboardButton("⬅️ Back", callback_data="learn_islam")],
        [InlineKeyboardButton(t(user_id, "home"), callback_data="home")],
    ]

    return InlineKeyboardMarkup(rows)


def get_learn_pages(topic, level, lang):
    topic_data = LEARN_ISLAM_TOPICS.get(topic, {})
    levels = topic_data.get("levels", {})
    level_data = levels.get(level, {})

    pages = (
        level_data.get(lang)
        or level_data.get("en")
        or level_data.get("ar")
        or []
    )

    if isinstance(pages, str):
        pages = [pages]

    return pages


def render_learn_page(user_id, topic, level, page):
    lang = get_bot_lang(user_id)
    pages = get_learn_pages(topic, level, lang)

    if not pages:
        return "❌ Lesson not found.", learn_islam_menu(user_id)

    if page < 0:
        page = 0

    if page >= len(pages):
        page = len(pages) - 1

    text = pages[page]

    if len(pages) > 1:
        text += f"\n\n<b>{page + 1}/{len(pages)}</b>"

    buttons = []
    nav = []

    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"learn_page_{topic}_{level}_{page - 1}"))

    if page < len(pages) - 1:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"learn_page_{topic}_{level}_{page + 1}"))

    if nav:
        buttons.append(nav)

    if level != "summary":
        buttons.append([InlineKeyboardButton(learn_level_label("summary", lang), callback_data=f"learn_page_{topic}_summary_0")])

    if level != "sources":
        buttons.append([InlineKeyboardButton(learn_level_label("sources", lang), callback_data=f"learn_page_{topic}_sources_0")])

    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"learn_topic_{topic}")])
    buttons.append([InlineKeyboardButton(t(user_id, "home"), callback_data="home")])

    return text, InlineKeyboardMarkup(buttons)


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
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="adhkar_stats")],
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
        [InlineKeyboardButton("🤲 نشر دعاء الآن", callback_data="admin_post_dua")],
        [InlineKeyboardButton("🧠 نشر سؤال إسلامي", callback_data="admin_post_quiz")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("✍️ إرسال رسالة مخصصة للقناة", callback_data="admin_custom_post")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def about_menu():
    buttons = [
        [InlineKeyboardButton("🌐 قناة Telegram", url="https://t.me/UMMAHBRIDGE")]
    ]

    if WHATSAPP_CHANNEL_URL:
        buttons.append([InlineKeyboardButton("🟢 قناة WhatsApp", url=WHATSAPP_CHANNEL_URL)])

    buttons.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")])

    return InlineKeyboardMarkup(buttons)


def admin_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ رجوع للوحة الإدارة", callback_data="admin")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def adhkar_stats_back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ رجوع للأذكار", callback_data="adhkar_menu")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def completion_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="adhkar_stats")],
        [InlineKeyboardButton("⬅️ رجوع للأذكار", callback_data="adhkar_menu")],
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


async def send_channel_message(context, text, post_type, item_id, source, reply_markup=None):
    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        reply_markup=reply_markup,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    log_channel_post(post_type, item_id, source)


# =====================================================
# Commands
# =====================================================

async def show_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_id: str):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    add_user(user_id)
    ensure_adhkar_reminder_row(user_id, chat_id)

    quiz = get_quiz_by_id(quiz_id)

    if not quiz:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ لم يتم العثور على السؤال.",
            reply_markup=reply_main_menu(user_id),
            parse_mode="HTML"
        )
        return

    text, markup = render_quiz_question(quiz)

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=markup,
        parse_mode="HTML"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    add_user(user_id)
    ensure_adhkar_reminder_row(user_id, chat_id)

    if context.args:
        payload = context.args[0]
        if payload.startswith("quiz_"):
            quiz_id = payload.replace("quiz_", "", 1)
            await show_quiz(update, context, quiz_id)
            return

    await update.message.reply_text(
        t(user_id, "welcome"),
        reply_markup=reply_main_menu(user_id),
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

        await send_pending_preview(
            context=context,
            post_type="hadith",
            text=text,
            item_id=hid,
            source="auto_hadith_pending"
        )

        print("📋 Hadith preview sent to admin.")

    except Exception as e:
        print(f"❌ Auto hadith preview error: {e}")


async def auto_publish_quran(context: ContextTypes.DEFAULT_TYPE):
    try:
        text, ayah_ref = quran_channel_message()

        await send_pending_preview(
            context=context,
            post_type="quran",
            text=text,
            item_id=ayah_ref,
            source="auto_quran_pending"
        )

        print("📋 Quran preview sent to admin.")

    except Exception as e:
        print(f"❌ Auto quran preview error: {e}")


async def auto_publish_dua(context: ContextTypes.DEFAULT_TYPE):
    try:
        text, dua_id = dua_channel_message()

        await send_pending_preview(
            context=context,
            post_type="dua",
            text=text,
            item_id=dua_id,
            source="auto_dua_pending"
        )

        print("📋 Dua preview sent to admin.")

    except Exception as e:
        print(f"❌ Auto dua preview error: {e}")


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

    if data.startswith("quiz_answer_"):
        parts = data.split("_")
        quiz_id = parts[2]
        selected = int(parts[3])

        quiz = get_quiz_by_id(quiz_id)

        if not quiz:
            await safe_edit(q, "❌ لم يتم العثور على السؤال.", main_menu(user_id))
            return

        correct_index = quiz["correct"]
        is_correct = selected == correct_index
        inserted = record_quiz_answer(user_id, quiz_id, selected, is_correct)

        letters = ["A", "B", "C", "D"]
        selected_text = quiz["choices"][selected]
        correct_text = quiz["choices"][correct_index]

        if is_correct:
            result = "✅ <b>إجابة صحيحة</b>"
        else:
            result = "❌ <b>إجابة غير صحيحة</b>"

        already = ""
        if not inserted:
            already = "\n\nℹ️ <i>لقد أجبت على هذا السؤال من قبل. لم يتم احتساب الإجابة مرة ثانية.</i>"

        text = f"""🧠 <b>نتيجة السؤال</b>

{result}

<b>السؤال:</b>
{esc(quiz["question"])}

<b>إجابتك:</b>
{letters[selected]}) {esc(selected_text)}

<b>الإجابة الصحيحة:</b>
{letters[correct_index]}) {esc(correct_text)}

💡 <b>الشرح:</b>
{esc(quiz["explanation"])}
{already}
"""

        await safe_edit(
            q,
            text,
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
            ])
        )

    elif data.startswith("pending_publish_"):
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        pending_id = int(data.replace("pending_publish_", "", 1))
        pending = get_pending_channel_post(pending_id)

        if not pending:
            await safe_edit(q, "❌ هذا المنشور غير موجود أو تم التعامل معه سابقًا.", admin_menu())
            return

        await send_channel_message(
            context=context,
            text=pending["text"],
            post_type=pending["post_type"],
            item_id=pending["item_id"],
            source=f"approved_{pending['source']}"
        )

        delete_pending_channel_post(pending_id)

        await safe_edit(
            q,
            f"✅ <b>تم نشر المنشور في القناة.</b>\n\nالنوع: {esc(pending_type_title(pending['post_type']))}",
            admin_menu()
        )

    elif data.startswith("pending_cancel_"):
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        pending_id = int(data.replace("pending_cancel_", "", 1))
        pending = get_pending_channel_post(pending_id)

        if not pending:
            await safe_edit(q, "❌ هذا المنشور غير موجود أو تم التعامل معه سابقًا.", admin_menu())
            return

        delete_pending_channel_post(pending_id)

        await safe_edit(
            q,
            f"❌ <b>تم إلغاء المنشور.</b>\n\nالنوع: {esc(pending_type_title(pending['post_type']))}",
            admin_menu()
        )

    elif data.startswith("pending_regen_"):
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        pending_id = int(data.replace("pending_regen_", "", 1))
        pending = get_pending_channel_post(pending_id)

        if not pending:
            await safe_edit(q, "❌ هذا المنشور غير موجود أو تم التعامل معه سابقًا.", admin_menu())
            return

        post_type = pending["post_type"]
        delete_pending_channel_post(pending_id)

        new_text, new_item_id = generate_channel_post_by_type(post_type)

        new_pending_id = create_pending_channel_post(
            post_type=post_type,
            text=new_text,
            item_id=new_item_id,
            source=f"regen_{pending['source']}"
        )

        preview = f"""📋 <b>معاينة منشور جديد</b>

النوع: <b>{esc(pending_type_title(post_type))}</b>
Pending ID: <code>{new_pending_id}</code>

تم تغيير المحتوى. هل تريد نشر النسخة الجديدة؟

━━━━━━━━━━━━━━

{new_text}
"""

        await safe_edit(
            q,
            preview,
            pending_approval_keyboard(new_pending_id)
        )

    elif data == "home":
        await q.message.reply_text(
            t(user_id, "welcome"),
            reply_markup=reply_main_menu(user_id),
            parse_mode="HTML"
        )

    elif data == "bot_language_menu":
        await safe_edit(q, t(user_id, "language_title"), bot_language_menu(user_id))

    elif data.startswith("botlang_"):
        lang = data.replace("botlang_", "", 1)
        set_bot_lang(user_id, lang)
        await q.message.reply_text(
            f"{t(user_id, 'language_saved')} <b>{esc(bot_lang_name(lang))}</b>",
            reply_markup=reply_main_menu(user_id),
            parse_mode="HTML"
        )

    elif data == "learn_islam":
        await safe_edit(q, t(user_id, "learn_title"), learn_islam_menu(user_id))

    elif data.startswith("learn_topic_"):
        topic = data.replace("learn_topic_", "", 1)
        topic_title = learn_topic_label(topic, get_bot_lang(user_id))

        await safe_edit(
            q,
            f"{esc(topic_title)}\n\nاختر مستوى القراءة:",
            learn_level_menu(user_id, topic)
        )

    elif data.startswith("learn_page_"):
        parts = data.replace("learn_page_", "", 1).rsplit("_", 2)
        if len(parts) != 3:
            await safe_edit(q, "❌ Lesson not found.", learn_islam_menu(user_id))
            return

        topic, level, page_text = parts

        try:
            page = int(page_text)
        except Exception:
            page = 0

        text, markup = render_learn_page(user_id, topic, level, page)
        await safe_edit(q, text, markup)

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

    elif data == "adhkar_stats":
        text = render_user_adhkar_stats(user_id, chat_id)

        await safe_edit(
            q,
            text,
            adhkar_stats_back_menu()
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
        stats = record_adhkar_completion(user_id, chat_id, "morning")
        text = render_completion_message("morning", stats)

        await safe_edit(q, text, completion_menu())

    elif data == "adhkar_done_evening":
        stats = record_adhkar_completion(user_id, chat_id, "evening")
        text = render_completion_message("evening", stats)

        await safe_edit(q, text, completion_menu())

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

✅ التذكير سيصل حسب منطقتك الزمنية.
"""

        await safe_edit(q, text, adhkar_reminder_menu(user_id, chat_id))

    elif data == "adhkar_toggle_morning":
        status = get_adhkar_reminder_status(user_id, chat_id)
        new_value = 0 if status["morning"] else 1

        set_adhkar_reminder(user_id, chat_id, "morning", new_value)

        await q.answer("تم تحديث تذكير الصباح ✅", show_alert=True)

        await safe_edit(
            q,
            "⏰ <b>تم تحديث إعدادات التذكير.</b>",
            adhkar_reminder_menu(user_id, chat_id)
        )

    elif data == "adhkar_toggle_evening":
        status = get_adhkar_reminder_status(user_id, chat_id)
        new_value = 0 if status["evening"] else 1

        set_adhkar_reminder(user_id, chat_id, "evening", new_value)

        await q.answer("تم تحديث تذكير المساء ✅", show_alert=True)

        await safe_edit(
            q,
            "⏰ <b>تم تحديث إعدادات التذكير.</b>",
            adhkar_reminder_menu(user_id, chat_id)
        )

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

🕊️ حديث اليوم.
📖 آية اليوم.
🤲 دعاء اليوم.
🧠 سؤال إسلامي تفاعلي.

🤲 يحتوي البوت على أذكار الصباح والمساء بلغات متعددة مع عداد تكرار.
🔥 ويحتوي على إنجاز يومي وسلسلة أيام للأذكار.
⏰ ويمكن لكل مستخدم اختيار وقت التذكير والمنطقة الزمنية الخاصة به.
✅ النشر التلقائي للقناة يتم بعد موافقة الأدمن.

🌍 Telegram:
{esc(CHANNEL_ID)}

🟢 WhatsApp:
{esc(WHATSAPP_CHANNEL_URL) if WHATSAPP_CHANNEL_URL else "غير مضاف بعد"}
""",
            about_menu()
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

        await safe_edit(q, "✅ <b>تم نشر حديث في القناة.</b>", admin_menu())

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

        await safe_edit(q, "✅ <b>تم نشر آية في القناة.</b>", admin_menu())

    elif data == "admin_post_dua":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        text, dua_id = dua_channel_message()

        await send_channel_message(
            context=context,
            text=text,
            post_type="dua",
            item_id=dua_id,
            source="admin_manual_dua"
        )

        await safe_edit(q, "✅ <b>تم نشر دعاء في القناة.</b>", admin_menu())

    elif data == "admin_post_quiz":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        quiz = random_quiz()
        text, quiz_id = quiz_channel_message(quiz)

        await send_channel_message(
            context=context,
            text=text,
            post_type="quiz",
            item_id=quiz_id,
            source="admin_manual_quiz",
            reply_markup=quiz_channel_keyboard(quiz_id)
        )

        await safe_edit(
            q,
            f"✅ <b>تم نشر السؤال الإسلامي في القناة.</b>\n\nQuiz ID: <code>{esc(quiz_id)}</code>",
            admin_menu()
        )

    elif data == "admin_stats":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        morning_count = len(get_adhkar_subscribers("morning"))
        evening_count = len(get_adhkar_subscribers("evening"))

        total_quiz_answers = quiz_answers_count()
        correct_quiz_answers = quiz_correct_answers_count()

        await safe_edit(
            q,
            f"""📊 <b>لوحة إحصائيات Ummah Bridge</b>

👥 <b>عدد المستخدمين:</b> {users_count()}
❤️ <b>عدد الأحاديث المحفوظة:</b> {saved_count()}
🤲 <b>إجمالي إنجازات الأذكار:</b> {adhkar_completions_count()}

📢 <b>إجمالي منشورات القناة:</b> {channel_posts_count()}
🕊️ <b>منشورات الحديث:</b> {channel_posts_count_by_type("hadith")}
📖 <b>منشورات القرآن:</b> {channel_posts_count_by_type("quran")}
🤲 <b>منشورات الدعاء:</b> {channel_posts_count_by_type("dua")}
🧠 <b>منشورات الأسئلة:</b> {channel_posts_count_by_type("quiz")}

🧠 <b>إجابات الأسئلة:</b> {total_quiz_answers}
✅ <b>الإجابات الصحيحة:</b> {correct_quiz_answers}

📋 <b>منشورات بانتظار الموافقة:</b> {pending_channel_posts_count()}

🤲 <b>مشتركو تذكير الصباح:</b> {morning_count}
🤲 <b>مشتركو تذكير المساء:</b> {evening_count}

🔁 <b>ميزة عداد التكرار:</b> مفعلة
🔥 <b>إنجاز يومي + Streak:</b> مفعّل
⏰ <b>التذكير الشخصي:</b> مفعّل
🌍 <b>المنطقة الزمنية لكل مستخدم:</b> مفعّلة
✅ <b>مراجعة قبل النشر التلقائي:</b> مفعّلة
🧠 <b>سؤال إسلامي تفاعلي:</b> مفعّل
🟢 <b>زر WhatsApp:</b> {"مفعّل" if WHATSAPP_CHANNEL_URL else "غير مفعّل"}

⏰ <b>أوقات النشر التلقائي:</b>
• حديث اليوم: <code>{esc(HADITH_POST_TIME)}</code>
• دعاء اليوم: <code>{esc(DUA_POST_TIME)}</code>
• آية اليوم: <code>{esc(QURAN_POST_TIME)}</code>

⏰ <b>الأوقات الافتراضية للمستخدم الجديد:</b>
• صباح: <code>{esc(DEFAULT_MORNING_ADHKAR_TIME)}</code>
• مساء: <code>{esc(DEFAULT_EVENING_ADHKAR_TIME)}</code>
• Timezone: <code>{esc(safe_timezone(DEFAULT_USER_TIMEZONE))}</code>

🤖 <b>Bot username:</b> @{esc(BOT_USERNAME)}
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
# Reply Keyboard Main Menu
# =====================================================

async def send_fatiha_from_menu(update: Update):
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

        await update.message.reply_text(
            text,
            reply_markup=back(),
            parse_mode="HTML"
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ خطأ في جلب القرآن:\n<code>{esc(e)}</code>",
            reply_markup=back(),
            parse_mode="HTML"
        )


async def send_about_from_menu(update: Update):
    await update.message.reply_text(
        f"""ℹ️ <b>Ummah Bridge</b>

مشروع دعوي للتعريف بالإسلام عبر الإنترنت.

📖 المصدر:
القرآن الكريم والسنة النبوية.

🚫 لا نقدّم فتاوى.
🚫 لا نقدّم آراء شخصية.
✅ ننشر نصوصًا موثقة ومترجمة.

🕊️ حديث اليوم.
📖 آية اليوم.
🤲 دعاء اليوم.
🧠 سؤال إسلامي تفاعلي.
🧭 تعلم الإسلام بلغات متعددة.

🤲 يحتوي البوت على أذكار الصباح والمساء بلغات متعددة مع عداد تكرار.
🔥 ويحتوي على إنجاز يومي وسلسلة أيام للأذكار.
⏰ ويمكن لكل مستخدم اختيار وقت التذكير والمنطقة الزمنية الخاصة به.
✅ النشر التلقائي للقناة يتم بعد موافقة الأدمن.

🌍 Telegram:
{esc(CHANNEL_ID)}

🟢 WhatsApp:
{esc(WHATSAPP_CHANNEL_URL) if WHATSAPP_CHANNEL_URL else "غير مضاف بعد"}
""",
        reply_markup=about_menu(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


async def handle_reply_keyboard_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = (update.message.text or "").strip()

    if is_menu_text(text, "home"):
        await update.message.reply_text(
            t(user_id, "welcome"),
            reply_markup=reply_main_menu(user_id),
            parse_mode="HTML"
        )
        return True

    if is_menu_text(text, "quran"):
        await send_fatiha_from_menu(update)
        return True

    if is_menu_text(text, "hadith"):
        await update.message.reply_text(
            "🕊️ <b>قسم الأحاديث</b>",
            reply_markup=hadith_menu(),
            parse_mode="HTML"
        )
        return True

    if is_menu_text(text, "adhkar"):
        lang = get_adhkar_lang(user_id)
        await update.message.reply_text(
            f"🤲 <b>قسم الأذكار</b>\n\n"
            f"🌍 اللغة الحالية: <b>{esc(language_display(lang))}</b>\n\n"
            f"اختر ما تريد قراءته:",
            reply_markup=adhkar_main_menu(user_id),
            parse_mode="HTML"
        )
        return True

    if is_menu_text(text, "quiz"):
        quiz = random_quiz()
        quiz_text, quiz_markup = render_quiz_question(quiz)
        await update.message.reply_text(
            quiz_text,
            reply_markup=quiz_markup,
            parse_mode="HTML"
        )
        return True

    if is_menu_text(text, "learn"):
        await update.message.reply_text(
            t(user_id, "learn_title"),
            reply_markup=learn_islam_menu(user_id),
            parse_mode="HTML"
        )
        return True

    if is_menu_text(text, "bot_language"):
        await update.message.reply_text(
            t(user_id, "language_title"),
            reply_markup=bot_language_menu(user_id),
            parse_mode="HTML"
        )
        return True

    if is_menu_text(text, "about"):
        await send_about_from_menu(update)
        return True

    if is_menu_text(text, "telegram"):
        await update.message.reply_text(
            "🌐 Telegram:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Open Telegram", url="https://t.me/UMMAHBRIDGE")]
            ]),
            parse_mode="HTML"
        )
        return True

    if is_menu_text(text, "whatsapp"):
        if WHATSAPP_CHANNEL_URL:
            await update.message.reply_text(
                "🟢 WhatsApp:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🟢 Open WhatsApp", url=WHATSAPP_CHANNEL_URL)]
                ]),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text("❌ رابط قناة WhatsApp غير مضاف بعد.")
        return True

    if is_menu_text(text, "admin"):
        if not is_admin(user_id):
            await update.message.reply_text("❌ هذا القسم خاص بالمشرف فقط.")
            return True

        await update.message.reply_text(
            "🛠️ <b>لوحة الإدارة</b>\n\nاختر إجراء:",
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )
        return True

    return False



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
        return

    handled = await handle_reply_keyboard_menu(update, context)
    if handled:
        return

    await update.message.reply_text(
        t(user_id, "unknown"),
        reply_markup=reply_main_menu(user_id),
        parse_mode="HTML"
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
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("test_channel", test_channel))
    app.add_handler(CallbackQueryHandler(handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.job_queue.run_daily(
        auto_publish_hadith,
        time=parse_schedule_time(HADITH_POST_TIME, "09:00")
    )

    app.job_queue.run_daily(
        auto_publish_dua,
        time=parse_schedule_time(DUA_POST_TIME, "12:00")
    )

    app.job_queue.run_daily(
        auto_publish_quran,
        time=parse_schedule_time(QURAN_POST_TIME, "15:00")
    )

    app.job_queue.run_repeating(
        check_personal_adhkar_reminders,
        interval=60,
        first=10
    )

    print("Bot running with Hadith + Quran + Dua + Interactive Islamic Quiz.")
    print(f"Bot username: @{BOT_USERNAME}")
    print(f"Hadith post time: {HADITH_POST_TIME}")
    print(f"Dua post time: {DUA_POST_TIME}")
    print(f"Quran post time: {QURAN_POST_TIME}")
    print(f"Default morning adhkar time: {DEFAULT_MORNING_ADHKAR_TIME}")
    print(f"Default evening adhkar time: {DEFAULT_EVENING_ADHKAR_TIME}")
    print(f"Default user timezone: {safe_timezone(DEFAULT_USER_TIMEZONE)}")
    print(f"WhatsApp channel enabled: {bool(WHATSAPP_CHANNEL_URL)}")
    print("Personal reminders checker: every 60 seconds")
    print("Adhkar completion + streak system: enabled")
    print("Auto channel publishing approval: enabled")
    print("Manual Islamic quiz: enabled")

    app.run_polling()


if __name__ == "__main__":
    main()