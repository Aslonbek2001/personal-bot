# Bot qayta tuzilishi — reja

Maqsad — hozirgi bitta foydalanuvchili ingliz tili botini uch yo'nalishli, ko'p mavzuli va keyinchalik boshqa foydalanuvchilarga ochiladigan platformaga aylantirish. Kod bir marta, to'g'ri tuzilmada yoziladi.

**Asosiy tamoyillar:**
1. **Mazmun kodda emas.** Yangi til, yo'nalish yoki mavzu qo'shish uchun `content/` ga papka yoki fayl qo'shiladi, kod o'zgartirilmaydi.
2. **Bitta kod — ko'p fan.** English va Russian bitta "til" kodida ishlaydi. Programming esa "bilim" turidagi kodda ishlaydi. Keyinchalik yangi til yoki fan qo'shish uchun kod yozish shart emas.
3. **Hamma narsa foydalanuvchiga bog'langan.** Bazadagi har bir shaxsiy yozuvda `user_id` bo'ladi. Umumiy keshlar (tushuntirishlar, darslar, ovozlar) esa foydalanuvchilar o'rtasida bo'lishiladi va tokenni tejaydi.
4. **AI faqat kerak joyda.** Python bajara oladigan ishni Python bajaradi: Writing tekshiruvi, Speaking'dagi o'qish tahlili, takrorlash jadvali. AI natijasi keshlanadi.

---

## 1. Menyu

**Asosiy menyu** `content/` dagi fanlardan avtomatik tuziladi:

```
[🇬🇧 English] [🇷🇺 Russian] [💻 Programming]
[⚙️ Sozlamalar]
```

**Til menyusi** English va Russian uchun bir xil:

```
[📘 Grammatika] [🎙 Speaking]
[✍️ Writing]    [📝 Mistakes]
[🔁 Repetition] [📊 Progress]
[⬅️ Orqaga]
```

**Bilim menyusi** (Programming) papkalar bo'yicha ichma-ich ochiladi:

```
💻 Programming › Backend › Software architecture › Microservices
[✅ Service boundaries]
[▫️ Communication: sync vs async]
[▫️ Data ownership]
[◀️ 1/2 ▶️]
[⬅️ Orqaga] [🏠 Menyu]
```

- Yuqorida "yo'l" (breadcrumb) ko'rinadi, shuning uchun qayerda ekaningiz doim ma'lum.
- Bir sahifada ko'pi bilan 8 ta tugma bo'ladi. Ko'p bo'lsa, `◀️ ▶️` bilan sahifalanadi.
- ✅ — siz o'qigan qism. Papka tugmasida progress ko'rinadi, masalan "Backend (12/188)".

---

## 2. Fayl tuzilishi

```
english-teacher/
  bot/                         # kod (4-bo'lim)
  content/                     # mazmun — git da, siz tahrirlaysiz
  data/                        # faqat bot.db — serverda, git da emas
  tests/                       # Python testlar
  tools/
    check_content.py           # content/ ni tekshiradi: bo'sh fayl, takroriy nom, juda uzun sarlavha
  Dockerfile  docker-compose.yml  deploy.sh  DEPLOY.md  PLAN.md
```

### 2.1. `content/`

