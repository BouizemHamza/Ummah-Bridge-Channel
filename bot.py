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
# Languages
# =====================================================

ADHKAR_LANGUAGES = {
    "ar": {
        "flag": "🇸🇦",
        "name": "العربية",
        "label_arabic_text": "النص العربي",
        "label_meaning": "المعنى",
        "label_repeat": "التكرار",
        "label_source": "المصدر",
        "missing": "",
        "morning_title": "🌅 أذكار الصباح",
        "evening_title": "🌙 أذكار المساء",
        "dhikr_word": "الذكر",
        "done_morning": "✅ <b>أحسنت.</b>\n\nانتهيت من أذكار الصباح.\nنسأل الله أن يحفظك ويبارك يومك.",
        "done_evening": "✅ <b>أحسنت.</b>\n\nانتهيت من أذكار المساء.\nنسأل الله أن يحفظك في ليلتك.",
        "reminder_morning": "🌅 <b>تذكير أذكار الصباح</b>\n\nابدأ بقراءة أذكار الصباح الآن.",
        "reminder_evening": "🌙 <b>تذكير أذكار المساء</b>\n\nابدأ بقراءة أذكار المساء الآن.",
        "start_morning_button": "🌅 ابدأ أذكار الصباح",
        "start_evening_button": "🌙 ابدأ أذكار المساء",
    },
    "en": {
        "flag": "🇬🇧",
        "name": "English",
        "label_arabic_text": "Arabic text",
        "label_meaning": "Meaning in English",
        "label_repeat": "Repeat",
        "label_source": "Source",
        "missing": "Meaning in this language is being added.",
        "morning_title": "🌅 Morning Adhkar",
        "evening_title": "🌙 Evening Adhkar",
        "dhikr_word": "Dhikr",
        "done_morning": "✅ <b>Well done.</b>\n\nYou finished the morning adhkar.",
        "done_evening": "✅ <b>Well done.</b>\n\nYou finished the evening adhkar.",
        "reminder_morning": "🌅 <b>Morning Adhkar Reminder</b>\n\nStart reading your morning adhkar now.",
        "reminder_evening": "🌙 <b>Evening Adhkar Reminder</b>\n\nStart reading your evening adhkar now.",
        "start_morning_button": "🌅 Start Morning Adhkar",
        "start_evening_button": "🌙 Start Evening Adhkar",
    },
    "de": {
        "flag": "🇩🇪",
        "name": "Deutsch",
        "label_arabic_text": "Arabischer Text",
        "label_meaning": "Bedeutung auf Deutsch",
        "label_repeat": "Wiederholung",
        "label_source": "Quelle",
        "missing": "Die Bedeutung in dieser Sprache wird noch hinzugefügt.",
        "morning_title": "🌅 Morgen-Adhkar",
        "evening_title": "🌙 Abend-Adhkar",
        "dhikr_word": "Dhikr",
        "done_morning": "✅ <b>Sehr gut.</b>\n\nDu hast die Morgen-Adhkar beendet.",
        "done_evening": "✅ <b>Sehr gut.</b>\n\nDu hast die Abend-Adhkar beendet.",
        "reminder_morning": "🌅 <b>Erinnerung an Morgen-Adhkar</b>\n\nBeginne jetzt mit deinen Morgen-Adhkar.",
        "reminder_evening": "🌙 <b>Erinnerung an Abend-Adhkar</b>\n\nBeginne jetzt mit deinen Abend-Adhkar.",
        "start_morning_button": "🌅 Morgen-Adhkar starten",
        "start_evening_button": "🌙 Abend-Adhkar starten",
    },
    "fr": {
        "flag": "🇫🇷",
        "name": "Français",
        "label_arabic_text": "Texte arabe",
        "label_meaning": "Sens en français",
        "label_repeat": "Répétition",
        "label_source": "Source",
        "missing": "Le sens dans cette langue est en cours d’ajout.",
        "morning_title": "🌅 Adhkâr du matin",
        "evening_title": "🌙 Adhkâr du soir",
        "dhikr_word": "Dhikr",
        "done_morning": "✅ <b>Très bien.</b>\n\nVous avez terminé les adhkâr du matin.",
        "done_evening": "✅ <b>Très bien.</b>\n\nVous avez terminé les adhkâr du soir.",
        "reminder_morning": "🌅 <b>Rappel des adhkâr du matin</b>\n\nCommencez vos adhkâr du matin maintenant.",
        "reminder_evening": "🌙 <b>Rappel des adhkâr du soir</b>\n\nCommencez vos adhkâr du soir maintenant.",
        "start_morning_button": "🌅 Commencer les adhkâr du matin",
        "start_evening_button": "🌙 Commencer les adhkâr du soir",
    },
    "es": {
        "flag": "🇪🇸",
        "name": "Español",
        "label_arabic_text": "Texto árabe",
        "label_meaning": "Significado en español",
        "label_repeat": "Repetición",
        "label_source": "Fuente",
        "missing": "El significado en este idioma se está añadiendo.",
        "morning_title": "🌅 Adhkar de la mañana",
        "evening_title": "🌙 Adhkar de la tarde",
        "dhikr_word": "Dhikr",
        "done_morning": "✅ <b>Muy bien.</b>\n\nHas terminado los adhkar de la mañana.",
        "done_evening": "✅ <b>Muy bien.</b>\n\nHas terminado los adhkar de la tarde.",
        "reminder_morning": "🌅 <b>Recordatorio de adhkar de la mañana</b>\n\nEmpieza ahora tus adhkar de la mañana.",
        "reminder_evening": "🌙 <b>Recordatorio de adhkar de la tarde</b>\n\nEmpieza ahora tus adhkar de la tarde.",
        "start_morning_button": "🌅 Empezar adhkar de la mañana",
        "start_evening_button": "🌙 Empezar adhkar de la tarde",
    },
    "tr": {
        "flag": "🇹🇷",
        "name": "Türkçe",
        "label_arabic_text": "Arapça metin",
        "label_meaning": "Türkçe anlamı",
        "label_repeat": "Tekrar",
        "label_source": "Kaynak",
        "missing": "Bu dildeki anlam ekleniyor.",
        "morning_title": "🌅 Sabah zikirleri",
        "evening_title": "🌙 Akşam zikirleri",
        "dhikr_word": "Zikir",
        "done_morning": "✅ <b>Güzel.</b>\n\nSabah zikirlerini tamamladınız.",
        "done_evening": "✅ <b>Güzel.</b>\n\nAkşam zikirlerini tamamladınız.",
        "reminder_morning": "🌅 <b>Sabah zikirleri hatırlatması</b>\n\nSabah zikirlerinizi okumaya başlayın.",
        "reminder_evening": "🌙 <b>Akşam zikirleri hatırlatması</b>\n\nAkşam zikirlerinizi okumaya başlayın.",
        "start_morning_button": "🌅 Sabah zikirlerine başla",
        "start_evening_button": "🌙 Akşam zikirlerine başla",
    },
    "id": {
        "flag": "🇮🇩",
        "name": "Indonesia",
        "label_arabic_text": "Teks Arab",
        "label_meaning": "Makna dalam bahasa Indonesia",
        "label_repeat": "Pengulangan",
        "label_source": "Sumber",
        "missing": "Makna dalam bahasa ini sedang ditambahkan.",
        "morning_title": "🌅 Dzikir pagi",
        "evening_title": "🌙 Dzikir petang",
        "dhikr_word": "Dzikir",
        "done_morning": "✅ <b>Bagus.</b>\n\nAnda telah menyelesaikan dzikir pagi.",
        "done_evening": "✅ <b>Bagus.</b>\n\nAnda telah menyelesaikan dzikir petang.",
        "reminder_morning": "🌅 <b>Pengingat dzikir pagi</b>\n\nMulailah membaca dzikir pagi sekarang.",
        "reminder_evening": "🌙 <b>Pengingat dzikir petang</b>\n\nMulailah membaca dzikir petang sekarang.",
        "start_morning_button": "🌅 Mulai dzikir pagi",
        "start_evening_button": "🌙 Mulai dzikir petang",
    },
    "ur": {
        "flag": "🇺🇷",
        "name": "اردو",
        "label_arabic_text": "عربی متن",
        "label_meaning": "اردو میں معنی",
        "label_repeat": "تکرار",
        "label_source": "ماخذ",
        "missing": "اس زبان میں معنی شامل کیے جا رہے ہیں۔",
        "morning_title": "🌅 صبح کے اذکار",
        "evening_title": "🌙 شام کے اذکار",
        "dhikr_word": "ذکر",
        "done_morning": "✅ <b>بہت خوب۔</b>\n\nآپ نے صبح کے اذکار مکمل کر لیے۔",
        "done_evening": "✅ <b>بہت خوب۔</b>\n\nآپ نے شام کے اذکار مکمل کر لیے۔",
        "reminder_morning": "🌅 <b>صبح کے اذکار کی یاد دہانی</b>\n\nاب صبح کے اذکار پڑھنا شروع کریں۔",
        "reminder_evening": "🌙 <b>شام کے اذکار کی یاد دہانی</b>\n\nاب شام کے اذکار پڑھنا شروع کریں۔",
        "start_morning_button": "🌅 صبح کے اذکار شروع کریں",
        "start_evening_button": "🌙 شام کے اذکار شروع کریں",
    },
    "hi": {
        "flag": "🇮🇳",
        "name": "हिन्दी",
        "label_arabic_text": "अरबी पाठ",
        "label_meaning": "हिन्दी में अर्थ",
        "label_repeat": "दोहराव",
        "label_source": "स्रोत",
        "missing": "इस भाषा में अर्थ जोड़ा जा रहा है।",
        "morning_title": "🌅 सुबह के अज़कार",
        "evening_title": "🌙 शाम के अज़कार",
        "dhikr_word": "ज़िक्र",
        "done_morning": "✅ <b>बहुत अच्छा।</b>\n\nआपने सुबह के अज़कार पूरे कर लिए।",
        "done_evening": "✅ <b>बहुत अच्छा।</b>\n\nआपने शाम के अज़कार पूरे कर लिए।",
        "reminder_morning": "🌅 <b>सुबह के अज़कार की याद दिलाना</b>\n\nअब सुबह के अज़कार पढ़ना शुरू करें।",
        "reminder_evening": "🌙 <b>शाम के अज़कार की याद दिलाना</b>\n\nअब शाम के अज़कार पढ़ना शुरू करें।",
        "start_morning_button": "🌅 सुबह के अज़कार शुरू करें",
        "start_evening_button": "🌙 शाम के अज़कार शुरू करें",
    },
}


