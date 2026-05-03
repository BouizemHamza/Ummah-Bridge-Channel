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

QURAN_API = "https://api.alquran.cloud/v1"
HADEETH_API = "https://hadeethenc.com/api/v1/hadeeths/one/"
LIST_API = "https://hadeethenc.com/api/v1/hadeeths/list/"
DB = "bot.db"


# ================== أدوات عامة ==================

def esc(text):
    return html.escape(str(text or ""))


def line():
    return "\n━━━━━━━━━━━━━━\n"


def now_timestamp():
    return int(time.time())


def now_readable():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_admin(user_id):
    return user_id == ADMIN_ID


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
        hadith_id TEXT,
        posted_at INTEGER NOT NULL,
        hour INTEGER NOT NULL,
        source TEXT DEFAULT 'bot'
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


def log_channel_post(post_type="hadith", hadith_id=None, source="bot"):
    ts = now_timestamp()
    hour = datetime.datetime.now().hour

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO channel_posts(post_type, hadith_id, posted_at, hour, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        (post_type, str(hadith_id or ""), ts, hour, source)
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


def last_channel_post():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT post_type, hadith_id, posted_at, hour, source
        FROM channel_posts
        ORDER BY posted_at DESC
        LIMIT 1
    """)
    row = c.fetchone()
    conn.close()
    return row


def posts_by_hour():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT hour, COUNT(*)
        FROM channel_posts
        GROUP BY hour
        ORDER BY hour ASC
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def best_posting_hour():
    rows = posts_by_hour()
    if not rows:
        return None

    best = max(rows, key=lambda x: x[1])
    return best


def format_time_from_timestamp(ts):
    if not ts:
        return "غير متوفر"
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


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


def channel_message():
    try:
        hid = get_random_hadith_id()

        if not hid:
            return "❌ تعذر جلب حديث اليوم.", None

        ar = get_hadith_by_id(hid, "ar")
        en = get_hadith_by_id(hid, "en")
        de = get_hadith_by_id(hid, "de")

        text = f"""📩 <b>رسالة اليوم | Daily Message | Tägliche Nachricht</b>

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
        return f"❌ خطأ في بناء رسالة القناة:\n<code>{esc(e)}</code>", None


# ================== القوائم ==================

def main_menu(user_id):
    buttons = [
        [InlineKeyboardButton("📖 القرآن", callback_data="quran")],
        [InlineKeyboardButton("🕊️ الأحاديث", callback_data="hadith")],
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
        [InlineKeyboardButton("📢 نشر حديث في القناة الآن", callback_data="admin_post_channel")],
        [InlineKeyboardButton("👀 معاينة رسالة القناة", callback_data="admin_preview_channel")],
        [InlineKeyboardButton("📊 لوحة الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("🕒 إحصائيات أوقات النشر", callback_data="admin_time_stats")],
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

    text, hid = channel_message()

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    log_channel_post(post_type="hadith", hadith_id=hid, source="test_command")

    await update.message.reply_text("✅ تم نشر رسالة اختبار في القناة.")


# ================== النشر التلقائي ==================

async def auto_publish_channel(context: ContextTypes.DEFAULT_TYPE):
    try:
        text, hid = channel_message()

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        log_channel_post(post_type="hadith", hadith_id=hid, source="auto_schedule")

        print("✅ Daily channel post sent.")

    except Exception as e:
        print(f"❌ Daily channel post error: {e}")


# ================== Callback Handler ==================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
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

    elif data == "admin_preview_channel":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        text, hid = channel_message()
        context.user_data["admin_preview"] = text
        context.user_data["admin_preview_hid"] = hid

        await safe_edit(
            q,
            "👀 <b>معاينة رسالة القناة:</b>\n\n" + text,
            InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 نشر هذه الرسالة", callback_data="admin_publish_preview")],
                [InlineKeyboardButton("🔄 معاينة أخرى", callback_data="admin_preview_channel")],
                [InlineKeyboardButton("⬅️ رجوع للوحة الإدارة", callback_data="admin")]
            ])
        )

    elif data == "admin_publish_preview":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        text = context.user_data.get("admin_preview")
        hid = context.user_data.get("admin_preview_hid")

        if not text:
            text, hid = channel_message()

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        log_channel_post(post_type="hadith", hadith_id=hid, source="admin_preview")

        await q.answer("تم النشر في القناة ✅", show_alert=True)

    elif data == "admin_post_channel":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        text, hid = channel_message()

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        log_channel_post(post_type="hadith", hadith_id=hid, source="admin_manual")

        await safe_edit(
            q,
            "✅ <b>تم نشر حديث في القناة.</b>",
            admin_menu()
        )

    elif data == "admin_stats":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        total_posts = channel_posts_count()
        last_post = last_channel_post()

        if last_post:
            post_type, hadith_id, posted_at, hour, source = last_post
            last_post_text = (
                f"🕒 <b>آخر نشر:</b> {esc(format_time_from_timestamp(posted_at))}\n"
                f"🔢 <b>آخر حديث ID:</b> <code>{esc(hadith_id)}</code>\n"
                f"⚙️ <b>طريقة النشر:</b> {esc(source)}"
            )
        else:
            last_post_text = "🕒 <b>آخر نشر:</b> لا يوجد بعد"

        best = best_posting_hour()
        if best:
            best_hour, best_count = best
            best_text = f"⭐ <b>أكثر وقت نُشر فيه:</b> الساعة {best_hour}:00 بعدد {best_count} منشورات"
        else:
            best_text = "⭐ <b>أفضل وقت:</b> لا توجد بيانات كافية بعد"

        await safe_edit(
            q,
            f"""📊 <b>لوحة إحصائيات Ummah Bridge</b>

👥 <b>عدد المستخدمين:</b> {users_count()}
❤️ <b>عدد الأحاديث المحفوظة:</b> {saved_count()}
📢 <b>عدد منشورات القناة:</b> {total_posts}

{last_post_text}

{best_text}

🌐 <b>القناة:</b> {esc(CHANNEL_ID)}
""",
            admin_menu()
        )

    elif data == "admin_time_stats":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        rows = posts_by_hour()

        if not rows:
            text = "🕒 لا توجد إحصائيات نشر بعد."
        else:
            text = "🕒 <b>إحصائيات أوقات النشر</b>\n\n"
            for hour, count in rows:
                text += f"• الساعة <b>{hour}:00</b> — عدد المنشورات: <b>{count}</b>\n"

            best = best_posting_hour()
            if best:
                best_hour, best_count = best
                text += f"\n⭐ <b>اقتراح حالي:</b> الساعة <b>{best_hour}:00</b> لأنها الأكثر استخدامًا في سجل النشر."

        await safe_edit(q, text, admin_back())

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

        log_channel_post(post_type="custom", hadith_id="", source="admin_custom")

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

    publish_times = [
        datetime.time(hour=9, minute=0, second=0),
        datetime.time(hour=15, minute=0, second=0),
        datetime.time(hour=21, minute=0, second=0),
    ]

    for publish_time in publish_times:
        app.job_queue.run_daily(
            auto_publish_channel,
            time=publish_time
        )

    print("Bot running with advanced admin dashboard...")
    app.run_polling()


if __name__ == "__main__":
    main()