```
content/
  shared/
    style.md                        # umumiy uslub: qisqa, chat kabi, formatlash qoidalari
  english/
    subject.toml                    # fan sozlamalari (pastda)
    prompt.md                       # ingliz tili o'qituvchisi qoidalari
    grammar/
      01_tenses_for_daily_work.md
      02_questions_requests_modals.md
      03_explaining_systems.md
      04_natural_professional_english.md
      05_writing_at_work.md
  russian/
    subject.toml
    prompt.md                       # rus tili: so'z boyligiga urg'u, izohlar o'zbekcha
    grammar/
      01_daily_life.md              # oila, uy, ovqat
      02_city_and_shopping.md       # do'kon, transport, yo'l so'rash
      03_health_and_services.md     # shifokor, bank, pochta
      04_work_and_office.md
  programming/
    subject.toml
    prompt.md                       # senior mentor: inglizcha, kodsiz, tushuntirish tuzilmasi
    backend/
      _index.md                     # ixtiyoriy: papka sarlavhasi va tavsifi
      01_web_and_apis/
        01_http_request_lifecycle.md
        02_http_methods_status_codes.md
        ...
      02_clean_code_and_design/
      03_backend_architecture/
    frontend/
      01_html_css_basics/  02_javascript_core/  03_react/  04_state_management/  05_performance/
    qa/
      01_testing_fundamentals/  02_test_automation/  03_api_testing/  04_performance_testing/
    rag/
      01_rag_fundamentals/  02_retrieval/  03_llm_applications/  04_evaluation/
    ml/
      01_ml_foundations/  02_deep_learning/  03_mlops/
```

**`subject.toml`** — fan turi va sozlamalari:

```toml
title = "English"
icon = "🇬🇧"
type = "language"          # language | knowledge
order = 1

[language]                 # faqat type = "language" uchun
code = "en"                # Whisper tili
tts_engine = "groq"        # groq | edge
tts_voice = "troy"         # russian: engine = "edge", voice = "ru-RU-SvetlanaNeural"
default_level = "B1"
scheduled = true           # ertalabki dars, kechki eslatma, haftalik takrorlash (russian: false)
```

**Mavzu fayli** — hamma joyda bitta format:

```
# Microservices
- Service boundaries
- Communication: sync vs async
- Data ownership
```

- `grammar/*.md` da har bir `-` qatori bitta grammatika mavzusi bo'ladi. Programming'da esa bitta qism.

**Qoidalar:**
- **Tartib:** `01_` kabi raqamli prefiks tartibni belgilaydi va ekranda ko'rinmaydi.
- **Sarlavhalar:** fayl sarlavhasi uning ichidagi `# Title` qatoridan olinadi. Papka sarlavhasi `_index.md` dan olinadi, u bo'lmasa papka nomidan: `software_architecture` → "Software architecture".
- **Chuqurlik:** papkalar ixtiyoriy chuqurlikda bo'lishi mumkin.
- **Yangi mavzu, yo'nalish yoki til:**
  - yangi mavzu yoki yo'nalish qo'shish uchun fayl yoki papka qo'shiladi;
  - yangi til yoki fan qo'shish uchun `subject.toml` bor papka qo'shiladi.

  Ikkala holatda ham kod o'zgarmaydi.
- **Nomni o'zgartirish:** qism nomi o'zgarsa, uning saqlangan tushuntirishi yangi nomga o'tmaydi. `tools/check_content.py` bu haqda ogohlantiradi.

### 2.2. Ko'chirish (hozirgi → yangi)

| Hozir | Keyin |
|---|---|
| `data/context.md` | quyidagi qismlarga bo'linadi: `content/shared/style.md`, `english/prompt.md`, `programming/prompt.md`. "Men haqimda" bo'limi esa bazaga, foydalanuvchi profiliga o'tadi (4.3) |
| `data/topics.md` (5 blok, 31 mavzu) | `content/english/grammar/01..05_*.md` |
| `data/tech.md` (6 bo'lim, 47 mavzu, 188 qism) | Web and APIs, Clean code, Backend architecture → `backend/`; ML foundations → `ml/`; RAG, LLM applications → `rag/` |
| — | `frontend/`, `qa/`, `russian/grammar/`, qo'shimcha `ml/` va `rag/` mavzulari: boshlang'ich ro'yxatni men yozaman, siz tahrirlaysiz |

`docker-compose.yml`: `./content` konteynerga faqat o'qish uchun ulanadi (read-only). Mazmun o'zgarganda image'ni qayta build qilish shart emas, `docker compose restart` yetarli.

---

## 3. Bo'limlar

### 3.1. English va Russian farqlari

| | English | Russian |
|---|---|---|
| Maqsad | ish muloqoti: yozish va gapirish | kundalik so'z boyligi: eshitib tushunasiz, lekin oddiy so'zlarni ham bilmaysiz |
| Daraja | B1 | tushunish yaxshi, so'z boyligi kam (A2) |
| Mavzular | ishga oid grammatika, dasturchi hayoti | kundalik hayot va ish; grammatika yengil, asosiy urg'u so'zlarda |
| Izohlar | oddiy inglizcha + o'zbekcha eslatma | har bir yangi so'z o'zbekcha tarjima bilan, izohlar o'zbekcha |
| Dars qachon | 05:00 da avtomatik + tugma bilan | faqat Grammatika tugmasi bosilganda |
| Kechki eslatma, haftalik takrorlash | bor | yo'q (qo'shimcha o'rganish, bosim yo'q) |
| Whisper tili | `en` | `ru` |
| 🔊 Ovoz | Groq TTS (`troy`) | edge-tts (`ru-RU-SvetlanaNeural`) |