REPEAT_TRANSLATIONS = {
    "مرة واحدة": {
        "ar": "مرة واحدة",
        "en": "Once",
        "de": "Einmal",
        "fr": "Une fois",
        "es": "Una vez",
        "tr": "Bir kez",
        "id": "Sekali",
        "ur": "ایک بار",
        "hi": "एक बार",
    },
    "ثلاث مرات": {
        "ar": "ثلاث مرات",
        "en": "Three times",
        "de": "Dreimal",
        "fr": "Trois fois",
        "es": "Tres veces",
        "tr": "Üç kez",
        "id": "Tiga kali",
        "ur": "تین بار",
        "hi": "तीन बार",
    },
    "أربع مرات": {
        "ar": "أربع مرات",
        "en": "Four times",
        "de": "Viermal",
        "fr": "Quatre fois",
        "es": "Cuatro veces",
        "tr": "Dört kez",
        "id": "Empat kali",
        "ur": "چار بار",
        "hi": "चार बार",
    },
    "سبع مرات": {
        "ar": "سبع مرات",
        "en": "Seven times",
        "de": "Siebenmal",
        "fr": "Sept fois",
        "es": "Siete veces",
        "tr": "Yedi kez",
        "id": "Tujuh kali",
        "ur": "سات بار",
        "hi": "सात बार",
    },
    "عشر مرات": {
        "ar": "عشر مرات",
        "en": "Ten times",
        "de": "Zehnmal",
        "fr": "Dix fois",
        "es": "Diez veces",
        "tr": "On kez",
        "id": "Sepuluh kali",
        "ur": "دس بار",
        "hi": "दस बार",
    },
    "مائة مرة": {
        "ar": "مائة مرة",
        "en": "One hundred times",
        "de": "Hundertmal",
        "fr": "Cent fois",
        "es": "Cien veces",
        "tr": "Yüz kez",
        "id": "Seratus kali",
        "ur": "سو بار",
        "hi": "सौ बार",
    },
    "عشر مرات أو مائة مرة": {
        "ar": "عشر مرات أو مائة مرة",
        "en": "Ten or one hundred times",
        "de": "Zehnmal oder hundertmal",
        "fr": "Dix ou cent fois",
        "es": "Diez o cien veces",
        "tr": "On kez veya yüz kez",
        "id": "Sepuluh atau seratus kali",
        "ur": "دس بار یا سو بار",
        "hi": "दस बार या सौ बार",
    },
}


