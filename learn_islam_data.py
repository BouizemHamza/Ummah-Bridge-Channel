# learn_islam_data.py
# Detailed Learn Islam content for Ummah Bridge.
#
# Structure:
# LEARN_ISLAM_TOPICS[topic_id]["title"][lang]
# LEARN_ISLAM_TOPICS[topic_id]["levels"][level][lang] = list of pages
#
# Levels:
# - summary: quick short version
# - medium: balanced explanation
# - detailed: longer explanation with evidences
# - sources: references and recommended books

LEARN_ISLAM_TOPICS = {
    "what_is_islam": {
        "title": {
            "ar": "🧭 ما هو الإسلام؟",
            "en": "🧭 What is Islam?",
            "de": "🧭 Was ist Islam?",
        },
        "levels": {
            "summary": {
                "ar": [
                    """🧭 <b>ما هو الإسلام؟</b>

الإسلام هو الاستسلام لله وحده بالتوحيد، والانقياد له بالطاعة، والبراءة من الشرك وأهله.

وهو دين جميع الأنبياء من حيث الأصل: عبادة الله وحده، لكن الشريعة الخاتمة هي شريعة محمد ﷺ.

يدعو الإسلام إلى الإيمان بالله، وإقامة الصلاة، والزكاة، والصيام، والحج، وإلى الرحمة والعدل وحسن الخلق."""
                ],
                "en": [
                    """🧭 <b>What is Islam?</b>

Islam means submitting to Allah alone through monotheism, obeying Him, and rejecting shirk.

In its essence, Islam is the religion of all prophets: worship Allah alone. The final law is the message brought by Prophet Muhammad ﷺ.

Islam calls to belief in Allah, prayer, zakat, fasting, Hajj, mercy, justice, and good character."""
                ],
                "de": [
                    """🧭 <b>Was ist Islam?</b>

Islam bedeutet, sich Allah allein durch Tauhid zu ergeben, Ihm zu gehorchen und Schirk abzulehnen.

Im Ursprung ist Islam die Religion aller Propheten: Allah allein anzubeten. Die abschließende Gesetzgebung ist die Botschaft Muhammads ﷺ.

Der Islam ruft zum Glauben an Allah, Gebet, Zakat, Fasten, Hajj, Barmherzigkeit, Gerechtigkeit und gutem Charakter auf."""
                ],
            },
            "medium": {
                "ar": [
                    """🧭 <b>ما هو الإسلام؟</b>
📖 الشرح المتوسط — الصفحة 1/3

الإسلام في اللغة يدل على الاستسلام والانقياد.

وفي الشرع: هو الاستسلام لله بالتوحيد، والانقياد له بالطاعة، والبراءة من الشرك.

فالمسلم لا يعبد إلا الله، ولا يجعل العبادة لغيره: لا لنبي، ولا لولي، ولا لقبر، ولا لصنم.

قال الله تعالى:
<blockquote>إِنَّ الدِّينَ عِندَ اللَّهِ الْإِسْلَامُ</blockquote>
آل عمران: 19""",
                    """🧭 <b>ما هو الإسلام؟</b>
📖 الشرح المتوسط — الصفحة 2/3

الإسلام ليس مجرد اسم أو انتماء، بل هو عقيدة وعبادة وأخلاق.

العقيدة: الإيمان بالله وما أخبر به.
العبادة: الصلاة والصيام والزكاة والحج وسائر الطاعات.
الأخلاق: الصدق، الرحمة، العدل، الأمانة، وبر الوالدين.

وقد أكمل الله هذا الدين، قال تعالى:
<blockquote>الْيَوْمَ أَكْمَلْتُ لَكُمْ دِينَكُمْ</blockquote>
المائدة: 3""",
                    """🧭 <b>ما هو الإسلام؟</b>
📖 الشرح المتوسط — الصفحة 3/3

الإسلام هو الدين الخاتم الذي بعث الله به محمدًا ﷺ إلى الناس كافة.

ومن دخل في الإسلام نطق بالشهادتين:
أشهد أن لا إله إلا الله، وأشهد أن محمدًا رسول الله.

ومعناها: لا معبود بحق إلا الله، ومحمد ﷺ هو الرسول الذي يجب اتباعه فيما أمر، وتصديقه فيما أخبر."""
                ],
                "en": [
                    """🧭 <b>What is Islam?</b>
📖 Medium explanation — page 1/3

Linguistically, Islam is submission and surrender.

Religiously, it means submitting to Allah through monotheism, obeying Him, and rejecting shirk.

A Muslim worships Allah alone and does not direct worship to a prophet, saint, grave, idol, or any created being.

Allah says:
<blockquote>Indeed, the religion in the sight of Allah is Islam.</blockquote>
Quran 3:19""",
                    """🧭 <b>What is Islam?</b>
📖 Medium explanation — page 2/3

Islam is not only a label. It is belief, worship, and character.

Belief: faith in Allah and what He revealed.
Worship: prayer, fasting, zakat, Hajj, and obedience.
Character: truthfulness, mercy, justice, trustworthiness, and kindness to parents.

Allah says:
<blockquote>This day I have perfected for you your religion.</blockquote>
Quran 5:3""",
                    """🧭 <b>What is Islam?</b>
📖 Medium explanation — page 3/3

Islam is the final religion sent with Muhammad ﷺ to all people.

To enter Islam, one testifies:
I bear witness that none has the right to be worshipped except Allah, and I bear witness that Muhammad is the Messenger of Allah.

This means worshipping Allah alone and following the Messenger ﷺ."""
                ],
                "de": [
                    """🧭 <b>Was ist Islam?</b>
📖 Mittlere Erklärung — Seite 1/3

Sprachlich bedeutet Islam Hingabe und Unterwerfung.

Religiös bedeutet es: sich Allah durch Tauhid zu ergeben, Ihm zu gehorchen und Schirk abzulehnen.

Ein Muslim betet Allah allein an und richtet keine Anbetung an Propheten, Heilige, Gräber, Götzen oder Geschöpfe.

Allah sagt:
<blockquote>Gewiss, die Religion bei Allah ist der Islam.</blockquote>
Quran 3:19""",
                    """🧭 <b>Was ist Islam?</b>
📖 Mittlere Erklärung — Seite 2/3

Islam ist nicht nur ein Name. Er umfasst Glauben, Anbetung und Charakter.

Glaube: Glaube an Allah und Seine Offenbarung.
Anbetung: Gebet, Fasten, Zakat, Hajj und Gehorsam.
Charakter: Wahrhaftigkeit, Barmherzigkeit, Gerechtigkeit und Güte zu den Eltern.

Allah sagt:
<blockquote>Heute habe Ich euch eure Religion vervollkommnet.</blockquote>
Quran 5:3""",
                    """🧭 <b>Was ist Islam?</b>
📖 Mittlere Erklärung — Seite 3/3

Islam ist die abschließende Religion, die mit Muhammad ﷺ zu allen Menschen gesandt wurde.

Wer in den Islam eintritt, bezeugt:
Ich bezeuge, dass niemand das Recht hat, angebetet zu werden, außer Allah, und ich bezeuge, dass Muhammad der Gesandte Allahs ist.

Das bedeutet: Allah allein anbeten und dem Gesandten ﷺ folgen."""
                ],
            },
            "detailed": {
                "ar": [
                    """🧭 <b>ما هو الإسلام؟</b>
📚 الشرح المفصل — الصفحة 1/6

الإسلام يقوم على أصل عظيم: توحيد الله.

والتوحيد هو إفراد الله بالعبادة، فلا يُدعى إلا الله، ولا يُستغاث إلا به فيما لا يقدر عليه إلا هو، ولا يُذبح ولا يُنذر إلا له.

هذا هو أصل دعوة الأنبياء جميعًا.

قال الله تعالى:
<blockquote>وَمَا أَرْسَلْنَا مِن قَبْلِكَ مِن رَّسُولٍ إِلَّا نُوحِي إِلَيْهِ أَنَّهُ لَا إِلَٰهَ إِلَّا أَنَا فَاعْبُدُونِ</blockquote>
الأنبياء: 25""",
                    """🧭 <b>ما هو الإسلام؟</b>
📚 الشرح المفصل — الصفحة 2/6

الإسلام دين الأنبياء من حيث التوحيد، لكن الشرائع قد تختلف.

فنوح وإبراهيم وموسى وعيسى ومحمد عليهم الصلاة والسلام كلهم دعوا إلى عبادة الله وحده.

أما شريعة محمد ﷺ فهي الشريعة الخاتمة التي نسخت ما قبلها، وهي للناس جميعًا.

قال الله تعالى:
<blockquote>وَمَا أَرْسَلْنَاكَ إِلَّا كَافَّةً لِّلنَّاسِ بَشِيرًا وَنَذِيرًا</blockquote>
سبأ: 28""",
                    """🧭 <b>ما هو الإسلام؟</b>
📚 الشرح المفصل — الصفحة 3/6

الإسلام يشمل العقيدة والعبادة والمعاملة.

العقيدة: أن تؤمن بالله وملائكته وكتبه ورسله واليوم الآخر والقدر.

العبادة: أن تعبد الله بما شرع، مثل الصلاة والزكاة والصيام والحج والدعاء.

المعاملة: أن تتعامل بالعدل والرحمة والصدق والأمانة، وأن تترك الظلم والخيانة والكذب.""",
                    """🧭 <b>ما هو الإسلام؟</b>
📚 الشرح المفصل — الصفحة 4/6

بيّن النبي ﷺ الإسلام في حديث جبريل المشهور.

لما سأله جبريل عن الإسلام قال:
<blockquote>الإسلام أن تشهد أن لا إله إلا الله وأن محمدًا رسول الله، وتقيم الصلاة، وتؤتي الزكاة، وتصوم رمضان، وتحج البيت إن استطعت إليه سبيلًا.</blockquote>

وهذا الحديث أصل عظيم في بيان مراتب الدين: الإسلام، والإيمان، والإحسان.""",
                    """🧭 <b>ما هو الإسلام؟</b>
📚 الشرح المفصل — الصفحة 5/6

الإسلام يجمع بين حق الله وحقوق الخلق.

حق الله: أن يعبد وحده لا شريك له.
وحقوق الخلق: الرحمة، العدل، الإحسان، بر الوالدين، صلة الرحم، حفظ الحقوق، والبعد عن الأذى.

ولهذا لا يكون التدين صحيحًا إذا انفصل عن الأخلاق.

قال النبي ﷺ:
<blockquote>إنما بعثت لأتمم صالح الأخلاق.</blockquote>""",
                    """🧭 <b>ما هو الإسلام؟</b>
📚 الشرح المفصل — الصفحة 6/6

خلاصة الدرس:

الإسلام هو عبادة الله وحده، واتباع رسوله محمد ﷺ، والعمل بما أمر الله، وترك ما نهى عنه.

وهو دين هداية ورحمة وعدل، لا يقوم على مجرد الشعارات، بل على الإيمان الصادق والعمل الصالح وحسن الخلق.

ومن أراد فهم الإسلام فليبدأ بالقرآن، وبالسنة الصحيحة، وبالعلم عن أهل العلم الموثوقين."""
                ],
                "en": [
                    """🧭 <b>What is Islam?</b>
📚 Detailed explanation — page 1/6

Islam is built upon a great foundation: Tawhid, the oneness of Allah.

Tawhid means singling out Allah alone in worship. Supplication, sacrifice, vows, and ultimate reliance are for Allah alone.

This was the core message of all prophets.

Allah says:
<blockquote>And We sent not before you any messenger except that We revealed to him that there is no deity except Me, so worship Me.</blockquote>
Quran 21:25""",
                    """🧭 <b>What is Islam?</b>
📚 Detailed explanation — page 2/6

Islam is the religion of all prophets in its foundation of monotheism, although laws differed.

Noah, Abraham, Moses, Jesus, and Muhammad, peace be upon them, all called to worship Allah alone.

The law of Muhammad ﷺ is the final law sent to all people.

Allah says:
<blockquote>And We have not sent you except to all mankind as a bringer of good news and a warner.</blockquote>
Quran 34:28""",
                    """🧭 <b>What is Islam?</b>
📚 Detailed explanation — page 3/6

Islam includes belief, worship, and conduct.

Belief: faith in Allah, His angels, His books, His messengers, the Last Day, and divine decree.

Worship: worshipping Allah as He legislated, including prayer, zakat, fasting, Hajj, and supplication.

Conduct: justice, mercy, truthfulness, trustworthiness, and avoiding oppression, betrayal, and lies.""",
                    """🧭 <b>What is Islam?</b>
📚 Detailed explanation — page 4/6

The Prophet ﷺ explained Islam in the famous Hadith of Jibril.

When Jibril asked about Islam, the Prophet ﷺ said:
<blockquote>Islam is to testify that none has the right to be worshipped except Allah and that Muhammad is the Messenger of Allah, to establish prayer, give zakat, fast Ramadan, and perform Hajj if you are able.</blockquote>

This hadith explains the levels of the religion: Islam, Iman, and Ihsan.""",
                    """🧭 <b>What is Islam?</b>
📚 Detailed explanation — page 5/6

Islam combines the right of Allah and the rights of creation.

The right of Allah is that He alone is worshipped without partners.

The rights of creation include mercy, justice, kindness to parents, maintaining family ties, protecting rights, and avoiding harm.

True religiosity cannot be separated from good character.""",
                    """🧭 <b>What is Islam?</b>
📚 Detailed explanation — page 6/6

Summary:

Islam is worshipping Allah alone, following His Messenger Muhammad ﷺ, doing what Allah commands, and avoiding what He forbids.

It is a religion of guidance, mercy, and justice. It is not merely slogans, but sincere faith, righteous action, and good character.

To understand Islam, begin with the Quran, authentic Sunnah, and trustworthy scholarship."""
                ],
                "de": [
                    """🧭 <b>Was ist Islam?</b>
📚 Ausführliche Erklärung — Seite 1/6

Der Islam baut auf einer großen Grundlage auf: Tauhid, der Einzigkeit Allahs.

Tauhid bedeutet, Allah allein in der Anbetung zu widmen. Bittgebet, Opfer, Gelübde und endgültiges Vertrauen gelten Allah allein.

Dies war die Kernbotschaft aller Propheten.

Allah sagt:
<blockquote>Und Wir sandten vor dir keinen Gesandten, dem Wir nicht offenbarten: Es gibt keinen Gott außer Mir, so dient Mir.</blockquote>
Quran 21:25""",
                    """🧭 <b>Was ist Islam?</b>
📚 Ausführliche Erklärung — Seite 2/6

Islam ist in seiner Grundlage des Tauhid die Religion aller Propheten, auch wenn sich einzelne Gesetzgebungen unterschieden.

Noah, Abraham, Moses, Jesus und Muhammad, Friede sei mit ihnen, riefen alle dazu auf, Allah allein anzubeten.

Die Gesetzgebung Muhammads ﷺ ist die abschließende Botschaft für alle Menschen.

Allah sagt:
<blockquote>Und Wir haben dich nur zu allen Menschen gesandt als Verkünder froher Botschaft und Warner.</blockquote>
Quran 34:28""",
                    """🧭 <b>Was ist Islam?</b>
📚 Ausführliche Erklärung — Seite 3/6

Islam umfasst Glauben, Anbetung und Verhalten.

Glaube: Glaube an Allah, Seine Engel, Seine Bücher, Seine Gesandten, den Jüngsten Tag und die Vorherbestimmung.

Anbetung: Allah so dienen, wie Er es vorgeschrieben hat: Gebet, Zakat, Fasten, Hajj und Bittgebet.

Verhalten: Gerechtigkeit, Barmherzigkeit, Wahrhaftigkeit und Vertrauenswürdigkeit.""",
                    """🧭 <b>Was ist Islam?</b>
📚 Ausführliche Erklärung — Seite 4/6

Der Prophet ﷺ erklärte den Islam im berühmten Hadith von Jibril.

Als Jibril nach dem Islam fragte, sagte der Prophet ﷺ:
<blockquote>Islam ist, dass du bezeugst, dass niemand das Recht hat, angebetet zu werden, außer Allah, und dass Muhammad der Gesandte Allahs ist; dass du das Gebet verrichtest, Zakat gibst, Ramadan fastest und Hajj verrichtest, wenn du dazu imstande bist.</blockquote>

Dieser Hadith erklärt die Stufen der Religion: Islam, Iman und Ihsan.""",
                    """🧭 <b>Was ist Islam?</b>
📚 Ausführliche Erklärung — Seite 5/6

Islam verbindet das Recht Allahs und die Rechte der Menschen.

Das Recht Allahs ist, dass Er allein ohne Teilhaber angebetet wird.

Zu den Rechten der Menschen gehören Barmherzigkeit, Gerechtigkeit, Güte zu den Eltern, Pflege der Verwandtschaft, Schutz der Rechte und das Vermeiden von Schaden.

Wahre Religiosität kann nicht von gutem Charakter getrennt werden.""",
                    """🧭 <b>Was ist Islam?</b>
📚 Ausführliche Erklärung — Seite 6/6

Zusammenfassung:

Islam bedeutet, Allah allein anzubeten, Seinem Gesandten Muhammad ﷺ zu folgen, Allahs Gebote umzusetzen und Seine Verbote zu meiden.

Er ist eine Religion der Rechtleitung, Barmherzigkeit und Gerechtigkeit. Er besteht nicht nur aus Worten, sondern aus aufrichtigem Glauben, guten Taten und gutem Charakter.

Wer Islam verstehen möchte, beginnt mit Quran, authentischer Sunnah und vertrauenswürdigem Wissen."""
                ],
            },
            "sources": {
                "ar": [
                    """📚 <b>مصادر درس: ما هو الإسلام؟</b>

<b>من القرآن الكريم:</b>
• آل عمران: 19
• المائدة: 3
• الأنبياء: 25
• سبأ: 28

<b>من السنة:</b>
• حديث جبريل في صحيح مسلم
• حديث: «بني الإسلام على خمس» في الصحيحين

<b>كتب نافعة:</b>
• شرح الأصول الثلاثة
• الأربعون النووية
• رياض الصالحين
• كتاب التوحيد"""
                ],
                "en": [
                    """📚 <b>Sources: What is Islam?</b>

<b>From the Quran:</b>
• Quran 3:19
• Quran 5:3
• Quran 21:25
• Quran 34:28

<b>From the Sunnah:</b>
• Hadith of Jibril in Sahih Muslim
• Hadith: “Islam is built upon five” in Bukhari and Muslim

<b>Useful books:</b>
• Explanation of the Three Fundamental Principles
• Forty Hadith of Imam Nawawi
• Riyad as-Salihin
• Kitab at-Tawhid"""
                ],
                "de": [
                    """📚 <b>Quellen: Was ist Islam?</b>

<b>Aus dem Quran:</b>
• Quran 3:19
• Quran 5:3
• Quran 21:25
• Quran 34:28

<b>Aus der Sunnah:</b>
• Hadith von Jibril in Sahih Muslim
• Hadith: „Islam ist auf fünf gebaut“ in Bukhari und Muslim

<b>Nützliche Bücher:</b>
• Erklärung der drei Grundprinzipien
• Die vierzig Hadithe von Imam an-Nawawi
• Riyad as-Salihin
• Kitab at-Tawhid"""
                ],
            },
        },
    },

    "pillars_islam": {
        "title": {
            "ar": "🕋 أركان الإسلام",
            "en": "🕋 Pillars of Islam",
            "de": "🕋 Säulen des Islam",
        },
        "levels": {
            "summary": {
                "ar": ["""🕋 <b>أركان الإسلام</b>

أركان الإسلام خمسة:
1. الشهادتان
2. الصلاة
3. الزكاة
4. صوم رمضان
5. حج البيت لمن استطاع إليه سبيلًا

هذه الأركان هي الأساس العملي الظاهر للإسلام."""],
                "en": ["""🕋 <b>The Pillars of Islam</b>

The pillars of Islam are five:
1. The testimony of faith
2. Prayer
3. Zakat
4. Fasting Ramadan
5. Hajj for those who are able

These pillars are the visible practical foundation of Islam."""],
                "de": ["""🕋 <b>Die Säulen des Islam</b>

Die Säulen des Islam sind fünf:
1. Das Glaubensbekenntnis
2. Das Gebet
3. Zakat
4. Fasten im Ramadan
5. Hajj für diejenigen, die dazu fähig sind

Diese Säulen sind die sichtbare praktische Grundlage des Islam."""],
            },
            "medium": {
                "ar": [
                    """🕋 <b>أركان الإسلام</b>
📖 الشرح المتوسط — الصفحة 1/3

الأركان هي الأسس التي يقوم عليها البناء.

وقد قال النبي ﷺ:
<blockquote>بني الإسلام على خمس...</blockquote>

فالإسلام له أصل قلبي وهو الإيمان، وله أعمال ظاهرة عظيمة، وأعظمها هذه الأركان الخمسة.""",
                    """🕋 <b>أركان الإسلام</b>
📖 الشرح المتوسط — الصفحة 2/3

الشهادتان هما باب الدخول في الإسلام.

الصلاة أعظم عبادة بدنية متكررة، وهي صلة بين العبد وربه.

الزكاة تطهير للمال والنفس، ومساعدة للفقراء والمحتاجين.""",
                    """🕋 <b>أركان الإسلام</b>
📖 الشرح المتوسط — الصفحة 3/3

صيام رمضان عبادة تجمع الصبر والتقوى ومجاهدة النفس.

والحج عبادة عظيمة لمن استطاع، يجتمع فيها التوحيد، والذكر، والطاعة، والأخوة بين المسلمين."""
                ],
                "en": [
                    """🕋 <b>Pillars of Islam</b>
📖 Medium explanation — page 1/3

Pillars are the foundations upon which a building stands.

The Prophet ﷺ said:
<blockquote>Islam is built upon five...</blockquote>

Islam has inner faith and major outward actions. The greatest outward foundations are these five pillars.""",
                    """🕋 <b>Pillars of Islam</b>
📖 Medium explanation — page 2/3

The two testimonies are the entrance into Islam.

Prayer is the greatest repeated physical act of worship and a connection between the servant and Allah.

Zakat purifies wealth and the soul and supports the poor and needy.""",
                    """🕋 <b>Pillars of Islam</b>
📖 Medium explanation — page 3/3

Fasting Ramadan teaches patience, taqwa, and self-discipline.

Hajj is a great act of worship for those able to perform it. It includes monotheism, remembrance, obedience, and Muslim brotherhood."""
                ],
                "de": [
                    """🕋 <b>Säulen des Islam</b>
📖 Mittlere Erklärung — Seite 1/3

Säulen sind die Grundlagen, auf denen ein Gebäude steht.

Der Prophet ﷺ sagte:
<blockquote>Islam ist auf fünf gebaut...</blockquote>

Der Islam hat inneren Glauben und wichtige äußere Handlungen. Die größten äußeren Grundlagen sind diese fünf Säulen.""",
                    """🕋 <b>Säulen des Islam</b>
📖 Mittlere Erklärung — Seite 2/3

Die beiden Glaubenszeugnisse sind der Eintritt in den Islam.

Das Gebet ist die größte wiederkehrende körperliche Anbetung und eine Verbindung zwischen dem Diener und Allah.

Zakat reinigt Besitz und Seele und unterstützt Arme und Bedürftige.""",
                    """🕋 <b>Säulen des Islam</b>
📖 Mittlere Erklärung — Seite 3/3

Das Fasten im Ramadan lehrt Geduld, Taqwa und Selbstdisziplin.

Hajj ist eine große Anbetung für diejenigen, die dazu fähig sind. Sie umfasst Tauhid, Gedenken, Gehorsam und muslimische Brüderlichkeit."""
                ],
            },
            "detailed": {
                "ar": [
                    """🕋 <b>أركان الإسلام</b>
📚 الشرح المفصل — الصفحة 1/5

قال النبي ﷺ:
<blockquote>بني الإسلام على خمس: شهادة أن لا إله إلا الله وأن محمدًا رسول الله، وإقام الصلاة، وإيتاء الزكاة، والحج، وصوم رمضان.</blockquote>

هذا الحديث أصل في بيان أعمال الإسلام الظاهرة.""",
                    """🕋 <b>الركن الأول: الشهادتان</b>
📚 الصفحة 2/5

معنى لا إله إلا الله: لا معبود بحق إلا الله.

ومعنى محمد رسول الله: تصديقه فيما أخبر، وطاعته فيما أمر، واجتناب ما نهى عنه وزجر، وألا يعبد الله إلا بما شرع.""",
                    """🕋 <b>الركن الثاني والثالث</b>
📚 الصفحة 3/5

الصلاة عمود الدين، وهي أول ما يحاسب عليه العبد من عمله يوم القيامة.

والزكاة حق واجب في المال، تؤخذ من الأغنياء وترد على الفقراء، وفيها تطهير للنفس والمال.""",
                    """🕋 <b>الركن الرابع والخامس</b>
📚 الصفحة 4/5

صوم رمضان فرض على المسلمين، وهو إمساك عن المفطرات من طلوع الفجر إلى غروب الشمس بنية العبادة.

والحج فرض مرة في العمر على المستطيع، وهو من أعظم شعائر الإسلام.""",
                    """🕋 <b>خلاصة أركان الإسلام</b>
📚 الصفحة 5/5

هذه الأركان ليست كل الإسلام، لكنها أعظم مبانيه الظاهرة.

فالمسلم يجمع بين العقيدة الصحيحة، والعبادة، وحسن الخلق، والبعد عن المحرمات."""
                ],
                "en": [
                    """🕋 <b>Pillars of Islam</b>
📚 Detailed explanation — page 1/5

The Prophet ﷺ said:
<blockquote>Islam is built upon five: testifying that none has the right to be worshipped except Allah and that Muhammad is the Messenger of Allah, establishing prayer, giving zakat, Hajj, and fasting Ramadan.</blockquote>

This hadith is a foundation for the outward actions of Islam.""",
                    """🕋 <b>The first pillar: the testimonies</b>
📚 Page 2/5

The meaning of “La ilaha illa Allah” is: none has the right to be worshipped except Allah.

The meaning of “Muhammad is the Messenger of Allah” is to believe what he reported, obey what he commanded, avoid what he forbade, and worship Allah only as he taught.""",
                    """🕋 <b>The second and third pillars</b>
📚 Page 3/5

Prayer is the pillar of the religion and the first deed a person will be asked about on the Day of Judgment.

Zakat is an obligatory right in wealth. It supports the poor and purifies wealth and the soul.""",
                    """🕋 <b>The fourth and fifth pillars</b>
📚 Page 4/5

Fasting Ramadan is obligatory upon Muslims. It means abstaining from things that break the fast from dawn to sunset with the intention of worship.

Hajj is obligatory once in a lifetime for those able to perform it.""",
                    """🕋 <b>Summary of the pillars</b>
📚 Page 5/5

These pillars are not all of Islam, but they are its greatest outward foundations.

A Muslim combines correct belief, worship, good character, and avoidance of sins."""
                ],
                "de": [
                    """🕋 <b>Säulen des Islam</b>
📚 Ausführliche Erklärung — Seite 1/5

Der Prophet ﷺ sagte:
<blockquote>Islam ist auf fünf gebaut: dem Zeugnis, dass niemand das Recht hat, angebetet zu werden, außer Allah und dass Muhammad der Gesandte Allahs ist; dem Gebet, der Zakat, dem Hajj und dem Fasten im Ramadan.</blockquote>

Dieser Hadith ist eine Grundlage für die äußeren Handlungen des Islam.""",
                    """🕋 <b>Die erste Säule: die Glaubenszeugnisse</b>
📚 Seite 2/5

Die Bedeutung von „La ilaha illa Allah“ ist: Niemand hat das Recht, angebetet zu werden, außer Allah.

Die Bedeutung von „Muhammad ist der Gesandte Allahs“ ist: ihm glauben, ihm gehorchen, seine Verbote meiden und Allah nur so anbeten, wie er es lehrte.""",
                    """🕋 <b>Die zweite und dritte Säule</b>
📚 Seite 3/5

Das Gebet ist die Säule der Religion und die erste Tat, nach der der Mensch am Tag des Gerichts gefragt wird.

Zakat ist ein verpflichtendes Recht im Besitz. Sie hilft den Armen und reinigt Besitz und Seele.""",
                    """🕋 <b>Die vierte und fünfte Säule</b>
📚 Seite 4/5

Das Fasten im Ramadan ist Pflicht für Muslime. Es bedeutet, von Morgendämmerung bis Sonnenuntergang mit Gottesdienstabsicht auf Fastenbrechendes zu verzichten.

Hajj ist einmal im Leben Pflicht für den, der dazu fähig ist.""",
                    """🕋 <b>Zusammenfassung der Säulen</b>
📚 Seite 5/5

Diese Säulen sind nicht der gesamte Islam, aber seine größten äußeren Grundlagen.

Ein Muslim verbindet korrekten Glauben, Anbetung, guten Charakter und das Meiden von Sünden."""
                ],
            },
            "sources": {
                "ar": ["""📚 <b>مصادر درس: أركان الإسلام</b>

• حديث «بني الإسلام على خمس» في صحيح البخاري وصحيح مسلم
• حديث جبريل في صحيح مسلم
• القرآن الكريم: البقرة 43، البقرة 183، آل عمران 97
• الأربعون النووية، الحديث الثالث"""],
                "en": ["""📚 <b>Sources: Pillars of Islam</b>

• Hadith “Islam is built upon five” in Sahih al-Bukhari and Sahih Muslim
• Hadith of Jibril in Sahih Muslim
• Quran: 2:43, 2:183, 3:97
• Forty Hadith of Imam Nawawi, Hadith 3"""],
                "de": ["""📚 <b>Quellen: Säulen des Islam</b>

• Hadith „Islam ist auf fünf gebaut“ in Sahih al-Bukhari und Sahih Muslim
• Hadith von Jibril in Sahih Muslim
• Quran: 2:43, 2:183, 3:97
• Vierzig Hadithe von Imam an-Nawawi, Hadith 3"""],
            },
        },
    },

    "pillars_iman": {
        "title": {
            "ar": "✨ أركان الإيمان",
            "en": "✨ Pillars of Faith",
            "de": "✨ Säulen des Glaubens",
        },
        "levels": {
            "summary": {
                "ar": ["""✨ <b>أركان الإيمان</b>

أركان الإيمان ستة:
1. الإيمان بالله
2. ملائكته
3. كتبه
4. رسله
5. اليوم الآخر
6. القدر خيره وشره

هذه الأصول هي أساس عقيدة المسلم."""],
                "en": ["""✨ <b>The Pillars of Faith</b>

The pillars of faith are six:
1. Belief in Allah
2. His angels
3. His books
4. His messengers
5. The Last Day
6. Divine decree, its good and its bad

These foundations are the basis of Muslim belief."""],
                "de": ["""✨ <b>Die Säulen des Glaubens</b>

Die Säulen des Glaubens sind sechs:
1. Glaube an Allah
2. Seine Engel
3. Seine Bücher
4. Seine Gesandten
5. Den Jüngsten Tag
6. Die Vorherbestimmung, das Gute und Schlechte davon

Diese Grundlagen bilden die Basis des muslimischen Glaubens."""],
            },
            "medium": {
                "ar": [
                    """✨ <b>أركان الإيمان</b>
📖 الشرح المتوسط — الصفحة 1/3

الإيمان ليس مجرد معرفة، بل هو تصديق القلب، وقول اللسان، وعمل الجوارح.

يزيد بالطاعة وينقص بالمعصية.

وأصول الإيمان الستة جاءت في حديث جبريل المشهور.""",
                    """✨ <b>الإيمان بالله وملائكته وكتبه ورسله</b>
📖 الصفحة 2/3

الإيمان بالله يشمل الإيمان بوجوده وربوبيته وألوهيته وأسمائه وصفاته.

والإيمان بالملائكة أنهم عباد مكرمون خلقهم الله من نور.

والإيمان بالكتب والرسل يعني التصديق بما أنزل الله وبمن أرسلهم لهداية الناس.""",
                    """✨ <b>اليوم الآخر والقدر</b>
📖 الصفحة 3/3

الإيمان باليوم الآخر يشمل البعث والحساب والجنة والنار.

والإيمان بالقدر يعني أن الله علم كل شيء، وكتبه، وشاءه، وخلقه، مع إثبات مسؤولية الإنسان عن اختياره."""
                ],
                "en": [
                    """✨ <b>Pillars of Faith</b>
📖 Medium explanation — page 1/3

Faith is not merely knowledge. It is belief in the heart, speech of the tongue, and actions of the limbs.

It increases with obedience and decreases with sin.

The six foundations of faith are mentioned in the famous Hadith of Jibril.""",
                    """✨ <b>Belief in Allah, angels, books, and messengers</b>
📖 Page 2/3

Belief in Allah includes belief in His existence, lordship, right to be worshipped, names, and attributes.

Belief in angels means believing they are honored servants created by Allah.

Belief in books and messengers means accepting what Allah revealed and those He sent to guide people.""",
                    """✨ <b>The Last Day and divine decree</b>
📖 Page 3/3

Belief in the Last Day includes resurrection, judgment, Paradise, and Hell.

Belief in divine decree means Allah knew everything, wrote it, willed it, and created it, while humans remain responsible for their choices."""
                ],
                "de": [
                    """✨ <b>Säulen des Glaubens</b>
📖 Mittlere Erklärung — Seite 1/3

Glaube ist nicht nur Wissen. Er umfasst Überzeugung im Herzen, Worte der Zunge und Taten der Glieder.

Er nimmt durch Gehorsam zu und durch Sünden ab.

Die sechs Grundlagen des Glaubens werden im berühmten Hadith von Jibril erwähnt.""",
                    """✨ <b>Glaube an Allah, Engel, Bücher und Gesandte</b>
📖 Seite 2/3

Der Glaube an Allah umfasst den Glauben an Seine Existenz, Herrschaft, Anbetungswürdigkeit, Namen und Eigenschaften.

Der Glaube an Engel bedeutet zu glauben, dass sie geehrte Diener sind, die Allah erschaffen hat.

Der Glaube an Bücher und Gesandte bedeutet, die Offenbarung Allahs und Seine Gesandten anzunehmen.""",
                    """✨ <b>Der Jüngste Tag und Vorherbestimmung</b>
📖 Seite 3/3

Der Glaube an den Jüngsten Tag umfasst Auferstehung, Abrechnung, Paradies und Hölle.

Der Glaube an die Vorherbestimmung bedeutet, dass Allah alles wusste, niederschrieb, wollte und erschuf, während der Mensch für seine Entscheidungen verantwortlich bleibt."""
                ],
            },
            "detailed": {
                "ar": [
                    """✨ <b>أركان الإيمان</b>
📚 الشرح المفصل — الصفحة 1/6

في حديث جبريل لما سأل عن الإيمان قال النبي ﷺ:
<blockquote>أن تؤمن بالله، وملائكته، وكتبه، ورسله، واليوم الآخر، وتؤمن بالقدر خيره وشره.</blockquote>

فهذا الحديث أصل في بيان العقيدة.""",
                    """✨ <b>الإيمان بالله</b>
📚 الصفحة 2/6

الإيمان بالله يشمل:
• الإيمان بوجوده
• الإيمان بربوبيته
• الإيمان بألوهيته
• الإيمان بأسمائه وصفاته

والله سبحانه ليس كمثله شيء، وهو السميع البصير.""",
                    """✨ <b>الإيمان بالملائكة والكتب</b>
📚 الصفحة 3/6

الملائكة خلق عظيم من خلق الله، لا يعصون الله ما أمرهم ويفعلون ما يؤمرون.

والكتب هي ما أنزله الله على رسله، ومنها التوراة والإنجيل والزبور والقرآن.

والقرآن هو الكتاب الخاتم المحفوظ.""",
                    """✨ <b>الإيمان بالرسل</b>
📚 الصفحة 4/6

الرسل بشر اصطفاهم الله لتبليغ وحيه.

نؤمن بمن سمّى الله منهم ومن لم يسمّ، ونؤمن أن محمدًا ﷺ خاتمهم.

قال تعالى:
<blockquote>مَّا كَانَ مُحَمَّدٌ أَبَا أَحَدٍ مِّن رِّجَالِكُمْ وَلَٰكِن رَّسُولَ اللَّهِ وَخَاتَمَ النَّبِيِّينَ</blockquote>
الأحزاب: 40""",
                    """✨ <b>الإيمان باليوم الآخر</b>
📚 الصفحة 5/6

يشمل الإيمان بالبعث بعد الموت، والحساب، والميزان، والصراط، والجنة والنار.

وهذا الإيمان يجعل الإنسان يراقب أعماله، ويستعد للقاء الله.""",
                    """✨ <b>الإيمان بالقدر</b>
📚 الصفحة 6/6

الإيمان بالقدر يشمل أربع مراتب:
• علم الله بكل شيء
• كتابته للمقادير
• مشيئته النافذة
• خلقه لكل شيء

وهذا لا يعني أن الإنسان مجبور بلا اختيار، بل له إرادة وعمل، والله يحاسبه على اختياره."""
                ],
                "en": [
                    """✨ <b>Pillars of Faith</b>
📚 Detailed explanation — page 1/6

In the Hadith of Jibril, when asked about faith, the Prophet ﷺ said:
<blockquote>It is to believe in Allah, His angels, His books, His messengers, the Last Day, and to believe in divine decree, its good and its bad.</blockquote>

This hadith is a foundation for Islamic belief.""",
                    """✨ <b>Belief in Allah</b>
📚 Page 2/6

Belief in Allah includes:
• Belief in His existence
• Belief in His lordship
• Belief that He alone deserves worship
• Belief in His names and attributes

There is nothing like Allah, and He is the All-Hearing, the All-Seeing.""",
                    """✨ <b>Belief in angels and books</b>
📚 Page 3/6

Angels are a great creation of Allah. They do not disobey Him and do what they are commanded.

The books are revelations Allah sent to His messengers, including the Torah, Gospel, Psalms, and Quran.

The Quran is the final preserved book.""",
                    """✨ <b>Belief in messengers</b>
📚 Page 4/6

Messengers are humans chosen by Allah to convey His revelation.

We believe in those Allah named and those He did not name, and we believe Muhammad ﷺ is the final messenger.

Allah says:
<blockquote>Muhammad is not the father of any of your men, but he is the Messenger of Allah and the seal of the prophets.</blockquote>
Quran 33:40""",
                    """✨ <b>Belief in the Last Day</b>
📚 Page 5/6

This includes belief in resurrection after death, judgment, the scale, the bridge, Paradise, and Hell.

This belief makes a person watch their deeds and prepare to meet Allah.""",
                    """✨ <b>Belief in divine decree</b>
📚 Page 6/6

Belief in decree includes four levels:
• Allah’s knowledge of everything
• His writing of all decrees
• His will
• His creation of everything

This does not mean humans are forced without choice. Humans have will and action, and Allah judges them for their choices."""
                ],
                "de": [
                    """✨ <b>Säulen des Glaubens</b>
📚 Ausführliche Erklärung — Seite 1/6

Im Hadith von Jibril sagte der Prophet ﷺ auf die Frage nach Iman:
<blockquote>Dass du an Allah, Seine Engel, Seine Bücher, Seine Gesandten, den Jüngsten Tag und an die Vorherbestimmung glaubst, das Gute und das Schlechte davon.</blockquote>

Dieser Hadith ist eine Grundlage der islamischen Glaubenslehre.""",
                    """✨ <b>Glaube an Allah</b>
📚 Seite 2/6

Der Glaube an Allah umfasst:
• Glaube an Seine Existenz
• Glaube an Seine Herrschaft
• Glaube, dass Er allein Anbetung verdient
• Glaube an Seine Namen und Eigenschaften

Nichts ist Allah gleich, und Er ist der Allhörende, der Allsehende.""",
                    """✨ <b>Glaube an Engel und Bücher</b>
📚 Seite 3/6

Engel sind eine große Schöpfung Allahs. Sie widersetzen sich Allah nicht und tun, was ihnen befohlen wird.

Die Bücher sind Offenbarungen, die Allah Seinen Gesandten sandte, darunter Tora, Evangelium, Psalmen und Quran.

Der Quran ist das abschließende bewahrte Buch.""",
                    """✨ <b>Glaube an Gesandte</b>
📚 Seite 4/6

Gesandte sind Menschen, die Allah zur Übermittlung Seiner Offenbarung auswählte.

Wir glauben an diejenigen, die Allah nannte, und an diejenigen, die Er nicht nannte. Muhammad ﷺ ist der letzte Gesandte.

Allah sagt:
<blockquote>Muhammad ist nicht der Vater eines eurer Männer, sondern Allahs Gesandter und das Siegel der Propheten.</blockquote>
Quran 33:40""",
                    """✨ <b>Glaube an den Jüngsten Tag</b>
📚 Seite 5/6

Dazu gehört der Glaube an Auferstehung, Abrechnung, Waage, Brücke, Paradies und Hölle.

Dieser Glaube lässt den Menschen seine Taten prüfen und sich auf die Begegnung mit Allah vorbereiten.""",
                    """✨ <b>Glaube an die Vorherbestimmung</b>
📚 Seite 6/6

Der Glaube an die Vorherbestimmung umfasst vier Stufen:
• Allahs Wissen über alles
• Seine Niederschrift aller Dinge
• Seinen Willen
• Seine Erschaffung von allem

Das bedeutet nicht, dass der Mensch ohne Wahl gezwungen ist. Der Mensch hat Willen und Handlung, und Allah richtet ihn nach seinen Entscheidungen."""
                ],
            },
            "sources": {
                "ar": ["""📚 <b>مصادر درس: أركان الإيمان</b>

• حديث جبريل في صحيح مسلم
• القرآن الكريم: البقرة 177، النساء 136، الأحزاب 40، الشورى 11
• العقيدة الواسطية
• شرح أصول الإيمان
• الأربعون النووية، الحديث الثاني"""],
                "en": ["""📚 <b>Sources: Pillars of Faith</b>

• Hadith of Jibril in Sahih Muslim
• Quran: 2:177, 4:136, 33:40, 42:11
• Al-Aqidah al-Wasitiyyah
• Explanation of the Foundations of Faith
• Forty Hadith of Imam Nawawi, Hadith 2"""],
                "de": ["""📚 <b>Quellen: Säulen des Glaubens</b>

• Hadith von Jibril in Sahih Muslim
• Quran: 2:177, 4:136, 33:40, 42:11
• Al-Aqidah al-Wasitiyyah
• Erklärung der Grundlagen des Glaubens
• Vierzig Hadithe von Imam an-Nawawi, Hadith 2"""],
            },
        },
    },
}