Bu farqlar kodda yozilmaydi — ular `subject.toml` va `prompt.md` dan olinadi.

### 3.2. 📘 Grammatika
- **Bugungi dars:** karta, qoida, hikoya va 20 so'z. Agar bugun ko'rilgan bo'lsa, qisqa eslatma chiqadi.
- **Keyin oddiy yozma suhbat:** tuzatish, tabiiyroq variant va eslatma chiqadi, bugungi so'zlarni ishlatishga undaladi.
- **Tugmalar:** `[✅ Bajardim] [⬅️ Orqaga]`.
- **Dars keshi umumiy.** Kalit: til + mavzu + daraja. Bitta mavzu bo'yicha dars bir marta yaratiladi va o'sha darajadagi hamma foydalanuvchiga beriladi.

### 3.3. ✍️ Writing
1. AI vazifa beradi, navbatma-navbat:
   - o'zbekcha gap — siz uni yozib tarjima qilasiz;
   - ish yoki kundalik vaziyat — Slack xabari, email, code review javobi, bug report, PR tavsifi. Russian'da vaziyatlar kundalik hayotdan olinadi.
2. Siz yozasiz, AI tahlil qiladi: ✏️ to'g'rilangan versiya, 🚀 kuchaytirilgan versiya, 📌 eslatma. Keyingi vazifani AI shu javobning o'zida tayyorlab qo'yadi, lekin u hali ko'rsatilmaydi.
3. **Qayta yozish AI siz, faqat Python bilan tekshiriladi:**
   - "✏️ To'g'rilangan versiyani yozing" → siz yozasiz → tekshiriladi.
   - "🚀 Kuchaytirilgan versiyani yozing" → siz yozasiz → tekshiriladi.
   - Mos kelmasa, farqlar ko'rsatiladi: tushib qolgan, ortiqcha va noto'g'ri so'zlar. Qayta yozasiz.
   - Ikkalasi ham to'g'ri bo'lgach, tayyorlab qo'yilgan keyingi vazifa darhol chiqadi. Qo'shimcha AI so'rovi ketmaydi.
   - Xatosiz yozgan bo'lsangiz, bu bosqich o'tkazib yuboriladi.
4. **Qanday solishtiriladi:**
   - katta-kichik harf va ortiqcha probellar hisobga olinmaydi;
   - `’` va `'`, `“` va `"`, `—` va `-` bir xil deb olinadi;
   - oxiridagi nuqta majburiy emas;
   - so'zlar va ularning tartibi aniq mos kelishi kerak.
5. Faqat matn qabul qilinadi. Ovozli xabar yuborsangiz, bot "Yozib yuboring" deydi.

### 3.4. 🎙 Speaking
1. AI bir so'rovda 5 ta gapdan iborat to'plam tayyorlaydi. Gaplar bugungi mavzu va so'zlar asosida, oddiydan qiyinga qarab tuziladi.
2. **1-5 gap:** maqsad tilidagi matn va o'zbekcha tarjimasi beriladi, siz o'qib ovozli xabar yuborasiz.
   - Tahlil **AI siz, Python bilan** qilinadi:
     - Whisper eshitgan matn maqsadli gap bilan so'zma-so'z solishtiriladi;
     - noto'g'ri eshitilgan yoki tushib qolgan so'zlar ajratib ko'rsatiladi;
     - gapirish tezligi ko'rsatiladi;
     - 🔊 to'g'ri talaffuz ovozli xabar sifatida yuboriladi.