SOURCE_TRANSLATIONS = {
    "من أذكار الصباح": {
        "ar": "من أذكار الصباح",
        "en": "Morning adhkar",
        "de": "Morgen-Adhkar",
        "fr": "Adhkâr du matin",
        "es": "Adhkar de la mañana",
        "tr": "Sabah zikirleri",
        "id": "Dzikir pagi",
        "ur": "صبح کے اذکار",
        "hi": "सुबह के अज़कार",
    },
    "من أذكار المساء": {
        "ar": "من أذكار المساء",
        "en": "Evening adhkar",
        "de": "Abend-Adhkar",
        "fr": "Adhkâr du soir",
        "es": "Adhkar de la tarde",
        "tr": "Akşam zikirleri",
        "id": "Dzikir petang",
        "ur": "شام کے اذکار",
        "hi": "शाम के अज़कार",
    },
    "من أذكار الصباح والمساء": {
        "ar": "من أذكار الصباح والمساء",
        "en": "Morning and evening adhkar",
        "de": "Morgen- und Abend-Adhkar",
        "fr": "Adhkâr du matin et du soir",
        "es": "Adhkar de la mañana y de la tarde",
        "tr": "Sabah ve akşam zikirleri",
        "id": "Dzikir pagi dan petang",
        "ur": "صبح و شام کے اذکار",
        "hi": "सुबह और शाम के अज़कार",
    },
    "سيد الاستغفار": {
        "ar": "سيد الاستغفار",
        "en": "The master supplication for forgiveness",
        "de": "Das umfassende Bittgebet um Vergebung",
        "fr": "L’invocation maîtresse du pardon",
        "es": "La súplica principal para pedir perdón",
        "tr": "Bağışlanma duasının en kapsamlısı",
        "id": "Doa utama untuk memohon ampunan",
        "ur": "استغفار کی جامع دعا",
        "hi": "क्षमा मांगने की प्रमुख दुआ",
    },
    "من الأذكار": {
        "ar": "من الأذكار",
        "en": "General dhikr",
        "de": "Allgemeiner Dhikr",
        "fr": "Dhikr général",
        "es": "Dhikr general",
        "tr": "Genel zikir",
        "id": "Dzikir umum",
        "ur": "عام ذکر",
        "hi": "सामान्य ज़िक्र",
    },
    "من الأذكار المشروعة": {
        "ar": "من الأذكار المشروعة",
        "en": "Legislated remembrance",
        "de": "Überlieferter Dhikr",
        "fr": "Dhikr rapporté",
        "es": "Dhikr legislado",
        "tr": "Meşru zikir",
        "id": "Dzikir yang disyariatkan",
        "ur": "مشروع ذکر",
        "hi": "मसनून ज़िक्र",
    },
}


