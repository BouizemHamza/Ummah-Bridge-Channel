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


# ================== ADHKAR DATA ==================

MORNING_ADHKAR = [
    {
        "ar": "أَصْـبَحْنا وَأَصْـبَحَ المُـلْكُ لله، والحَمْدُ لله، لا إلهَ إلاّ اللهُ وحدَهُ لا شريكَ له، لهُ المُـلْكُ ولهُ الحَمْـد، وهوَ على كلّ شيءٍ قدير.",
        "en": "We have entered the morning, and all dominion belongs to Allah. Praise belongs to Allah. There is no deity worthy of worship except Allah alone, with no partner. His is the dominion and His is the praise, and He has power over all things.",
        "de": "Wir sind in den Morgen eingetreten, und die Herrschaft gehört Allah. Alles Lob gehört Allah. Es gibt keinen anbetungswürdigen Gott außer Allah allein, ohne Partner. Ihm gehört die Herrschaft und Ihm gehört das Lob, und Er hat Macht über alle Dinge.",
        "repeat_ar": "مرة واحدة",
        "repeat_en": "Once",
        "repeat_de": "Einmal",
        "source_ar": "من أذكار الصباح",
        "source_en": "Morning adhkar",
        "source_de": "Morgen-Adhkar",
    },
    {
        "ar": "اللّهـمَّ بِكَ أَصْـبَحْنا، وَبِكَ أَمْسَيْـنا، وَبِكَ نَحْـيا، وَبِكَ نَمـوتُ، وَإِلَيْكَ النُّـشور.",
        "en": "O Allah, by You we enter the morning, by You we enter the evening, by You we live, by You we die, and to You is the resurrection.",
        "de": "O Allah, durch Dich treten wir in den Morgen ein, durch Dich treten wir in den Abend ein, durch Dich leben wir, durch Dich sterben wir, und zu Dir ist die Auferstehung.",
        "repeat_ar": "مرة واحدة",
        "repeat_en": "Once",
        "repeat_de": "Einmal",
        "source_ar": "من أذكار الصباح",
        "source_en": "Morning adhkar",
        "source_de": "Morgen-Adhkar",
    },
    {
        "ar": "اللّهـمَّ أَنْتَ رَبِّـي لا إلهَ إلاّ أَنْتَ، خَلَقْتَنـي وأنا عَبْـدُك، وأنا على عَهْـدِكَ ووَعْـدِكَ ما استطعتُ، أعوذُ بكَ مِنْ شَرِّ ما صَنَعْت، أبوءُ لكَ بنِعْمَتِكَ عليَّ، وأبوءُ بذَنْـبي، فاغْفِـرْ لي، فإنّهُ لا يَغْفِـرُ الذُّنوبَ إلاّ أنت.",
        "en": "O Allah, You are my Lord. There is no deity worthy of worship except You. You created me and I am Your servant. I remain upon Your covenant and promise as much as I am able. I seek refuge in You from the evil of what I have done. I acknowledge Your favor upon me and I acknowledge my sin, so forgive me, for none forgives sins except You.",
        "de": "O Allah, Du bist mein Herr. Es gibt keinen anbetungswürdigen Gott außer Dir. Du hast mich erschaffen und ich bin Dein Diener. Ich halte mich, soweit ich kann, an Deinen Bund und Dein Versprechen. Ich suche Zuflucht bei Dir vor dem Übel dessen, was ich getan habe. Ich erkenne Deine Gnade an mir an und erkenne meine Sünde an, so vergib mir, denn niemand vergibt Sünden außer Dir.",
        "repeat_ar": "مرة واحدة",
        "repeat_en": "Once",
        "repeat_de": "Einmal",
        "source_ar": "سيد الاستغفار",
        "source_en": "The master supplication for forgiveness",
        "source_de": "Das umfassende Bittgebet um Vergebung",
    },
    {
        "ar": "رَضيتُ باللهِ ربًّا، وبالإسلامِ دينًا، وبمحمّدٍ ﷺ نبيًّا.",
        "en": "I am pleased with Allah as my Lord, Islam as my religion, and Muhammad ﷺ as my Prophet.",
        "de": "Ich bin zufrieden mit Allah als meinem Herrn, mit dem Islam als meiner Religion und mit Muhammad ﷺ als meinem Propheten.",
        "repeat_ar": "ثلاث مرات",
        "repeat_en": "Three times",
        "repeat_de": "Dreimal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "اللّهـمَّ إنّي أَصْبَحْتُ أُشْهِدُكَ، وأُشْهِدُ حَمَلَةَ عَرْشِكَ، ومَلائِكَتَكَ، وجميعَ خَلْقِكَ، أنّكَ أنتَ اللهُ لا إلهَ إلاّ أنتَ وحدَكَ لا شريكَ لك، وأنّ محمّدًا عبدُكَ ورسولُك.",
        "en": "O Allah, I have entered the morning calling You to witness, and calling the bearers of Your Throne, Your angels, and all Your creation to witness, that You are Allah; there is no deity worthy of worship except You alone with no partner, and that Muhammad is Your servant and Messenger.",
        "de": "O Allah, ich bin in den Morgen eingetreten und rufe Dich, die Träger Deines Thrones, Deine Engel und Deine gesamte Schöpfung als Zeugen an, dass Du Allah bist; es gibt keinen anbetungswürdigen Gott außer Dir allein, ohne Partner, und dass Muhammad Dein Diener und Gesandter ist.",
        "repeat_ar": "أربع مرات",
        "repeat_en": "Four times",
        "repeat_de": "Viermal",
        "source_ar": "من أذكار الصباح",
        "source_en": "Morning adhkar",
        "source_de": "Morgen-Adhkar",
    },
    {
        "ar": "اللّهـمَّ ما أَصْبَحَ بي مِنْ نِعْمَةٍ أو بأَحَدٍ مِنْ خَلْقِكَ، فَمِنْكَ وحدَكَ لا شريكَ لك، فَلَكَ الحمدُ ولكَ الشُّكر.",
        "en": "O Allah, whatever blessing has come to me or to any of Your creation this morning is from You alone, with no partner. To You belongs all praise and all thanks.",
        "de": "O Allah, jede Gnade, die mich oder eines Deiner Geschöpfe an diesem Morgen erreicht hat, ist von Dir allein, ohne Partner. Dir gebührt alles Lob und aller Dank.",
        "repeat_ar": "مرة واحدة",
        "repeat_en": "Once",
        "repeat_de": "Einmal",
        "source_ar": "من أذكار الصباح",
        "source_en": "Morning adhkar",
        "source_de": "Morgen-Adhkar",
    },
    {
        "ar": "حَسْبِيَ اللهُ لا إلهَ إلاّ هو، عليهِ توكّلتُ، وهوَ ربُّ العرشِ العظيم.",
        "en": "Allah is sufficient for me. There is no deity worthy of worship except Him. Upon Him I rely, and He is the Lord of the Mighty Throne.",
        "de": "Allah genügt mir. Es gibt keinen anbetungswürdigen Gott außer Ihm. Auf Ihn vertraue ich, und Er ist der Herr des gewaltigen Thrones.",
        "repeat_ar": "سبع مرات",
        "repeat_en": "Seven times",
        "repeat_de": "Siebenmal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "بِسْمِ اللهِ الذي لا يَضُرُّ مع اسمِهِ شيءٌ في الأرضِ ولا في السماءِ، وهوَ السميعُ العليم.",
        "en": "In the name of Allah, with whose name nothing on earth or in the heavens can cause harm, and He is the All-Hearing, the All-Knowing.",
        "de": "Im Namen Allahs, mit dessen Namen nichts auf der Erde und nichts im Himmel Schaden zufügen kann. Er ist der Allhörende, der Allwissende.",
        "repeat_ar": "ثلاث مرات",
        "repeat_en": "Three times",
        "repeat_de": "Dreimal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "اللّهـمَّ عافِني في بَدَني، اللّهـمَّ عافِني في سَمْعي، اللّهـمَّ عافِني في بَصَري، لا إلهَ إلاّ أنت.",
        "en": "O Allah, grant me well-being in my body. O Allah, grant me well-being in my hearing. O Allah, grant me well-being in my sight. There is no deity worthy of worship except You.",
        "de": "O Allah, schenke mir Wohlergehen in meinem Körper. O Allah, schenke mir Wohlergehen in meinem Gehör. O Allah, schenke mir Wohlergehen in meinem Sehvermögen. Es gibt keinen anbetungswürdigen Gott außer Dir.",
        "repeat_ar": "ثلاث مرات",
        "repeat_en": "Three times",
        "repeat_de": "Dreimal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "اللّهـمَّ إنّي أعوذُ بكَ مِنَ الكُفْرِ والفَقْر، وأعوذُ بكَ مِنْ عذابِ القَبْر، لا إلهَ إلاّ أنت.",
        "en": "O Allah, I seek refuge in You from disbelief and poverty, and I seek refuge in You from the punishment of the grave. There is no deity worthy of worship except You.",
        "de": "O Allah, ich suche Zuflucht bei Dir vor Unglauben und Armut, und ich suche Zuflucht bei Dir vor der Strafe des Grabes. Es gibt keinen anbetungswürdigen Gott außer Dir.",
        "repeat_ar": "ثلاث مرات",
        "repeat_en": "Three times",
        "repeat_de": "Dreimal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "اللّهـمَّ إنّي أسألُكَ العفوَ والعافيةَ في الدنيا والآخرة.",
        "en": "O Allah, I ask You for pardon and well-being in this world and the Hereafter.",
        "de": "O Allah, ich bitte Dich um Vergebung und Wohlergehen im Diesseits und im Jenseits.",
        "repeat_ar": "مرة واحدة",
        "repeat_en": "Once",
        "repeat_de": "Einmal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "اللّهـمَّ إنّي أسألُكَ العفوَ والعافيةَ في ديني ودنيايَ وأهلي ومالي.",
        "en": "O Allah, I ask You for pardon and well-being in my religion, my worldly life, my family, and my wealth.",
        "de": "O Allah, ich bitte Dich um Vergebung und Wohlergehen in meiner Religion, meinem weltlichen Leben, meiner Familie und meinem Besitz.",
        "repeat_ar": "مرة واحدة",
        "repeat_en": "Once",
        "repeat_de": "Einmal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "اللّهـمَّ استُرْ عوراتي، وآمِنْ رَوْعاتي.",
        "en": "O Allah, conceal my faults and calm my fears.",
        "de": "O Allah, bedecke meine Fehler und beruhige meine Ängste.",
        "repeat_ar": "مرة واحدة",
        "repeat_en": "Once",
        "repeat_de": "Einmal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "اللّهـمَّ احفظني مِنْ بينِ يديَّ، ومِنْ خَلْفي، وعن يميني، وعن شمالي، ومِنْ فوقي، وأعوذُ بعظمتِكَ أن أُغتالَ مِنْ تحتي.",
        "en": "O Allah, protect me from in front of me, from behind me, from my right, from my left, and from above me. I seek refuge in Your greatness from being taken unaware from beneath me.",
        "de": "O Allah, beschütze mich von vorne, von hinten, von rechts, von links und von oben. Ich suche Zuflucht bei Deiner Größe davor, von unten unerwartet getroffen zu werden.",
        "repeat_ar": "مرة واحدة",
        "repeat_en": "Once",
        "repeat_de": "Einmal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "يا حيُّ يا قيّومُ، برحمتِكَ أستغيث، أصلِحْ لي شأني كلَّه، ولا تَكِلْني إلى نفسي طَرْفَةَ عين.",
        "en": "O Ever-Living, O Sustainer, by Your mercy I seek help. Rectify all of my affairs and do not leave me to myself even for the blink of an eye.",
        "de": "O Ewig-Lebendiger, O Erhalter, durch Deine Barmherzigkeit suche ich Hilfe. Verbessere all meine Angelegenheiten und überlasse mich mir selbst nicht einmal für einen Augenblick.",
        "repeat_ar": "مرة واحدة",
        "repeat_en": "Once",
        "repeat_de": "Einmal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "أَصْبَحْنا على فِطْرَةِ الإسلام، وعلى كلمةِ الإخلاص، وعلى دينِ نبيّنا محمدٍ ﷺ، وعلى مِلّةِ أبينا إبراهيمَ حنيفًا مسلمًا وما كانَ مِنَ المشركين.",
        "en": "We have entered the morning upon the natural way of Islam, the word of sincerity, the religion of our Prophet Muhammad ﷺ, and the way of our father Ibrahim, who was upright and Muslim and was not among the polytheists.",
        "de": "Wir sind in den Morgen eingetreten auf der natürlichen Veranlagung des Islam, auf dem Wort der Aufrichtigkeit, auf der Religion unseres Propheten Muhammad ﷺ und auf dem Weg unseres Vaters Ibrahim, der aufrichtig und Muslim war und nicht zu den Götzendienern gehörte.",
        "repeat_ar": "مرة واحدة",
        "repeat_en": "Once",
        "repeat_de": "Einmal",
        "source_ar": "من أذكار الصباح",
        "source_en": "Morning adhkar",
        "source_de": "Morgen-Adhkar",
    },
    {
        "ar": "سُبْحانَ اللهِ وبحمدِه.",
        "en": "Glory and praise be to Allah.",
        "de": "Preis sei Allah und Lob sei Ihm.",
        "repeat_ar": "مائة مرة",
        "repeat_en": "One hundred times",
        "repeat_de": "Hundertmal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "لا إلهَ إلاّ اللهُ وحدَهُ لا شريكَ له، لهُ الملكُ ولهُ الحمدُ، وهوَ على كلّ شيءٍ قدير.",
        "en": "There is no deity worthy of worship except Allah alone, with no partner. His is the dominion and His is the praise, and He has power over all things.",
        "de": "Es gibt keinen anbetungswürdigen Gott außer Allah allein, ohne Partner. Ihm gehört die Herrschaft und Ihm gehört das Lob, und Er hat Macht über alle Dinge.",
        "repeat_ar": "عشر مرات أو مائة مرة",
        "repeat_en": "Ten or one hundred times",
        "repeat_de": "Zehnmal oder hundertmal",
        "source_ar": "من أذكار الصباح والمساء",
        "source_en": "Morning and evening adhkar",
        "source_de": "Morgen- und Abend-Adhkar",
    },
    {
        "ar": "أستغفرُ اللهَ وأتوبُ إليه.",
        "en": "I seek Allah’s forgiveness and repent to Him.",
        "de": "Ich bitte Allah um Vergebung und bereue vor Ihm.",
        "repeat_ar": "مائة مرة",
        "repeat_en": "One hundred times",
        "repeat_de": "Hundertmal",
        "source_ar": "من الأذكار",
        "source_en": "General dhikr",
        "source_de": "Allgemeiner Dhikr",
    },
    {
        "ar": "اللّهـمَّ صلِّ وسلّمْ على نبيّنا محمد.",
        "en": "O Allah, send prayers and peace upon our Prophet Muhammad.",
        "de": "O Allah, sende Segen und Frieden auf unseren Propheten Muhammad.",
        "repeat_ar": "عشر مرات",
        "repeat_en": "Ten times",
        "repeat_de": "Zehnmal",
        "source_ar": "من الأذكار المشروعة",
        "source_en": "Legislated remembrance",
        "source_de": "Überlieferter Dhikr",
    },
]