3. **6-gapdan boshlab:** faqat o'zbekchasi beriladi, siz tarjimasini o'zingiz aytasiz. Tahlilni **AI** qiladi va ma'no hamda grammatikani baholaydi, keyin 🔊 to'g'ri variantni yuboradi.
4. Xohlagancha qayta yuborasiz. Ishonchingiz komil bo'lsa, `[➡️ Keyingi]` ni bosasiz. To'plam tugasa, keyingi 5 ta gap so'raladi.
5. **Texnik tanlovlar:**
   - Whisper'ga maqsadli gap berilmaydi. Aks holda u xatoni yashirib qo'yadi.
   - 🔊 ovoz fayllari keshlanadi: bir xil matn qayta ovozlashtirilmaydi va Telegram `file_id` qayta ishlatiladi.
   - Bu bo'limda matn yozsangiz, bot "ovozli xabar yuboring" deydi.

### 3.5. 📝 Mistakes
- Xatolar ro'yxati chiqadi. Takrorlangan xatolar birlashtiriladi va "×3" kabi soni bilan ko'rsatiladi.
- `[🔁 Mashq qilish]`: AI xatolarni bittadan olib, to'g'ri shaklni ishlatadigan gap yozishni so'raydi.
- Haftalik takrorlash faqat `scheduled = true` bo'lgan tilda (English) keladi.

### 3.6. 🔁 Repetition
- **Ekran:** bugungi so'zlar holati (masalan 7/20, ✅/▫️) va `[▶️ Boshlash]` tugmasi.
- **So'z tanlash:** o'tgan kunlar so'zlaridan olinadi. Oralig'i 1, 3, 7, 14 va 30 kun bo'ladi (spaced repetition), ishlatilmagan so'zlar birinchi keladi. Bir sessiyada 10 ta so'z.
- **Mashq:** bot o'zbekcha ma'no yoki vaziyat beradi, siz shu so'z bilan gap yozasiz. AI to'g'ri ishlatganingizni tekshiradi.
- **Keyingi takrorlash sanasi:** to'g'ri ishlatsangiz, keyingi oraliqqa o'tadi. Xato qilsangiz, 1 kunga qaytadi. Bu hisobni Python qiladi.

### 3.7. 📊 Progress (har bir til uchun alohida)
- Grammatika mavzulari va progress chizig'i.
- 7 kunlik statistika: javoblar, xatolar, gapirish tezligi.
- Takrorlanishi kerak bo'lgan so'zlar soni.

### 3.8. 💻 Programming (bilim turi)
- Papkalar va fayllar bo'yicha ichma-ich yuriladi, eng oxirida qismlar (eng kichik mavzu) tanlanadi.
- **Qism tanlanganda:**
  - bazada tushuntirish bo'lsa, u darhol chiqadi va **0 token** sarflanadi;
  - bo'lmasa, AI inglizcha, kodsiz tushuntiradi va natija **bazaga saqlanadi**.
