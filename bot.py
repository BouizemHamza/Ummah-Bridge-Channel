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

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@UMMAHBRIDGE")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

HADITH_POST_TIME = os.environ.get("HADITH_POST_TIME", "09:00")
QURAN_POST_TIME = os.environ.get("QURAN_POST_TIME", "15:00")
MIXED_POST_TIME = os.environ.get("MIXED_POST_TIME", "21:00")

MORNING_ADHKAR_TIME = os.environ.get("MORNING_ADHKAR_TIME", "06:00")
EVENING_ADHKAR_TIME = os.environ.get("EVENING_ADHKAR_TIME", "18:00")

AUTO_POST_MIN_GAP_HOURS = int(os.environ.get("AUTO_POST_MIN_GAP_HOURS", "6"))

QURAN_API = "https://api.alquran.cloud/v1"
HADEETH_API = "https://hadeethenc.com/api/v1/hadeeths/one/"
LIST_API = "https://hadeethenc.com/api/v1/hadeeths/list/"
DB = "bot.db"


# ================== الأذكار ==================

MORNING_ADHKAR = [
    {
        "text": "أَصْـبَحْنا وَأَصْـبَحَ المُـلْكُ لله، والحَمْدُ لله، لا إلهَ إلاّ اللهُ وحدَهُ لا شريكَ له، لهُ المُـلْكُ ولهُ الحَمْـد، وهوَ على كلّ شيءٍ قدير.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح"
    },
    {
        "text": "اللّهـمَّ بِكَ أَصْـبَحْنا، وَبِكَ أَمْسَيْـنا، وَبِكَ نَحْـيا، وَبِكَ نَمـوتُ، وَإِلَيْكَ النُّـشور.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح"
    },
    {
        "text": "اللّهـمَّ أَنْتَ رَبِّـي لا إلهَ إلاّ أَنْتَ، خَلَقْتَنـي وأنا عَبْـدُك، وأنا على عَهْـدِكَ ووَعْـدِكَ ما استطعتُ، أعوذُ بكَ مِنْ شَرِّ ما صَنَعْت، أبوءُ لكَ بنِعْمَتِكَ عليَّ، وأبوءُ بذَنْـبي، فاغْفِـرْ لي، فإنّهُ لا يَغْفِـرُ الذُّنوبَ إلاّ أنت.",
        "repeat": "مرة واحدة",
        "source": "سيد الاستغفار"
    },
    {
        "text": "رَضيتُ باللهِ ربًّا، وبالإسلامِ دينًا، وبمحمّدٍ ﷺ نبيًّا.",
        "repeat": "ثلاث مرات",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ إنّي أَصْبَحْتُ أُشْهِدُكَ، وأُشْهِدُ حَمَلَةَ عَرْشِكَ، ومَلائِكَتَكَ، وجميعَ خَلْقِكَ، أنّكَ أنتَ اللهُ لا إلهَ إلاّ أنتَ وحدَكَ لا شريكَ لك، وأنّ محمّدًا عبدُكَ ورسولُك.",
        "repeat": "أربع مرات",
        "source": "من أذكار الصباح"
    },
    {
        "text": "اللّهـمَّ ما أَصْبَحَ بي مِنْ نِعْمَةٍ أو بأَحَدٍ مِنْ خَلْقِكَ، فَمِنْكَ وحدَكَ لا شريكَ لك، فَلَكَ الحمدُ ولكَ الشُّكر.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح"
    },
    {
        "text": "حَسْبِيَ اللهُ لا إلهَ إلاّ هو، عليهِ توكّلتُ، وهوَ ربُّ العرشِ العظيم.",
        "repeat": "سبع مرات",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "بِسْمِ اللهِ الذي لا يَضُرُّ مع اسمِهِ شيءٌ في الأرضِ ولا في السماءِ، وهوَ السميعُ العليم.",
        "repeat": "ثلاث مرات",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ عافِني في بَدَني، اللّهـمَّ عافِني في سَمْعي، اللّهـمَّ عافِني في بَصَري، لا إلهَ إلاّ أنت.",
        "repeat": "ثلاث مرات",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ إنّي أعوذُ بكَ مِنَ الكُفْرِ والفَقْر، وأعوذُ بكَ مِنْ عذابِ القَبْر، لا إلهَ إلاّ أنت.",
        "repeat": "ثلاث مرات",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ إنّي أسألُكَ العفوَ والعافيةَ في الدنيا والآخرة.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ إنّي أسألُكَ العفوَ والعافيةَ في ديني ودنيايَ وأهلي ومالي.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ استُرْ عوراتي، وآمِنْ رَوْعاتي.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ احفظني مِنْ بينِ يديَّ، ومِنْ خَلْفي، وعن يميني، وعن شمالي، ومِنْ فوقي، وأعوذُ بعظمتِكَ أن أُغتالَ مِنْ تحتي.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "يا حيُّ يا قيّومُ، برحمتِكَ أستغيث، أصلِحْ لي شأني كلَّه، ولا تَكِلْني إلى نفسي طَرْفَةَ عين.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "أَصْبَحْنا على فِطْرَةِ الإسلام، وعلى كلمةِ الإخلاص، وعلى دينِ نبيّنا محمدٍ ﷺ، وعلى مِلّةِ أبينا إبراهيمَ حنيفًا مسلمًا وما كانَ مِنَ المشركين.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح"
    },
    {
        "text": "سُبْحانَ اللهِ وبحمدِه.",
        "repeat": "مائة مرة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "لا إلهَ إلاّ اللهُ وحدَهُ لا شريكَ له، لهُ الملكُ ولهُ الحمدُ، وهوَ على كلّ شيءٍ قدير.",
        "repeat": "عشر مرات أو مائة مرة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "أستغفرُ اللهَ وأتوبُ إليه.",
        "repeat": "مائة مرة",
        "source": "من الأذكار"
    },
    {
        "text": "اللّهـمَّ صلِّ وسلّمْ على نبيّنا محمد.",
        "repeat": "عشر مرات",
        "source": "من الأذكار المشروعة"
    },
]