EVENING_ADHKAR = []
for item in MORNING_ADHKAR:
    EVENING_ADHKAR.append(item.copy())

EVENING_ADHKAR[0] = {
    "ar": "أَمْسَيْنا وأَمْسَى المُـلْكُ لله، والحَمْدُ لله، لا إلهَ إلاّ اللهُ وحدَهُ لا شريكَ له، لهُ المُـلْكُ ولهُ الحَمْـد، وهوَ على كلّ شيءٍ قدير.",
    "en": "We have entered the evening, and all dominion belongs to Allah. Praise belongs to Allah. There is no deity worthy of worship except Allah alone, with no partner. His is the dominion and His is the praise, and He has power over all things.",
    "de": "Wir sind in den Abend eingetreten, und die Herrschaft gehört Allah. Alles Lob gehört Allah. Es gibt keinen anbetungswürdigen Gott außer Allah allein, ohne Partner. Ihm gehört die Herrschaft und Ihm gehört das Lob, und Er hat Macht über alle Dinge.",
    "repeat_ar": "مرة واحدة",
    "repeat_en": "Once",
    "repeat_de": "Einmal",
    "source_ar": "من أذكار المساء",
    "source_en": "Evening adhkar",
    "source_de": "Abend-Adhkar",
}

EVENING_ADHKAR[1] = {
    "ar": "اللّهـمَّ بِكَ أَمْسَيْنا، وبِكَ أَصْبَحْنا، وبِكَ نَحْيا، وبِكَ نَموتُ، وإليكَ المصير.",
    "en": "O Allah, by You we enter the evening, by You we enter the morning, by You we live, by You we die, and to You is the return.",
    "de": "O Allah, durch Dich treten wir in den Abend ein, durch Dich treten wir in den Morgen ein, durch Dich leben wir, durch Dich sterben wir, und zu Dir ist die Rückkehr.",
    "repeat_ar": "مرة واحدة",
    "repeat_en": "Once",
    "repeat_de": "Einmal",
    "source_ar": "من أذكار المساء",
    "source_en": "Evening adhkar",
    "source_de": "Abend-Adhkar",
}