- **Kesh umumiy:** bir qismning tushuntirishi bir marta yaratiladi va hamma foydalanuvchiga beriladi.
- **Tushuntirish sifati — asosiy talab.** Qayta yaratish tugmasi yo'q, shuning uchun birinchi yaratishning o'zi mukammal bo'lishi kerak:
  - **To'liq kontekst:** AI'ga yo'nalish, papka, mavzu va shu mavzudagi boshqa qismlar ro'yxati beriladi. U mavzu chegarasini biladi va takrorlamaydi.
  - **Qat'iy tuzilma:** nima bu, nega kerak, qanday ishlaydi (`A -> B -> C` oqimi bilan), tizimda qayerda turadi, real misol, trade-off'lar va qachon tanlanadi, keng tarqalgan xatolar, 3-5 ta asosiy xulosa.
  - **Ikki bosqich:** AI avval yozadi, keyin alohida so'rov bilan aniqlik, to'liqlik va tushunarlilikni tekshirib tuzatadi. Bazaga faqat tekshirilgan variant yoziladi.
  - **Kuchliroq model:** `EXPLAIN_MODEL` sozlamasi, standart qiymati `claude-opus-5-5`. U faqat tushuntirish yaratishda ishlatiladi, suhbat va mashqlar arzonroq modelda qoladi.
  - **Til:** oddiy B1-B2 inglizcha, atamalar inglizcha, juda qiyin tushunchaga qisqa o'zbekcha izoh. Kod yozilmaydi.
- **Qo'shimcha savollar:** har bir savol alohida AI so'rovi bo'ladi, unga shu qismning saqlangan tushuntirishi kontekst sifatida beriladi. Javoblar **saqlanmaydi**. Inglizchangiz tuzatiladi va xatolar English → Mistakes ga tushadi.
- **Tugmalar:** `[➡️ Keyingi qism] [⬅️ Orqaga] [🏠 Menyu]`.

---

## 4. Ko'p foydalanuvchi va kengayish

Hozir faqat siz foydalanasiz, lekin asos boshidan ko'p foydalanuvchi uchun quriladi. Keyinchalik foydalanuvchi qo'shish uchun kodni qayta yozish shart bo'lmaydi.

### 4.1. Kirish (access)
- `/start` bosgan yangi foydalanuvchi `pending` holatiga tushadi. Egaga (owner) `[✅ Ruxsat] [⛔ Rad]` tugmali xabar keladi.
- **Rollar:** `owner` (siz), `admin`, `user`. Holatlar: `pending`, `active`, `blocked`.
- **Rejim:** `ACCESS_MODE` sozlamasi — `approval` (standart) yoki `open`.
- Hozirgi `OWNER_ID` birinchi ishga tushishda `owner` sifatida yoziladi.

### 4.2. Middleware
Har bir xabar va tugma bosishda quyidagilar bajariladi:
1. Foydalanuvchi bazadan yuklanadi, yangi bo'lsa yaratiladi.
2. Kirish tekshiriladi: `pending` yoki `blocked` bo'lsa, xabar to'xtatiladi.
3. Band holat tekshiriladi: har bir foydalanuvchida bir vaqtda bitta AI so'rovi.
4. Foydalanuvchi handlerga uzatiladi, shuning uchun handlerlar `settings.owner_id` ni bilmaydi.

### 4.3. Profil va sozlamalar
- **Profil** "Men haqimda" o'rnini bosadi va bazada saqlanadi: kasb, maqsad, har bir til uchun daraja, vaqt mintaqasi, dars va eslatma soati, yoqilgan fanlar.
- **Promptlar:** AI'ga promptda shu foydalanuvchining profili beriladi. `profile.md` fayl emas, bazadagi yozuv bo'ladi.
- **Tahrirlash:** `⚙️ Sozlamalar` menyusi orqali — daraja, dars soati, fanlarni yoqish yoki o'chirish.
- **Boshlang'ich qiymat:** sizning profilingiz hozirgi `context.md` dan olinadi.

### 4.4. Shaxsiy va umumiy ma'lumot

| Umumiy (hamma uchun bitta, token tejaydi) | Shaxsiy (`user_id` bilan) |
|---|---|
| Grammatika darslari (til + mavzu + daraja) | Tugallangan mavzular, progress |
| Dars so'zlari | So'zlarni ishlatish va takrorlash holati |
| Programming tushuntirishlari | Qaysi qismlarni o'qigani (✅) |
| TTS ovoz keshi | Javoblar, xatolar, statistika |
| | Bot holati (FSM), suhbat tarixi |