# =====================================================
# Adhkar Data
# =====================================================

MORNING_ADHKAR = [
    {
        "ar": "أَصْـبَحْنا وَأَصْـبَحَ المُـلْكُ لله، والحَمْدُ لله، لا إلهَ إلاّ اللهُ وحدَهُ لا شريكَ له، لهُ المُـلْكُ ولهُ الحَمْـد، وهوَ على كلّ شيءٍ قدير.",
        "repeat": {"ar": "مرة واحدة"},
        "source": {"ar": "من أذكار الصباح"},
        "meanings": {
            "en": "We have entered the morning, and all dominion belongs to Allah. Praise belongs to Allah. There is no deity worthy of worship except Allah alone, with no partner. His is the dominion and His is the praise, and He has power over all things.",
            "de": "Wir sind in den Morgen eingetreten, und die Herrschaft gehört Allah. Alles Lob gehört Allah. Es gibt keinen anbetungswürdigen Gott außer Allah allein, ohne Partner. Ihm gehört die Herrschaft und Ihm gehört das Lob, und Er hat Macht über alle Dinge.",
            "fr": "Nous sommes entrés dans le matin, et toute la royauté appartient à Allah. La louange appartient à Allah. Nul ne mérite d’être adoré sauf Allah, seul, sans associé.",
            "es": "Hemos llegado a la mañana, y todo dominio pertenece a Allah. La alabanza pertenece a Allah. No hay divinidad digna de adoración excepto Allah, solo, sin asociado.",
            "tr": "Sabaha ulaştık ve mülk Allah’ındır. Hamd Allah’adır. Allah’tan başka ibadete layık hiçbir ilah yoktur; O tektir, ortağı yoktur.",
            "id": "Kami memasuki waktu pagi, dan seluruh kerajaan adalah milik Allah. Segala puji bagi Allah. Tidak ada sesembahan yang berhak disembah selain Allah semata.",
            "ur": "ہم نے صبح کی اور بادشاہی اللہ ہی کے لیے ہے۔ تمام تعریف اللہ کے لیے ہے۔ اللہ کے سوا کوئی معبود برحق نہیں۔",
            "hi": "हमने सुबह की, और सारी बादशाही अल्लाह ही की है। सारी प्रशंसा अल्लाह के लिए है। अल्लाह के सिवा कोई सच्चा पूज्य नहीं।",
        },
    },
    {
        "ar": "اللّهـمَّ بِكَ أَصْـبَحْنا، وَبِكَ أَمْسَيْـنا، وَبِكَ نَحْـيا، وَبِكَ نَمـوتُ، وَإِلَيْكَ النُّـشور.",
        "repeat": {"ar": "مرة واحدة"},
        "source": {"ar": "من أذكار الصباح"},
        "meanings": {
            "en": "O Allah, by You we enter the morning, by You we enter the evening, by You we live, by You we die, and to You is the resurrection.",
            "de": "O Allah, durch Dich treten wir in den Morgen ein, durch Dich treten wir in den Abend ein, durch Dich leben wir, durch Dich sterben wir, und zu Dir ist die Auferstehung.",
            "fr": "Ô Allah, c’est par Toi que nous entrons dans le matin, par Toi que nous entrons dans le soir, par Toi que nous vivons, par Toi que nous mourons, et vers Toi sera la résurrection.",
            "es": "Oh Allah, por Ti entramos en la mañana, por Ti entramos en la tarde, por Ti vivimos, por Ti morimos, y hacia Ti será la resurrección.",
            "tr": "Allah’ım, Seninle sabaha ulaştık, Seninle akşama ulaşırız, Seninle yaşarız, Seninle ölürüz ve diriliş Sanadır.",
            "id": "Ya Allah, dengan-Mu kami memasuki pagi, dengan-Mu kami memasuki petang, dengan-Mu kami hidup, dengan-Mu kami mati, dan kepada-Mu kebangkitan.",
            "ur": "اے اللہ! تیرے ہی ذریعے ہم نے صبح کی، تیرے ہی ذریعے ہم شام کرتے ہیں، تیرے ہی ذریعے ہم جیتے ہیں، تیرے ہی ذریعے ہم مرتے ہیں، اور تیری ہی طرف دوبارہ اٹھایا جانا ہے۔",
            "hi": "ऐ अल्लाह! तेरे ही सहारे हमने सुबह की, तेरे ही सहारे हम शाम करते हैं, तेरे ही सहारे हम जीते हैं, तेरे ही सहारे हम मरते हैं, और तेरी ही ओर उठाया जाना है।",
        },
    },
    {
        "ar": "اللّهـمَّ أَنْتَ رَبِّـي لا إلهَ إلاّ أَنْتَ، خَلَقْتَنـي وأنا عَبْـدُك، وأنا على عَهْـدِكَ ووَعْـدِكَ ما استطعتُ، أعوذُ بكَ مِنْ شَرِّ ما صَنَعْت، أبوءُ لكَ بنِعْمَتِكَ عليَّ، وأبوءُ بذَنْـبي، فاغْفِـرْ لي، فإنّهُ لا يَغْفِـرُ الذُّنوبَ إلاّ أنت.",
        "repeat": {"ar": "مرة واحدة"},
        "source": {"ar": "سيد الاستغفار"},
        "meanings": {
            "en": "O Allah, You are my Lord. There is no deity worthy of worship except You. You created me and I am Your servant. I remain upon Your covenant and promise as much as I am able. I seek refuge in You from the evil of what I have done. I acknowledge Your favor upon me and I acknowledge my sin, so forgive me, for none forgives sins except You.",
            "de": "O Allah, Du bist mein Herr. Es gibt keinen anbetungswürdigen Gott außer Dir. Du hast mich erschaffen und ich bin Dein Diener. Ich halte mich, soweit ich kann, an Deinen Bund und Dein Versprechen. Ich suche Zuflucht bei Dir vor dem Übel dessen, was ich getan habe. Ich erkenne Deine Gnade an mir an und erkenne meine Sünde an, so vergib mir, denn niemand vergibt Sünden außer Dir.",
        },
    },
    {
        "ar": "رَضيتُ باللهِ ربًّا، وبالإسلامِ دينًا، وبمحمّدٍ ﷺ نبيًّا.",
        "repeat": {"ar": "ثلاث مرات"},
        "source": {"ar": "من أذكار الصباح والمساء"},
        "meanings": {
            "en": "I am pleased with Allah as my Lord, Islam as my religion, and Muhammad ﷺ as my Prophet.",
            "de": "Ich bin zufrieden mit Allah als meinem Herrn, mit dem Islam als meiner Religion und mit Muhammad ﷺ als meinem Propheten.",
        },
    },
    {
        "ar": "اللّهـمَّ إنّي أَصْبَحْتُ أُشْهِدُكَ، وأُشْهِدُ حَمَلَةَ عَرْشِكَ، ومَلائِكَتَكَ، وجميعَ خَلْقِكَ، أنّكَ أنتَ اللهُ لا إلهَ إلاّ أنتَ وحدَكَ لا شريكَ لك، وأنّ محمّدًا عبدُكَ ورسولُك.",
        "repeat": {"ar": "أربع مرات"},
        "source": {"ar": "من أذكار الصباح"},
        "meanings": {
            "en": "O Allah, I have entered the morning calling You to witness, and calling the bearers of Your Throne, Your angels, and all Your creation to witness, that You are Allah; there is no deity worthy of worship except You alone with no partner, and that Muhammad is Your servant and Messenger.",
        },
    },
    {
        "ar": "اللّهـمَّ ما أَصْبَحَ بي مِنْ نِعْمَةٍ أو بأَحَدٍ مِنْ خَلْقِكَ، فَمِنْكَ وحدَكَ لا شريكَ لك، فَلَكَ الحمدُ ولكَ الشُّكر.",
        "repeat": {"ar": "مرة واحدة"},
        "source": {"ar": "من أذكار الصباح"},
        "meanings": {
            "en": "O Allah, whatever blessing has come to me or to any of Your creation this morning is from You alone, with no partner. To You belongs all praise and all thanks.",
        },
    },
    {
        "ar": "حَسْبِيَ اللهُ لا إلهَ إلاّ هو، عليهِ توكّلتُ، وهوَ ربُّ العرشِ العظيم.",
        "repeat": {"ar": "سبع مرات"},
        "source": {"ar": "من أذكار الصباح والمساء"},
        "meanings": {
            "en": "Allah is sufficient for me. There is no deity worthy of worship except Him. Upon Him I rely, and He is the Lord of the Mighty Throne.",
            "de": "Allah genügt mir. Es gibt keinen anbetungswürdigen Gott außer Ihm. Auf Ihn vertraue ich, und Er ist der Herr des gewaltigen Thrones.",
        },
    },
    {
        "ar": "بِسْمِ اللهِ الذي لا يَضُرُّ مع اسمِهِ شيءٌ في الأرضِ ولا في السماءِ، وهوَ السميعُ العليم.",
        "repeat": {"ar": "ثلاث مرات"},
        "source": {"ar": "من أذكار الصباح والمساء"},
        "meanings": {
            "en": "In the name of Allah, with whose name nothing on earth or in the heavens can cause harm, and He is the All-Hearing, the All-Knowing.",
            "de": "Im Namen Allahs, mit dessen Namen nichts auf der Erde und nichts im Himmel Schaden zufügen kann. Er ist der Allhörende, der Allwissende.",
        },
    },
    {
        "ar": "اللّهـمَّ إنّي أسألُكَ العفوَ والعافيةَ في الدنيا والآخرة.",
        "repeat": {"ar": "مرة واحدة"},
        "source": {"ar": "من أذكار الصباح والمساء"},
        "meanings": {
            "en": "O Allah, I ask You for pardon and well-being in this world and the Hereafter.",
        },
    },
    {
        "ar": "اللّهـمَّ إنّي أسألُكَ العفوَ والعافيةَ في ديني ودنيايَ وأهلي ومالي.",
        "repeat": {"ar": "مرة واحدة"},
        "source": {"ar": "من أذكار الصباح والمساء"},
        "meanings": {
            "en": "O Allah, I ask You for pardon and well-being in my religion, my worldly life, my family, and my wealth.",
        },
    },
    {
        "ar": "اللّهـمَّ استُرْ عوراتي، وآمِنْ رَوْعاتي.",
        "repeat": {"ar": "مرة واحدة"},
        "source": {"ar": "من أذكار الصباح والمساء"},
        "meanings": {
            "en": "O Allah, conceal my faults and calm my fears.",
        },
    },
    {
        "ar": "يا حيُّ يا قيّومُ، برحمتِكَ أستغيث، أصلِحْ لي شأني كلَّه، ولا تَكِلْني إلى نفسي طَرْفَةَ عين.",
        "repeat": {"ar": "مرة واحدة"},
        "source": {"ar": "من أذكار الصباح والمساء"},
        "meanings": {
            "en": "O Ever-Living, O Sustainer, by Your mercy I seek help. Rectify all of my affairs and do not leave me to myself even for the blink of an eye.",
        },
    },
    {
        "ar": "سُبْحانَ اللهِ وبحمدِه.",
        "repeat": {"ar": "مائة مرة"},
        "source": {"ar": "من أذكار الصباح والمساء"},
        "meanings": {
            "en": "Glory and praise be to Allah.",
            "fr": "Gloire et louange à Allah.",
            "es": "Gloria y alabanza sean para Allah.",
            "tr": "Allah’ı tesbih ederim ve O’na hamd ederim.",
            "id": "Mahasuci Allah dan segala puji bagi-Nya.",
            "ur": "اللہ پاک ہے اور اسی کے لیے تعریف ہے۔",
            "hi": "अल्लाह पाक है और सारी प्रशंसा उसी के लिए है।",
        },
    },
    {
        "ar": "لا إلهَ إلاّ اللهُ وحدَهُ لا شريكَ له، لهُ الملكُ ولهُ الحمدُ، وهوَ على كلّ شيءٍ قدير.",
        "repeat": {"ar": "عشر مرات أو مائة مرة"},
        "source": {"ar": "من أذكار الصباح والمساء"},
        "meanings": {
            "en": "There is no deity worthy of worship except Allah alone, with no partner. His is the dominion and His is the praise, and He has power over all things.",
        },
    },
    {
        "ar": "أستغفرُ اللهَ وأتوبُ إليه.",
        "repeat": {"ar": "مائة مرة"},
        "source": {"ar": "من الأذكار"},
        "meanings": {
            "en": "I seek Allah’s forgiveness and repent to Him.",
            "fr": "Je demande pardon à Allah et je me repens à Lui.",
            "es": "Pido perdón a Allah y me arrepiento ante Él.",
            "tr": "Allah’tan bağışlanma dilerim ve O’na tövbe ederim.",
            "id": "Aku memohon ampun kepada Allah dan bertaubat kepada-Nya.",
            "ur": "میں اللہ سے بخشش طلب کرتا ہوں اور اسی کی طرف توبہ کرتا ہوں۔",
            "hi": "मैं अल्लाह से क्षमा मांगता हूँ और उसी की ओर तौबा करता हूँ।",
        },
    },
    {
        "ar": "اللّهـمَّ صلِّ وسلّمْ على نبيّنا محمد.",
        "repeat": {"ar": "عشر مرات"},
        "source": {"ar": "من الأذكار المشروعة"},
        "meanings": {
            "en": "O Allah, send prayers and peace upon our Prophet Muhammad.",
            "fr": "Ô Allah, accorde Tes prières et Ta paix à notre Prophète Muhammad.",
            "es": "Oh Allah, concede bendiciones y paz a nuestro Profeta Muhammad.",
            "tr": "Allah’ım, Peygamberimiz Muhammed’e salât ve selâm eyle.",
            "id": "Ya Allah, limpahkan salawat dan salam kepada Nabi kami Muhammad.",
            "ur": "اے اللہ! ہمارے نبی محمد پر درود و سلام بھیج۔",
            "hi": "ऐ अल्लाह! हमारे नबी मुहम्मद पर दुरूद और सलाम भेज।",
        },
    },
]


