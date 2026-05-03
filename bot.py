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
HADEETH_API = "https://hadeethenc.com/api/v1/hadeeths/one/"
LIST_API = "https://hadeethenc.com/api/v1/hadeeths/list/"

DB = "bot.db"


# ================== أدوات ==================
def esc(text):
    return html.escape(str(text or ""))


def line():
    return "\n━━━━━━━━━━━━━━\n"


# ================== قاعدة البيانات ==================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS saved(
        user_id INTEGER,
        text TEXT
    )
    """)

    conn.commit()
    conn.close()


# ================== API ==================
def random_hadith(lang):
    try:
        res = requests.get(LIST_API, params={
            "language": "ar",
            "page": random.randint(1, 5),
            "per_page": 10
        }).json()

        hid = random.choice(res["data"])["id"]

        h = requests.get(HADEETH_API, params={
            "language": lang,
            "id": hid
        }).json()

        return f"""🕊️ <b>Hadith</b>{line()}
{esc(h.get("hadeeth",""))}
{line()}
📚 {esc(h.get("attribution",""))}
✅ {esc(h.get("grade",""))}
"""

    except:
        return "❌ Error loading hadith"


# ================== أزرار ==================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 القرآن", callback_data="quran")],
        [InlineKeyboardButton("🕊️ الأحاديث", callback_data="hadith")],
        [InlineKeyboardButton("📩 الرسالة اليومية", callback_data="daily")],
        [InlineKeyboardButton("ℹ️ عن المشروع", callback_data="about")],
        [InlineKeyboardButton("🌐 القناة الرسمية", url="https://t.me/UMMAHBRIDGE")]
    ])


def hadith_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 حديث عشوائي", callback_data="random")],
        [InlineKeyboardButton("❤️ حفظ الحديث", callback_data="save")],
        [InlineKeyboardButton("📚 محفوظاتي", callback_data="saved")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


# ================== Handlers ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌉 <b>مرحبًا بك في Ummah Bridge</b>\n\nاختر:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data

    # ================== الرئيسية ==================
    if data == "home":
        await q.edit_message_text(
            "🌉 <b>Ummah Bridge</b>",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )

    # ================== القرآن ==================
    elif data == "quran":
        res = requests.get(f"{QURAN_API}/surah/1/quran-uthmani").json()
        ayat = res["data"]["ayahs"]

        text = "📖 <b>سورة الفاتحة</b>" + line()

        for a in ayat:
            text += f"{a['text']}\n"

        await q.edit_message_text(text, reply_markup=back(), parse_mode="HTML")

    # ================== الأحاديث ==================
    elif data == "hadith":
        await q.edit_message_text(
            "🕊️ <b>قسم الأحاديث</b>",
            reply_markup=hadith_menu(),
            parse_mode="HTML"
        )

    elif data == "random":
        h = random_hadith("ar")
        context.user_data["last"] = h

        await q.edit_message_text(
            h,
            reply_markup=hadith_menu(),
            parse_mode="HTML"
        )

    elif data == "save":
        h = context.user_data.get("last")

        if not h:
            await q.answer("لا يوجد حديث", show_alert=True)
            return

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO saved VALUES (?,?)", (q.from_user.id, h))
        conn.commit()
        conn.close()

        await q.answer("تم الحفظ ✅")

    elif data == "saved":
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT text FROM saved WHERE user_id=?", (q.from_user.id,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            text = "❌ لا يوجد محفوظات"
        else:
            text = "❤️ <b>محفوظاتك:</b>\n\n"
            for r in rows[:5]:
                text += r[0][:300] + "\n\n"

        await q.edit_message_text(text, reply_markup=back(), parse_mode="HTML")

    # ================== اليومية ==================
    elif data == "daily":
        await q.edit_message_text(
            "📩 <b>الميزة قادمة قريبًا...</b>",
            reply_markup=back(),
            parse_mode="HTML"
        )

    # ================== عن المشروع ==================
    elif data == "about":
        await q.edit_message_text(
            """ℹ️ <b>Ummah Bridge</b>

مشروع دعوي لنشر الإسلام
📖 القرآن
🕊️ السنة

🌍 بلغات متعددة

هدفنا:
تبليغ الإسلام الصحيح بدون آراء شخصية""",
            reply_markup=back(),
            parse_mode="HTML"
        )


# ================== تشغيل ==================
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN missing")
        return

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handler))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()