### 4.5. Xarajat nazorati
- **`ai_usage` jadvali:** har bir AI so'rovi uchun foydalanuvchi, model, kirish va chiqish tokenlari yoziladi.
- **Kunlik limit:** `DAILY_AI_LIMIT` — har bir foydalanuvchi uchun kunlik so'rovlar soni. Owner uchun limit yo'q. Limit tugasa, bot "Ertaga davom etamiz" deydi.
- **Parallellik:** bir vaqtda ko'pi bilan `AI_CONCURRENCY` ta Claude so'rovi yuboriladi (semafor).

### 4.6. Rejali xabarlar (ko'p foydalanuvchi uchun)
- Har bir foydalanuvchi uchun alohida cron job yaratilmaydi. Bitta job **har daqiqada** ishlaydi va mahalliy vaqti kelgan foydalanuvchilarga xabar yuboradi. Har kim o'z vaqt mintaqasi va soatini tanlay oladi.
- **Telegram limiti** (sekundiga ~30 xabar) hisobga olinadi: xabarlar navbat bilan yuboriladi.

| Vaqt (foydalanuvchi sozlamasi) | Nima |
|---|---|
| Dars soati (standart 05:00) | Ertalabki dars — `scheduled = true` bo'lgan tillar |
| Eslatma soati (standart 20:00) | Kechki natija yoki eslatma |
| Yakshanba 11:00 | Haftalik xatolar takrorlanishi |

### 4.7. Admin
`/admin` — faqat owner va admin uchun: foydalanuvchilar ro'yxati, ruxsat berish va bloklash, kunlik va oylik token sarfi.

### 4.8. Baza
- **Hozir SQLite** (WAL rejimida): bir necha yuz foydalanuvchigacha yetarli. Bazaga murojaat `aiosqlite` orqali asinxron bo'ladi, shuning uchun event loop to'xtab qolmaydi.
- **Kelajakda PostgreSQL:** barcha SQL `bot/db/` ichida, repository funksiyalari orqali. PostgreSQL'ga o'tganda faqat `db/` o'zgaradi.
- **Migratsiyalar:** `bot/db/migrations/001_*.sql, 002_*.sql ...` fayllari `PRAGMA user_version` orqali tartib bilan va bir marta bajariladi.

### 4.9. Katta mazmun (ko'p mavzu va yo'nalish)
- **Indeks:** `content/` ishga tushishda bir marta o'qiladi va xotirada daraxt (indeks) sifatida saqlanadi. `/reload` (admin) buyrug'i restartsiz qayta o'qiydi.
- **Qisqa ID:** har bir tugun (papka, fayl, qism) yo'lidan olingan 8 belgilik hash ID oladi. Telegram `callback_data` 64 bayt bilan cheklangani uchun uzun yo'llar tugmaga sig'maydi, qisqa ID esa sig'adi.
- **Sahifalash:** bir sahifada 8 ta tugma.
- **Tekshiruv:** `tools/check_content.py` fayllarni tekshiradi — bo'sh fayl, takroriy nom, 60 belgidan uzun sarlavha. Deploydan oldin ishga tushiriladi.
- **Kelajakda:** `/search` bilan mavzu qidirish, "tasodifiy mavzu" va "keyingi o'qilmagan qism" tugmalari. Tuzilma bunga tayyor.

### 4.10. Interfeys matnlari
Bot matnlari (tugmalar, xabarlar) kod ichida sochilib yotmaydi, `bot/ui/texts.py` da jamlanadi. Hozir hammasi o'zbekcha, lekin kerak bo'lsa, boshqa tilga o'tkazish bitta faylni tarjima qilishdan iborat bo'ladi.

---

## 5. Kod tuzilishi