EVENING_ADHKAR = [
    {
        "text": "أَمْسَيْنا وأَمْسَى المُـلْكُ لله، والحَمْدُ لله، لا إلهَ إلاّ اللهُ وحدَهُ لا شريكَ له، لهُ المُـلْكُ ولهُ الحَمْـد، وهوَ على كلّ شيءٍ قدير.",
        "repeat": "مرة واحدة",
        "source": "من أذكار المساء"
    },
    {
        "text": "اللّهـمَّ بِكَ أَمْسَيْنا، وبِكَ أَصْبَحْنا، وبِكَ نَحْيا، وبِكَ نَموتُ، وإليكَ المصير.",
        "repeat": "مرة واحدة",
        "source": "من أذكار المساء"
    },
    {
        "text": "اللّهـمَّ أَنْتَ رَبِّـي لا إلهَ إلاّ أَنْتَ، خَلَقْتَنـي وأنا عَبْـدُك، وأنا على عَهْـدِكَ ووَعْـدِكَ ما استطعتُ، أعوذُ بكَ مِنْ شَرِّ ما صَنَعْت، أبوءُ لكَ بنِعْمَتِكَ عليَّ، وأبوءُ بذَنْـبي، فاغْفِـرْ لي، فإنّهُ لا يَغْفِـرُ الذُّنوبَ إلاّ أنت.",
        "repeat": "مرة واحدة",
        "source": "سيد الاستغفار"
    },
    {
        "text": "رَضيتُ باللهِ ربًّا، وبالإسلامِ دينًا، وبمحمّدٍ ﷺ نبيًّا.",
        "repeat": "ثلاث مرات",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ إنّي أَمْسَيْتُ أُشْهِدُكَ، وأُشْهِدُ حَمَلَةَ عَرْشِكَ، ومَلائِكَتَكَ، وجميعَ خَلْقِكَ، أنّكَ أنتَ اللهُ لا إلهَ إلاّ أنتَ وحدَكَ لا شريكَ لك، وأنّ محمّدًا عبدُكَ ورسولُك.",
        "repeat": "أربع مرات",
        "source": "من أذكار المساء"
    },
    {
        "text": "اللّهـمَّ ما أَمْسَى بي مِنْ نِعْمَةٍ أو بأَحَدٍ مِنْ خَلْقِكَ، فَمِنْكَ وحدَكَ لا شريكَ لك، فَلَكَ الحمدُ ولكَ الشُّكر.",
        "repeat": "مرة واحدة",
        "source": "من أذكار المساء"
    },
    {
        "text": "حَسْبِيَ اللهُ لا إلهَ إلاّ هو، عليهِ توكّلتُ، وهوَ ربُّ العرشِ العظيم.",
        "repeat": "سبع مرات",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "بِسْمِ اللهِ الذي لا يَضُرُّ مع اسمِهِ شيءٌ في الأرضِ ولا في السماءِ، وهوَ السميعُ العليم.",
        "repeat": "ثلاث مرات",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ عافِني في بَدَني، اللّهـمَّ عافِني في سَمْعي، اللّهـمَّ عافِني في بَصَري، لا إلهَ إلاّ أنت.",
        "repeat": "ثلاث مرات",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ إنّي أعوذُ بكَ مِنَ الكُفْرِ والفَقْر، وأعوذُ بكَ مِنْ عذابِ القَبْر، لا إلهَ إلاّ أنت.",
        "repeat": "ثلاث مرات",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ إنّي أسألُكَ العفوَ والعافيةَ في الدنيا والآخرة.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ إنّي أسألُكَ العفوَ والعافيةَ في ديني ودنيايَ وأهلي ومالي.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ استُرْ عوراتي، وآمِنْ رَوْعاتي.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "اللّهـمَّ احفظني مِنْ بينِ يديَّ، ومِنْ خَلْفي، وعن يميني، وعن شمالي، ومِنْ فوقي، وأعوذُ بعظمتِكَ أن أُغتالَ مِنْ تحتي.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "يا حيُّ يا قيّومُ، برحمتِكَ أستغيث، أصلِحْ لي شأني كلَّه، ولا تَكِلْني إلى نفسي طَرْفَةَ عين.",
        "repeat": "مرة واحدة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "أَمْسَيْنا على فِطْرَةِ الإسلام، وعلى كلمةِ الإخلاص، وعلى دينِ نبيّنا محمدٍ ﷺ، وعلى مِلّةِ أبينا إبراهيمَ حنيفًا مسلمًا وما كانَ مِنَ المشركين.",
        "repeat": "مرة واحدة",
        "source": "من أذكار المساء"
    },
    {
        "text": "سُبْحانَ اللهِ وبحمدِه.",
        "repeat": "مائة مرة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "لا إلهَ إلاّ اللهُ وحدَهُ لا شريكَ له، لهُ الملكُ ولهُ الحمدُ، وهوَ على كلّ شيءٍ قدير.",
        "repeat": "عشر مرات أو مائة مرة",
        "source": "من أذكار الصباح والمساء"
    },
    {
        "text": "أستغفرُ اللهَ وأتوبُ إليه.",
        "repeat": "مائة مرة",
        "source": "من الأذكار"
    },
    {
        "text": "اللّهـمَّ صلِّ وسلّمْ على نبيّنا محمد.",
        "repeat": "عشر مرات",
        "source": "من الأذكار المشروعة"
    },
]