EVENING_ADHKAR[4] = {
    "ar": "اللّهـمَّ إنّي أَمْسَيْتُ أُشْهِدُكَ، وأُشْهِدُ حَمَلَةَ عَرْشِكَ، ومَلائِكَتَكَ، وجميعَ خَلْقِكَ، أنّكَ أنتَ اللهُ لا إلهَ إلاّ أنتَ وحدَكَ لا شريكَ لك، وأنّ محمّدًا عبدُكَ ورسولُك.",
    "en": "O Allah, I have entered the evening calling You to witness, and calling the bearers of Your Throne, Your angels, and all Your creation to witness, that You are Allah; there is no deity worthy of worship except You alone with no partner, and that Muhammad is Your servant and Messenger.",
    "de": "O Allah, ich bin in den Abend eingetreten und rufe Dich, die Träger Deines Thrones, Deine Engel und Deine gesamte Schöpfung als Zeugen an, dass Du Allah bist; es gibt keinen anbetungswürdigen Gott außer Dir allein, ohne Partner, und dass Muhammad Dein Diener und Gesandter ist.",
    "repeat_ar": "أربع مرات",
    "repeat_en": "Four times",
    "repeat_de": "Viermal",
    "source_ar": "من أذكار المساء",
    "source_en": "Evening adhkar",
    "source_de": "Abend-Adhkar",
}