```
bot/
  main.py                      # ishga tushirish: DB, content indeks, routerlar, scheduler
  config.py                    # .env sozlamalari
  content/
    models.py                  # Subject, Node, Topic, Leaf
    loader.py                  # papka, subject.toml, *.md o'qish
    index.py                   # daraxt, qisqa ID, qidirish, qayta yuklash
  db/
    core.py                    # aiosqlite ulanish, migratsiyalarni bajarish
    migrations/                # 001_initial.sql, 002_multi_user.sql, ...
    fsm.py                     # SQLiteStorage (aiogram)
    users.py                   # foydalanuvchi, rol, profil, sozlamalar
    language.py                # darslar, so'zlar, javoblar, xatolar, takrorlash
    knowledge.py               # tushuntirishlar keshi, o'qilgan qismlar
    media.py                   # TTS file_id keshi
    usage.py                   # AI token sarfi, limitlar
  ai/
    client.py                  # Claude chaqiruvi: qayta urinish, semafor, sarf yozish
    schemas.py                 # Lesson, ChatReply, WritingReply, SpeakingBatch, Explanation, ...
    prompts.py                 # promptni yig'ish: style + fan prompt + profil + rejim
  services/
    lessons.py                 # bugungi mavzu, dars keshi
    writing.py                 # vazifa → tahlil → qayta yozish bosqichlari
    speaking.py                # 5 talik to'plam, o'qish / tarjima bosqichi
    compare.py                 # Python solishtiruv (normalizatsiya, so'z farqi)
    repetition.py              # spaced repetition oraliqlari
    knowledge.py               # tushuntirish: kesh → 2 bosqichli yaratish
    access.py                  # ruxsat, rollar, limit
    words.py                   # bugungi so'zlarni matndan topish
  voice/
    stt.py                     # Whisper (Groq), ffmpeg tozalash
    tts.py                     # umumiy interfeys + groq va edge dvigatellari
  ui/
    texts.py                   # barcha bot matnlari
    format.py                  # fmt, quote, split_text, send_text
    card.py                    # dars kartasi rasmi
    keyboards/                 # main.py, language.py, knowledge.py, admin.py, pagination.py
    callbacks.py               # barcha CallbackData klasslari
  handlers/
    __init__.py                # routerlarni yig'ish
    middlewares.py             # foydalanuvchi, kirish, band holat, "Thinking…"
    start.py                   # /start, ro'yxatdan o'tish
    menu.py                    # asosiy menyu
    settings.py                # ⚙️ Sozlamalar
    admin.py                   # /admin, /reload
    language/
      menu.py grammar.py speaking.py writing.py mistakes.py repetition.py progress.py
    knowledge.py               # Programming va kelajakdagi bilim fanlari
  jobs/
    scheduler.py               # har daqiqalik job
    morning.py evening.py weekly.py
tests/
  test_compare.py test_repetition.py test_content_loader.py test_migrations.py test_words.py
tools/
  check_content.py
```

**Qoidalar:**
- **Qatlamlar:** `handlers` → `services` → `db` / `ai` / `voice`. Handler Telegram bilan ishlaydi va SQL yozmaydi. Service Telegram'ni bilmaydi.
- **Takrorlanish yo'q:** English va Russian bitta `handlers/language/` kodidan foydalanadi. Programming va kelajakdagi boshqa bilim fanlari bitta `handlers/knowledge.py` dan foydalanadi.
- **Holat:** har bir bo'lim holati aiogram `StatesGroup` orqali aniq belgilanadi.
- **Testlar:** AI siz ishlaydigan qismlar Python testlari bilan qoplanadi — solishtiruv, takrorlash, content o'qish, migratsiya.
- **Yangi bog'liqliklar:** `edge-tts`, `aiosqlite`, `pytest` (dev).

---

## 6. Baza

**Jadvallar:**