# ================== أدوات عامة ==================

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
            raise ValueError("Hour must be between 0 and 23")

        if minute < 0 or minute > 59:
            raise ValueError("Minute must be between 0 and 59")

        return datetime.time(hour=hour, minute=minute, second=0)

    except Exception:
        fallback_hour, fallback_minute = fallback.split(":")
        return datetime.time(
            hour=int(fallback_hour),
            minute=int(fallback_minute),
            second=0
        )


# ================== قاعدة البيانات ==================

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS saved(
        user_id INTEGER,
        text TEXT,
        created_at INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'ar',
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS skipped_posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_type TEXT NOT NULL,
        reason TEXT NOT NULL,
        skipped_at INTEGER NOT NULL,
        hour INTEGER NOT NULL,
        source TEXT DEFAULT 'auto'
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

    conn.commit()
    conn.close()


def add_user(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO users(user_id, created_at) VALUES(?, ?)",
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


def saved_count():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM saved")
    count = c.fetchone()[0]
    conn.close()
    return count


def save_hadith(user_id, text):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO saved(user_id, text, created_at) VALUES (?, ?, ?)",
        (user_id, text, now_timestamp())
    )
    conn.commit()
    conn.close()


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
    c.execute(
        "SELECT morning, evening FROM adhkar_reminders WHERE user_id=?",
        (user_id,)
    )
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
    ts = now_timestamp()
    hour = datetime.datetime.now().hour

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO channel_posts(post_type, item_id, posted_at, hour, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        (post_type, str(item_id or ""), ts, hour, source)
    )
    conn.commit()
    conn.close()


def log_skipped_post(post_type, reason, source="auto_duplicate_protection"):
    ts = now_timestamp()
    hour = datetime.datetime.now().hour

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO skipped_posts(post_type, reason, skipped_at, hour, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        (post_type, reason, ts, hour, source)
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


def skipped_posts_count():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM skipped_posts")
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


def last_auto_post_by_type(post_type):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT post_type, item_id, posted_at, hour, source
        FROM channel_posts
        WHERE post_type = ?
          AND source LIKE 'auto_%'
        ORDER BY posted_at DESC
        LIMIT 1
    """, (post_type,))
    row = c.fetchone()
    conn.close()
    return row


def was_auto_posted_recently(post_type, min_gap_hours):
    last_post = last_auto_post_by_type(post_type)

    if not last_post:
        return False, None

    _, item_id, posted_at, hour, source = last_post
    seconds_gap = min_gap_hours * 60 * 60
    elapsed = now_timestamp() - int(posted_at)

    if elapsed < seconds_gap:
        return True, last_post

    return False, last_post


# ================== HadeethEnc API ==================

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

    data = response.json()
    hadiths = data.get("data", [])

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
        "attribution": data.get("attribution", ""),
        "grade": data.get("grade", ""),
        "reference": data.get("reference", "")
    }


def random_hadith(lang="ar"):
    try:
        hid = get_random_hadith_id()

        if not hid:
            return "❌ لم يتم العثور على حديث."

        h = get_hadith_by_id(hid, lang)

        return f"""🕊️ <b>حديث نبوي</b>{line()}
{esc(h.get("text", ""))}
{line()}
📚 <b>المصدر:</b> {esc(h.get("attribution", "HadeethEnc"))}
✅ <b>الدرجة:</b> {esc(h.get("grade", ""))}
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

{esc(ar.get("text", ""))}

━━━━━━━━━━━━━━

🇬🇧 <b>English</b>

{esc(en.get("text", ""))}

━━━━━━━━━━━━━━

🇩🇪 <b>Deutsch</b>

{esc(de.get("text", ""))}

━━━━━━━━━━━━━━

📚 <b>المصدر:</b> {esc(ar.get("attribution", "HadeethEnc"))}
✅ <b>الدرجة:</b> {esc(ar.get("grade", ""))}
🔢 <b>HadeethEnc ID:</b> <code>{esc(hid)}</code>

🌍 {esc(CHANNEL_ID)}
"""
        return text, hid

    except Exception as e:
        return f"❌ خطأ في بناء رسالة الحديث:\n<code>{esc(e)}</code>", None


# ================== Quran API ==================

def get_random_ayah_number():
    return random.randint(1, 6236)


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
        "global_number": data.get("number", number),
        "edition": data.get("edition", {}).get("englishName", edition)
    }


def quran_channel_message():
    try:
        number = get_random_ayah_number()

        ar = get_ayah_by_number(number, "quran-uthmani")
        en = get_ayah_by_number(number, "en.sahih")
        de = get_ayah_by_number(number, "de.aburida")

        surah_label = f"{ar['surah_name']} | {en['surah_english']}"
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

📖 <b>السورة:</b> {esc(surah_label)}
🔢 <b>الآية:</b> <code>{esc(ayah_ref)}</code>
🌐 <b>المصدر التقني:</b> AlQuran Cloud API

🌍 {esc(CHANNEL_ID)}
"""
        return text, ayah_ref

    except Exception as e:
        return f"❌ خطأ في بناء رسالة الآية:\n<code>{esc(e)}</code>", None


def mixed_channel_message():
    try:
        quran_text, ayah_ref = quran_channel_message()
        hadith_text, hid = hadith_channel_message()

        text = f"""📩 <b>رسالة إيمانية | Faith Reminder</b>

━━━━━━━━━━━━━━

{quran_text}

━━━━━━━━━━━━━━

{hadith_text}
"""
        item_id = f"ayah:{ayah_ref}|hadith:{hid}"
        return text, item_id

    except Exception as e:
        return f"❌ خطأ في بناء الرسالة المختلطة:\n<code>{esc(e)}</code>", None


# ================== الأذكار UI ==================

def adhkar_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌅 أذكار الصباح", callback_data="adhkar_morning_0")],
        [InlineKeyboardButton("🌙 أذكار المساء", callback_data="adhkar_evening_0")],
        [InlineKeyboardButton("⏰ تذكير الأذكار", callback_data="adhkar_reminders")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
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


def render_adhkar(kind, index):
    adhkar_list = MORNING_ADHKAR if kind == "morning" else EVENING_ADHKAR
    title = "🌅 أذكار الصباح" if kind == "morning" else "🌙 أذكار المساء"

    total = len(adhkar_list)

    if index < 0:
        index = 0

    if index >= total:
        index = total - 1

    item = adhkar_list[index]

    text = f"""{title}

<b>الذكر {index + 1}/{total}</b>
{line()}
{esc(item["text"])}
{line()}
🔁 <b>التكرار:</b> {esc(item["repeat"])}
📚 <b>المصدر:</b> {esc(item["source"])}
"""

    return text, adhkar_navigation(kind, index, total)


# ================== القوائم العامة ==================

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


def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕊️ نشر حديث الآن", callback_data="admin_post_hadith")],
        [InlineKeyboardButton("📖 نشر آية الآن", callback_data="admin_post_quran")],
        [InlineKeyboardButton("📩 نشر آية + حديث", callback_data="admin_post_mixed")],
        [InlineKeyboardButton("👀 معاينة حديث", callback_data="admin_preview_hadith")],
        [InlineKeyboardButton("👀 معاينة آية", callback_data="admin_preview_quran")],
        [InlineKeyboardButton("📊 لوحة الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("🛡️ حالة الحماية من التكرار", callback_data="admin_duplicate_status")],
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


# ================== إرسال آمن ==================

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
    log_channel_post(post_type=post_type, item_id=item_id, source=source)


async def send_auto_channel_message(context, post_type, text_builder, source):
    recently_posted, last_post = was_auto_posted_recently(
        post_type=post_type,
        min_gap_hours=AUTO_POST_MIN_GAP_HOURS
    )

    if recently_posted:
        reason = f"Skipped duplicate auto post. Minimum gap is {AUTO_POST_MIN_GAP_HOURS} hours."
        log_skipped_post(post_type=post_type, reason=reason, source=source)
        print(f"🛡️ Skipped {post_type}: {reason}")
        return False

    text, item_id = text_builder()

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    log_channel_post(post_type=post_type, item_id=item_id, source=source)
    return True


# ================== الأوامر ==================

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
    add_user(user_id)

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


# ================== النشر التلقائي ==================

async def auto_publish_hadith(context: ContextTypes.DEFAULT_TYPE):
    try:
        sent = await send_auto_channel_message(
            context=context,
            post_type="hadith",
            text_builder=hadith_channel_message,
            source="auto_hadith"
        )

        if sent:
            print("✅ Scheduled hadith post sent.")

    except Exception as e:
        print(f"❌ Scheduled hadith post error: {e}")


async def auto_publish_quran(context: ContextTypes.DEFAULT_TYPE):
    try:
        sent = await send_auto_channel_message(
            context=context,
            post_type="quran",
            text_builder=quran_channel_message,
            source="auto_quran"
        )

        if sent:
            print("✅ Scheduled quran post sent.")

    except Exception as e:
        print(f"❌ Scheduled quran post error: {e}")


async def auto_publish_mixed(context: ContextTypes.DEFAULT_TYPE):
    try:
        sent = await send_auto_channel_message(
            context=context,
            post_type="mixed",
            text_builder=mixed_channel_message,
            source="auto_mixed"
        )

        if sent:
            print("✅ Scheduled mixed post sent.")

    except Exception as e:
        print(f"❌ Scheduled mixed post error: {e}")


# ================== تذكير الأذكار ==================

async def send_morning_adhkar_reminders(context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_adhkar_subscribers("morning")

    for user_id, chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🌅 <b>تذكير أذكار الصباح</b>\n\nابدأ بقراءة أذكار الصباح الآن.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌅 ابدأ أذكار الصباح", callback_data="adhkar_morning_0")]
                ]),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Morning adhkar reminder error for {user_id}: {e}")


async def send_evening_adhkar_reminders(context: ContextTypes.DEFAULT_TYPE):
    subscribers = get_adhkar_subscribers("evening")

    for user_id, chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🌙 <b>تذكير أذكار المساء</b>\n\nابدأ بقراءة أذكار المساء الآن.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌙 ابدأ أذكار المساء", callback_data="adhkar_evening_0")]
                ]),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Evening adhkar reminder error for {user_id}: {e}")


# ================== Callback Handler ==================

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
        rows = get_saved_hadiths(user_id, limit=5)

        if not rows:
            text = "❤️ لا توجد محفوظات بعد."
        else:
            text = "❤️ <b>محفوظاتك:</b>\n\n"
            for i, row in enumerate(rows, 1):
                saved_text = row[0]
                created_at = row[1]
                text += (
                    f"<b>#{i}</b>\n"
                    f"🕒 {esc(format_time_from_timestamp(created_at))}\n"
                    f"{esc(saved_text[:500])}\n\n"
                    f"━━━━━━━━━━━━━━\n\n"
                )

        await safe_edit(q, text, back())

    elif data == "adhkar_menu":
        await safe_edit(
            q,
            "🤲 <b>قسم الأذكار</b>\n\nاختر ما تريد قراءته:",
            adhkar_main_menu()
        )

    elif data.startswith("adhkar_morning_"):
        index = int(data.split("_")[-1])
        text, markup = render_adhkar("morning", index)
        await safe_edit(q, text, markup)

    elif data.startswith("adhkar_evening_"):
        index = int(data.split("_")[-1])
        text, markup = render_adhkar("evening", index)
        await safe_edit(q, text, markup)

    elif data == "adhkar_done_morning":
        await safe_edit(
            q,
            "✅ <b>أحسنت.</b>\n\nانتهيت من أذكار الصباح.\nنسأل الله أن يحفظك ويبارك يومك.",
            adhkar_main_menu()
        )

    elif data == "adhkar_done_evening":
        await safe_edit(
            q,
            "✅ <b>أحسنت.</b>\n\nانتهيت من أذكار المساء.\nنسأل الله أن يحفظك في ليلتك.",
            adhkar_main_menu()
        )

    elif data == "adhkar_reminders":
        morning, evening = get_adhkar_reminder_status(user_id)

        text = f"""⏰ <b>تذكير الأذكار</b>

🌅 تذكير الصباح: {"✅ مفعل" if morning else "❌ غير مفعل"}
🌙 تذكير المساء: {"✅ مفعل" if evening else "❌ غير مفعل"}

🕘 وقت الصباح الحالي: <code>{esc(MORNING_ADHKAR_TIME)}</code>
🕕 وقت المساء الحالي: <code>{esc(EVENING_ADHKAR_TIME)}</code>
"""

        await safe_edit(q, text, adhkar_reminder_menu(user_id))

    elif data == "adhkar_toggle_morning":
        morning, evening = get_adhkar_reminder_status(user_id)
        new_value = 0 if morning else 1
        set_adhkar_reminder(user_id, chat_id, "morning", new_value)

        await q.answer("تم تحديث تذكير الصباح ✅", show_alert=True)

        morning, evening = get_adhkar_reminder_status(user_id)
        text = f"""⏰ <b>تذكير الأذكار</b>

🌅 تذكير الصباح: {"✅ مفعل" if morning else "❌ غير مفعل"}
🌙 تذكير المساء: {"✅ مفعل" if evening else "❌ غير مفعل"}
"""
        await safe_edit(q, text, adhkar_reminder_menu(user_id))

    elif data == "adhkar_toggle_evening":
        morning, evening = get_adhkar_reminder_status(user_id)
        new_value = 0 if evening else 1
        set_adhkar_reminder(user_id, chat_id, "evening", new_value)

        await q.answer("تم تحديث تذكير المساء ✅", show_alert=True)

        morning, evening = get_adhkar_reminder_status(user_id)
        text = f"""⏰ <b>تذكير الأذكار</b>

🌅 تذكير الصباح: {"✅ مفعل" if morning else "❌ غير مفعل"}
🌙 تذكير المساء: {"✅ مفعل" if evening else "❌ غير مفعل"}
"""
        await safe_edit(q, text, adhkar_reminder_menu(user_id))

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

🤲 يحتوي البوت على أذكار الصباح والمساء.

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

🕘 <b>أوقات النشر:</b>
• حديث: <code>{esc(HADITH_POST_TIME)}</code>
• آية: <code>{esc(QURAN_POST_TIME)}</code>
• آية + حديث: <code>{esc(MIXED_POST_TIME)}</code>

⏰ <b>أوقات الأذكار:</b>
• صباح: <code>{esc(MORNING_ADHKAR_TIME)}</code>
• مساء: <code>{esc(EVENING_ADHKAR_TIME)}</code>

🌐 <b>القناة:</b> {esc(CHANNEL_ID)}
""",
            admin_menu()
        )

    elif data == "admin_duplicate_status":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        await safe_edit(
            q,
            f"""🛡️ <b>حالة الحماية من التكرار</b>

مدة الحماية الحالية:
<code>{AUTO_POST_MIN_GAP_HOURS} ساعات</code>

هذه الحماية تمنع النشر التلقائي المتكرر لنفس نوع المنشور خلال المدة المحددة.
""",
            admin_back()
        )

    elif data == "admin_custom_post":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        context.user_data["waiting_custom_post"] = True

        await safe_edit(
            q,
            "✍️ <b>أرسل الآن الرسالة التي تريد نشرها في القناة.</b>\n\nسيتم نشر النص كما هو.",
            admin_back()
        )


# ================== رسائل النص ==================

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

        log_channel_post(post_type="custom", item_id="", source="admin_custom")

        await update.message.reply_text(
            "✅ تم نشر الرسالة المخصصة في القناة.",
            reply_markup=admin_menu()
        )


# ================== التشغيل ==================

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

    print("Bot running with Adhkar feature...")
    print(f"Morning adhkar reminder: {MORNING_ADHKAR_TIME}")
    print(f"Evening adhkar reminder: {EVENING_ADHKAR_TIME}")

    app.run_polling()


if __name__ == "__main__":
    main()