EVENING_ADHKAR[5] = {
    "ar": "اللّهـمَّ ما أَمْسَى بي مِنْ نِعْمَةٍ أو بأَحَدٍ مِنْ خَلْقِكَ، فَمِنْكَ وحدَكَ لا شريكَ لك، فَلَكَ الحمدُ ولكَ الشُّكر.",
    "en": "O Allah, whatever blessing has come to me or to any of Your creation this evening is from You alone, with no partner. To You belongs all praise and all thanks.",
    "de": "O Allah, jede Gnade, die mich oder eines Deiner Geschöpfe an diesem Abend erreicht hat, ist von Dir allein, ohne Partner. Dir gebührt alles Lob und aller Dank.",
    "repeat_ar": "مرة واحدة",
    "repeat_en": "Once",
    "repeat_de": "Einmal",
    "source_ar": "من أذكار المساء",
    "source_en": "Evening adhkar",
    "source_de": "Abend-Adhkar",
}

EVENING_ADHKAR[15] = {
    "ar": "أَمْسَيْنا على فِطْرَةِ الإسلام، وعلى كلمةِ الإخلاص، وعلى دينِ نبيّنا محمدٍ ﷺ، وعلى مِلّةِ أبينا إبراهيمَ حنيفًا مسلمًا وما كانَ مِنَ المشركين.",
    "en": "We have entered the evening upon the natural way of Islam, the word of sincerity, the religion of our Prophet Muhammad ﷺ, and the way of our father Ibrahim, who was upright and Muslim and was not among the polytheists.",
    "de": "Wir sind in den Abend eingetreten auf der natürlichen Veranlagung des Islam, auf dem Wort der Aufrichtigkeit, auf der Religion unseres Propheten Muhammad ﷺ und auf dem Weg unseres Vaters Ibrahim, der aufrichtig und Muslim war und nicht zu den Götzendienern gehörte.",
    "repeat_ar": "مرة واحدة",
    "repeat_en": "Once",
    "repeat_de": "Einmal",
    "source_ar": "من أذكار المساء",
    "source_en": "Evening adhkar",
    "source_de": "Abend-Adhkar",
}