EVENING_ADHKAR = [item.copy() for item in MORNING_ADHKAR]

EVENING_ADHKAR[0] = {
    "ar": "أَمْسَيْنا وأَمْسَى المُـلْكُ لله، والحَمْدُ لله، لا إلهَ إلاّ اللهُ وحدَهُ لا شريكَ له، لهُ المُـلْكُ ولهُ الحَمْـد، وهوَ على كلّ شيءٍ قدير.",
    "repeat": {"ar": "مرة واحدة"},
    "source": {"ar": "من أذكار المساء"},
    "meanings": {
        "en": "We have entered the evening, and all dominion belongs to Allah. Praise belongs to Allah. There is no deity worthy of worship except Allah alone, with no partner.",
        "de": "Wir sind in den Abend eingetreten, und die Herrschaft gehört Allah. Alles Lob gehört Allah. Es gibt keinen anbetungswürdigen Gott außer Allah allein.",
        "fr": "Nous sommes entrés dans le soir, et toute la royauté appartient à Allah. La louange appartient à Allah.",
        "es": "Hemos llegado a la tarde, y todo dominio pertenece a Allah. La alabanza pertenece a Allah.",
        "tr": "Akşama ulaştık ve mülk Allah’ındır. Hamd Allah’adır.",
        "id": "Kami memasuki waktu petang, dan seluruh kerajaan adalah milik Allah. Segala puji bagi Allah.",
        "ur": "ہم نے شام کی اور بادشاہی اللہ ہی کے لیے ہے۔ تمام تعریف اللہ کے لیے ہے۔",
        "hi": "हमने शाम की, और सारी बादशाही अल्लाह ही की है। सारी प्रशंसा अल्लाह के लिए है।",
    },
}

