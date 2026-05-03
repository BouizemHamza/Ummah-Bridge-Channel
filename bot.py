import os
import random
import sqlite3
import requests
import html
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
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

QURAN_API = "https://api.alquran.cloud/v1"
HADEETH_API = "https://hadeethenc.com/api/v1/hadeeths/one/"
LIST_API = "https://hadeethenc.com/api/v1/hadeeths/list/"
DB = "bot.db"


def esc(text):
    return html.escape(str(text or ""))


def line():
    return "\n━━━━━━━━━━━━━━\n"


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS saved(
        user_id INTEGER,
        text TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'ar'
    )
    """)

    conn.commit()
    conn.close()


def add_user(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
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


def random_hadith(lang="ar"):
    try:
        res = requests.get(
            LIST_API,
            params={
                "language": "ar",
                "category_id": 1,
                "page": random.randint(1, 5),
                "per_page": 10
            },
            timeout=15
        ).json()

        hid = random.choice(res["data"])["id"]

        h = requests.get(
            HADEETH_API,
            params={"language": lang, "id": hid},
            timeout=15
        ).json()

        return f"""🕊️ <b>حديث نبوي</b>{line()}
{esc(h.get("hadeeth", ""))}
{line()}
📚 <b>المصدر:</b> {esc(h.get("attribution", ""))}
✅ <b>الدرجة:</b> {esc(h.get("grade", ""))}
🔢 <b>ID:</b> <code>{esc(hid)}</code>
"""

    except Exception as e:
        return f"❌ خطأ في جلب الحديث:\n<code>{esc(e)}</code>"


def channel_message():
    try:
        res = requests.get(
            LIST_API,
            params={
                "language": "ar",
                "category_id": 1,
                "page": random.randint(1, 5),
                "per_page": 10
            },
            timeout=15
        ).json()

        hid = random.choice(res["data"])["id"]

        ar = requests.get(HADEETH_API, params={"language": "ar", "id": hid}, timeout=15).json()
        en = requests.get(HADEETH_API, params={"language": "en", "id": hid}, timeout=15).json()
        de = requests.get(HADEETH_API, params={"language": "de", "id": hid}, timeout=15).json()

        return f"""📩 <b>رسالة اليوم | Daily Message | Tägliche Nachricht</b>

🕊️ <b>نفس الحديث بثلاث لغات</b>
<i>Same Hadith in Three Languages</i>

━━━━━━━━━━━━━━

🇸🇦 <b>العربية</b>

{esc(ar.get("hadeeth", ""))}

━━━━━━━━━━━━━━

🇬🇧 <b>English</b>

{esc(en.get("hadeeth", ""))}

━━━━━━━━━━━━━━

🇩🇪 <b>Deutsch</b>

{esc(de.get("hadeeth", ""))}

━━━━━━━━━━━━━━

📚 <b>المصدر:</b> {esc(ar.get("attribution", ""))}
✅ <b>الدرجة:</b> {esc(ar.get("grade", ""))}
🔢 <b>HadeethEnc ID:</b> <code>{esc(hid)}</code>

🌍 {esc(CHANNEL_ID)}
"""
    except Exception as e:
        return f"❌ خطأ في بناء رسالة القناة:\n<code>{esc(e)}</code>"


def is_admin(user_id):
    return user_id == ADMIN_ID


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
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("✍️ إرسال رسالة مخصصة للقناة", callback_data="admin_custom_post")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


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

    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر خاص بالمشرف فقط.")
        return

    await update.message.reply_text(
        "🛠️ <b>لوحة الإدارة</b>\n\nاختر إجراء:",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


async def auto_publish_channel(context: ContextTypes.DEFAULT_TYPE):
    try:
        text = channel_message()
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        print("✅ Daily channel post sent.")
    except Exception as e:
        print(f"❌ Daily channel post error: {e}")


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
            res = requests.get(f"{QURAN_API}/surah/1/quran-uthmani", timeout=15).json()
            ayat = res["data"]["ayahs"]

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

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO saved VALUES (?,?)", (user_id, h))
        conn.commit()
        conn.close()

        await q.answer("تم الحفظ ✅", show_alert=True)

    elif data == "saved":
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT text FROM saved WHERE user_id=? LIMIT 5", (user_id,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            text = "❤️ لا توجد محفوظات بعد."
        else:
            text = "❤️ <b>محفوظاتك:</b>\n\n"
            for i, row in enumerate(rows, 1):
                text += f"<b>#{i}</b>\n{row[0][:600]}\n\n━━━━━━━━━━━━━━\n\n"

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

        text = channel_message()
        context.user_data["admin_preview"] = text

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
        if not text:
            text = channel_message()

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        await q.answer("تم النشر في القناة ✅", show_alert=True)

    elif data == "admin_post_channel":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        text = channel_message()

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        await safe_edit(
            q,
            "✅ <b>تم نشر حديث في القناة.</b>",
            admin_menu()
        )

    elif data == "admin_stats":
        if not is_admin(user_id):
            await q.answer("غير مسموح", show_alert=True)
            return

        await safe_edit(
            q,
            f"""📊 <b>إحصائيات المشروع</b>

👥 عدد المستخدمين: <b>{users_count()}</b>
❤️ عدد الأحاديث المحفوظة: <b>{saved_count()}</b>
🌐 القناة: {esc(CHANNEL_ID)}
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
            "✍️ <b>أرسل الآن الرسالة التي تريد نشرها في القناة.</b>\n\nسيتم نشر النص كما هو.",
            back()
        )


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

        await update.message.reply_text(
            "✅ تم نشر الرسالة المخصصة في القناة.",
            reply_markup=admin_menu()
        )


async def test_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر خاص بالمشرف فقط.")
        return

    text = channel_message()

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    await update.message.reply_text("✅ تم نشر رسالة اختبار في القناة.")


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
        auto_publish_channel,
        time=datetime.time(hour=9, minute=0, second=0)
    )

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()