# ================== TOOLS ==================

def esc(text):
    return html.escape(str(text or ""))


def line():
    return "\n━━━━━━━━━━━━━━\n"


def now_timestamp():
    return int(time.time())


def is_admin(user_id):
    return user_id == ADMIN_ID


def parse_schedule_time(value, fallback="09:00"):
    try:
        value = str(value or fallback).strip()
        hour_text, minute_text = value.split(":")
        hour = int(hour_text)
        minute = int(minute_text)

        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("Invalid time")

        return datetime.time(hour=hour, minute=minute, second=0)

    except Exception:
        fallback_hour, fallback_minute = fallback.split(":")
        return datetime.time(hour=int(fallback_hour), minute=int(fallback_minute), second=0)


def format_time_from_timestamp(ts):
    if not ts:
        return "غير متوفر"
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


# ================== DATABASE ==================

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

    c.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in c.fetchall()]
    if "adhkar_lang" not in user_cols:
        c.execute("ALTER TABLE users ADD COLUMN adhkar_lang TEXT DEFAULT 'ar'")
    if "created_at" not in user_cols:
        c.execute("ALTER TABLE users ADD COLUMN created_at INTEGER DEFAULT 0")

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


def get_adhkar_lang(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT adhkar_lang FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return "ar"

    return row[0]


def set_adhkar_lang(user_id, lang):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE users SET adhkar_lang=? WHERE user_id=?", (lang, user_id))
    conn.commit()
    conn.close()


def users_count():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count


def save_hadith(user_id, text):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO saved(user_id, text, created_at) VALUES (?, ?, ?)", (user_id, text, now_timestamp()))
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
    c.execute("SELECT text, created_at FROM saved WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
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
        c.execute("UPDATE adhkar_reminders SET morning=?, chat_id=? WHERE user_id=?", (1 if enabled else 0, chat_id, user_id))
    elif kind == "evening":
        c.execute("UPDATE adhkar_reminders SET evening=?, chat_id=? WHERE user_id=?", (1 if enabled else 0, chat_id, user_id))

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


# ================== HADITH / QURAN API ==================

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
    response = requests.get(HADEETH_API, params={"language": lang, "id": hadith_id}, timeout=15)
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


# ================== ADHKAR UI ==================

def lang_name(lang):
    if lang == "en":
        return "English"
    if lang == "de":
        return "Deutsch"
    return "العربية"


def adhkar_main_menu(user_id):
    lang = get_adhkar_lang(user_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌅 أذكار الصباح", callback_data="adhkar_morning_0")],
        [InlineKeyboardButton("🌙 أذكار المساء", callback_data="adhkar_evening_0")],
        [InlineKeyboardButton(f"🌍 لغة الأذكار: {lang_name(lang)}", callback_data="adhkar_lang_menu")],
        [InlineKeyboardButton("⏰ تذكير الأذكار", callback_data="adhkar_reminders")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def adhkar_lang_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="adhkar_lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="adhkar_lang_en")],
        [InlineKeyboardButton("🇩🇪 Deutsch", callback_data="adhkar_lang_de")],
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


def render_adhkar(kind, index, lang):
    adhkar_list = MORNING_ADHKAR if kind == "morning" else EVENING_ADHKAR
    total = len(adhkar_list)

    if index < 0:
        index = 0
    if index >= total:
        index = total - 1

    item = adhkar_list[index]

    if kind == "morning":
        title_ar = "🌅 أذكار الصباح"
        title_en = "🌅 Morning Adhkar"
        title_de = "🌅 Morgen-Adhkar"
    else:
        title_ar = "🌙 أذكار المساء"
        title_en = "🌙 Evening Adhkar"
        title_de = "🌙 Abend-Adhkar"

    if lang == "en":
        text = f"""{title_en}

<b>Dhikr {index + 1}/{total}</b>
{line()}
<b>Arabic text:</b>

{esc(item["ar"])}

{line()}
<b>Meaning in English:</b>

{esc(item["en"])}

{line()}
🔁 <b>Repeat:</b> {esc(item["repeat_en"])}
📚 <b>Source:</b> {esc(item["source_en"])}
"""
    elif lang == "de":
        text = f"""{title_de}

<b>Dhikr {index + 1}/{total}</b>
{line()}
<b>Arabischer Text:</b>

{esc(item["ar"])}

{line()}
<b>Bedeutung auf Deutsch:</b>

{esc(item["de"])}

{line()}
🔁 <b>Wiederholung:</b> {esc(item["repeat_de"])}
📚 <b>Quelle:</b> {esc(item["source_de"])}
"""
    else:
        text = f"""{title_ar}

<b>الذكر {index + 1}/{total}</b>
{line()}
{esc(item["ar"])}
{line()}
🔁 <b>التكرار:</b> {esc(item["repeat_ar"])}
📚 <b>المصدر:</b> {esc(item["source_ar"])}
"""

    return text, adhkar_navigation(kind, index, total)


# ================== MENUS ==================

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
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("✍️ إرسال رسالة مخصصة للقناة", callback_data="admin_custom_post")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


def back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]])


def admin_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ رجوع للوحة الإدارة", callback_data="admin")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home")]
    ])