| Jadval | Nima | Tur |
|---|---|---|
| `users` | id, ism, rol, holat, vaqt mintaqasi, soatlar, yaratilgan sana | shaxsiy |
| `user_subjects` | foydalanuvchi + fan: daraja, yoqilganmi | shaxsiy |
| `fsm` | bot holati va suhbat tarixi | shaxsiy |
| `lessons` | til + mavzu + daraja → dars JSON | umumiy |
| `lesson_words` | dars so'zlari | umumiy |
| `user_words` | foydalanuvchi + so'z: ishlatilgan, `review_step`, `next_review` | shaxsiy |
| `done_topics` | foydalanuvchi + til + kun → mavzu | shaxsiy |
| `answers` | foydalanuvchi, til, bo'lim, matn, so'zlar soni, ovoz soniyalari, xatolar soni | shaxsiy |
| `mistakes` | foydalanuvchi, til, xato → to'g'ri, izoh | shaxsiy |
| `explanations` | tugun ID + yo'l + qism → tushuntirish JSON, model | umumiy |
| `knowledge_reads` | foydalanuvchi + tushuntirish: o'qilgan sana | shaxsiy |
| `tts_cache` | dvigatel + ovoz + matn → Telegram `file_id` | umumiy |
| `ai_usage` | foydalanuvchi, kun, model, tokenlar | shaxsiy |

**Hozirgi bazadan ko'chirish:** mavjud barcha yozuvlar (progress, darslar, so'zlar, xatolar, javoblar, holat) sizning `user_id` va `lang = 'en'` ga bog'lanadi. Hech narsa yo'qolmaydi. Migratsiya avval bazaning nusxasida sinaladi.

---

## 7. Ish tartibi

1. **Mazmun:** `content/` tuzilmasi, hozirgi fayllarni ko'chirish, yangi mavzu ro'yxatlari (frontend, qa, rus tili, qo'shimcha ml va rag). `tools/check_content.py`.
2. **Baza:** `db/` va migratsiyalar; mavjud `bot.db` nusxasida sinash.
3. **Mantiq:** `content/`, `services/`, `voice/` va ularning testlari.
4. **Telegram:** middleware, handlerlar va klaviaturalar.
5. **Sinov:** har bir bo'limni haqiqiy Claude, Groq va edge-tts so'rovlari bilan sinash.
6. **Hujjat va deploy:** `DEPLOY.md`, `.env.example`, `docker-compose.yml` ni yangilash va sizga bitta hisobot berish.

**Hozir qilinadigan va keyinga qoladigan ishlar:**

| Hozir | Keyinga (tuzilma tayyor, kod qo'shiladi) |
|---|---|
| Hamma bo'limlar (3-bo'lim) | `/search`, tasodifiy mavzu |
| `users`, rollar, `approval` kirish, middleware | To'liq ⚙️ Sozlamalar menyusi (hozir faqat daraja va soatlar) |
| `user_id` hamma shaxsiy jadvalda, umumiy keshlar | PostgreSQL |
| `ai_usage` yozish va kunlik limit | Admin'da grafiklar |
| `/admin`: ruxsat berish va bloklash, `/reload` | Interfeys uchun boshqa tillar |

---

## 8. Qabul qilingan qarorlar

| Savol | Qaror |
|---|---|
| Asosiy menyu | English, Russian, Programming (+ Sozlamalar) |
| Writing bo'limi | Tarjima + ish yozishmasi, navbatma-navbat |
| Writing tekshiruvi | Python; harf, probel, qo'shtirnoq farqi hisobga olinmaydi |
| Speaking | 5 ta gap o'qish, keyin faqat o'zbekcha; `[➡️ Keyingi]` ni o'zingiz bosasiz |
| Repetition | O'tgan kunlar so'zlari, spaced repetition |
| Russian | Qo'shimcha o'rganish: ertalabki dars va eslatmalar yo'q; so'z boyligiga urg'u |
| Programming yo'nalishlari | Backend, Frontend, QA, RAG, ML |
| Programming fayli | Fayl = mavzu, ichida qismlar; qism bazaga saqlanadi |
| Qayta tushuntirish tugmasi | Yo'q — birinchi tushuntirish mukammal bo'ladi (ikki bosqich + kuchli model) |
| 🔊 English | Groq TTS (shartlar qabul qilingan) |
| 🔊 Russian | edge-tts |
| Ko'p foydalanuvchi | Asos hozir quriladi: `approval` kirish, umumiy kesh, limitlar |