EVENING_ADHKAR[1] = {
    "ar": "اللّهـمَّ بِكَ أَمْسَيْنا، وبِكَ أَصْبَحْنا، وبِكَ نَحْيا، وبِكَ نَموتُ، وإليكَ المصير.",
    "repeat": {"ar": "مرة واحدة"},
    "source": {"ar": "من أذكار المساء"},
    "meanings": {
        "en": "O Allah, by You we enter the evening, by You we enter the morning, by You we live, by You we die, and to You is the return.",
        "de": "O Allah, durch Dich treten wir in den Abend ein, durch Dich treten wir in den Morgen ein, durch Dich leben wir, durch Dich sterben wir, und zu Dir ist die Rückkehr.",
        "fr": "Ô Allah, c’est par Toi que nous entrons dans le soir, par Toi que nous entrons dans le matin, par Toi que nous vivons, par Toi que nous mourons, et vers Toi est le retour.",
        "es": "Oh Allah, por Ti entramos en la tarde, por Ti entramos en la mañana, por Ti vivimos, por Ti morimos, y hacia Ti es el retorno.",
        "tr": "Allah’ım, Seninle akşama ulaştık, Seninle sabaha ulaşırız, Seninle yaşarız, Seninle ölürüz ve dönüş Sanadır.",
        "id": "Ya Allah, dengan-Mu kami memasuki petang, dengan-Mu kami memasuki pagi, dengan-Mu kami hidup, dengan-Mu kami mati, dan kepada-Mu tempat kembali.",
        "ur": "اے اللہ! تیرے ہی ذریعے ہم نے شام کی، تیرے ہی ذریعے ہم صبح کرتے ہیں، تیرے ہی ذریعے ہم جیتے ہیں، تیرے ہی ذریعے ہم مرتے ہیں، اور تیری ہی طرف لوٹنا ہے۔",
        "hi": "ऐ अल्लाह! तेरे ही सहारे हमने शाम की, तेरे ही सहारे हम सुबह करते हैं, तेरे ही सहारे हम जीते हैं, तेरे ही सहारे हम मरते हैं, और तेरी ही ओर लौटना है।",
    },
}


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
    c.execute(
        "INSERT INTO channel_posts(post_type, item_id, posted_at, hour, source) VALUES (?, ?, ?, ?, ?)",
        (post_type, str(item_id or ""), ts, datetime.datetime.now().hour, source)
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
        params={"language": "ar", "category_id": 1, "page": random.randint(1, 5), "per_page": 10},
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
        params={"language": lang, "id": hadith_id},
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
    response = requests.get(f"{QURAN_API}/ayah/{number}/{edition}", timeout=15)
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

    if lang == "ar":
        text = f"""{title}

<b>{lang_pack["dhikr_word"]} {index + 1}/{total}</b>
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
    await send_channel_message(context, text, "hadith", hid, "test_command")
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
# Adhkar Reminders
# =====================================================

async def send_morning_adhkar_reminders(context: ContextTypes.DEFAULT_TYPE):
    for user_id, chat_id in get_adhkar_subscribers("morning"):
        lang = get_adhkar_lang(user_id)
        lang_pack = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=lang_pack["reminder_morning"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(lang_pack["start_morning_button"], callback_data="adhkar_morning_0")]
                ]),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Morning adhkar reminder error for {user_id}: {e}")


async def send_evening_adhkar_reminders(context: ContextTypes.DEFAULT_TYPE):
    for user_id, chat_id in get_adhkar_subscribers("evening"):
        lang = get_adhkar_lang(user_id)
        lang_pack = ADHKAR_LANGUAGES.get(lang, ADHKAR_LANGUAGES["ar"])

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=lang_pack["reminder_evening"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(lang_pack["start_evening_button"], callback_data="adhkar_evening_0")]
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
                text += f"<b>#{i}</b>\n{esc(row[0][:500])}\n\n━━━━━━━━━━━━━━\n\n"

        await safe_edit(q, text, back())

    elif data == "adhkar_menu":
        lang = get_adhkar_lang(user_id)

        await safe_edit(
            q,
            f"🤲 <b>قسم الأذكار</b>\n\n🌍 اللغة الحالية: <b>{esc(language_display(lang))}</b>\n\nاختر ما تريد قراءته:",
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
        set_adhkar_reminder(user_id, chat_id, "morning", 0 if morning else 1)
        await q.answer("تم تحديث تذكير الصباح ✅", show_alert=True)
        await safe_edit(q, "⏰ <b>تم تحديث إعدادات التذكير.</b>", adhkar_reminder_menu(user_id))

    elif data == "adhkar_toggle_evening":
        morning, evening = get_adhkar_reminder_status(user_id)
        set_adhkar_reminder(user_id, chat_id, "evening", 0 if evening else 1)
        await q.answer("تم تحديث تذكير المساء ✅", show_alert=True)
        await safe_edit(q, "⏰ <b>تم تحديث إعدادات التذكير.</b>", adhkar_reminder_menu(user_id))

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
        await safe_edit(q, "✍️ <b>أرسل الآن الرسالة التي تريد نشرها في القناة.</b>", admin_back())


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

        log_channel_post("custom", "", "admin_custom")

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

    print("Bot running with fixed adhkar repeat/source translations...")
    print(f"Morning adhkar reminder: {MORNING_ADHKAR_TIME}")
    print(f"Evening adhkar reminder: {EVENING_ADHKAR_TIME}")

    app.run_polling()


if __name__ == "__main__":
    main()