# ================== SAFE SEND ==================

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


# ================== COMMANDS ==================

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


# ================== AUTO POSTS ==================

async def auto_publish_hadith(context: ContextTypes.DEFAULT_TYPE):
    text, hid = hadith_channel_message()
    await send_channel_message(context, text, "hadith", hid, "auto_hadith")


async def auto_publish_quran(context: ContextTypes.DEFAULT_TYPE):
    text, ayah_ref = quran_channel_message()
    await send_channel_message(context, text, "quran", ayah_ref, "auto_quran")


async def auto_publish_mixed(context: ContextTypes.DEFAULT_TYPE):
    text, item_id = mixed_channel_message()
    await send_channel_message(context, text, "mixed", item_id, "auto_mixed")


async def send_morning_adhkar_reminders(context: ContextTypes.DEFAULT_TYPE):
    for user_id, chat_id in get_adhkar_subscribers("morning"):
        lang = get_adhkar_lang(user_id)
        if lang == "en":
            text = "🌅 <b>Morning Adhkar Reminder</b>\n\nStart reading your morning adhkar now."
            button = "🌅 Start Morning Adhkar"
        elif lang == "de":
            text = "🌅 <b>Erinnerung an Morgen-Adhkar</b>\n\nBeginne jetzt mit deinen Morgen-Adhkar."
            button = "🌅 Morgen-Adhkar starten"
        else:
            text = "🌅 <b>تذكير أذكار الصباح</b>\n\nابدأ بقراءة أذكار الصباح الآن."
            button = "🌅 ابدأ أذكار الصباح"

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(button, callback_data="adhkar_morning_0")]]),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Morning adhkar reminder error for {user_id}: {e}")


async def send_evening_adhkar_reminders(context: ContextTypes.DEFAULT_TYPE):
    for user_id, chat_id in get_adhkar_subscribers("evening"):
        lang = get_adhkar_lang(user_id)
        if lang == "en":
            text = "🌙 <b>Evening Adhkar Reminder</b>\n\nStart reading your evening adhkar now."
            button = "🌙 Start Evening Adhkar"
        elif lang == "de":
            text = "🌙 <b>Erinnerung an Abend-Adhkar</b>\n\nBeginne jetzt mit deinen Abend-Adhkar."
            button = "🌙 Abend-Adhkar starten"
        else:
            text = "🌙 <b>تذكير أذكار المساء</b>\n\nابدأ بقراءة أذكار المساء الآن."
            button = "🌙 ابدأ أذكار المساء"

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(button, callback_data="adhkar_evening_0")]]),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Evening adhkar reminder error for {user_id}: {e}")


# ================== CALLBACK HANDLER ==================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    chat_id = q.message.chat_id
    add_user(user_id)

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
                text += f"<b>#{i}</b>\n{esc(row[0][:500])}\n\n━━━━━━━━━━━━━━\n\n"

        await safe_edit(q, text, back())

    elif data == "adhkar_menu":
        lang = get_adhkar_lang(user_id)
        await safe_edit(
            q,
            f"🤲 <b>قسم الأذكار</b>\n\n🌍 اللغة الحالية: <b>{esc(lang_name(lang))}</b>\n\nاختر ما تريد قراءته:",
            adhkar_main_menu(user_id)
        )

    elif data == "adhkar_lang_menu":
        await safe_edit(q, "🌍 <b>اختر لغة الأذكار:</b>", adhkar_lang_menu())

    elif data.startswith("adhkar_lang_"):
        lang = data.split("_")[-1]
        set_adhkar_lang(user_id, lang)
        await safe_edit(
            q,
            f"✅ تم تغيير لغة الأذكار إلى: <b>{esc(lang_name(lang))}</b>",
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
        if lang == "en":
            text = "✅ <b>Well done.</b>\n\nYou finished the morning adhkar."
        elif lang == "de":
            text = "✅ <b>Sehr gut.</b>\n\nDu hast die Morgen-Adhkar beendet."
        else:
            text = "✅ <b>أحسنت.</b>\n\nانتهيت من أذكار الصباح.\nنسأل الله أن يحفظك ويبارك يومك."
        await safe_edit(q, text, adhkar_main_menu(user_id))

    elif data == "adhkar_done_evening":
        lang = get_adhkar_lang(user_id)
        if lang == "en":
            text = "✅ <b>Well done.</b>\n\nYou finished the evening adhkar."
        elif lang == "de":
            text = "✅ <b>Sehr gut.</b>\n\nDu hast die Abend-Adhkar beendet."
        else:
            text = "✅ <b>أحسنت.</b>\n\nانتهيت من أذكار المساء.\nنسأل الله أن يحفظك في ليلتك."
        await safe_edit(q, text, adhkar_main_menu(user_id))

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

🤲 يحتوي البوت على أذكار الصباح والمساء بثلاث لغات.

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


# ================== TEXT HANDLER ==================

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


# ================== MAIN ==================

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

    app.job_queue.run_daily(auto_publish_hadith, time=parse_schedule_time(HADITH_POST_TIME, "09:00"))
    app.job_queue.run_daily(auto_publish_quran, time=parse_schedule_time(QURAN_POST_TIME, "15:00"))
    app.job_queue.run_daily(auto_publish_mixed, time=parse_schedule_time(MIXED_POST_TIME, "21:00"))

    app.job_queue.run_daily(send_morning_adhkar_reminders, time=parse_schedule_time(MORNING_ADHKAR_TIME, "06:00"))
    app.job_queue.run_daily(send_evening_adhkar_reminders, time=parse_schedule_time(EVENING_ADHKAR_TIME, "18:00"))

    print("Bot running with Adhkar in 3 languages...")
    print(f"Morning adhkar reminder: {MORNING_ADHKAR_TIME}")
    print(f"Evening adhkar reminder: {EVENING_ADHKAR_TIME}")

    app.run_polling()


if __name__ == "__main__":
    main()