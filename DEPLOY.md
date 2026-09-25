# Botni VPS ga joylash

Bot Docker ichida ishlaydi. Kod kompyuteringizdan `deploy.sh` orqali serverga yuboriladi, serverda build qilinib ishga tushadi. Serverga git yoki Python o'rnatish shart emas.

## Talablar

**Server (VPS):**
- Ubuntu 22.04 / 24.04 (yoki Debian 12)
- Kamida 1 GB RAM, 10 GB disk
- `root` yoki `sudo` huquqli foydalanuvchi bilan SSH kirish

**Kompyuteringiz (Mac):**
- `ssh`, `scp`, `rsync` (Mac da bor)
- To'ldirilgan `.env` fayl

> Telegram bot bitta tokenda faqat **bitta joyda** ishlay oladi. Server ishga tushgach, lokal botni to'xtating, aks holda `Conflict: terminated by other getUpdates request` xatosi chiqadi.

---

## 1. SSH kalit bilan kirishni sozlash (bir marta)

Har safar parol so'ramasligi uchun:

```bash
# Kalit yo'q bo'lsa, yaratish
ls ~/.ssh/id_ed25519.pub || ssh-keygen -t ed25519

# Kalitni serverga nusxalash (parolni bir marta so'raydi)
ssh-copy-id root@SERVER_IP

# Tekshirish — parolsiz kirishi kerak
ssh root@SERVER_IP
```

## 2. Server manzilini saqlash (bir marta)

Loyiha papkasida `deploy.env` fayl yarating (git ga tushmaydi):

```bash
cat > deploy.env <<'EOF'
SERVER=root@SERVER_IP
SSH_PORT=22
REMOTE_DIR=/opt/english-teacher
EOF
```

## 3. `.env` ni tayyorlash (bir marta)

```bash
cp .env.example .env
```

So'ng `.env` ni oching va to'ldiring:

| O'zgaruvchi | Qayerdan olinadi |
|---|---|
| `BOT_TOKEN` | Telegram → @BotFather |
| `OWNER_ID` | Telegram → @userinfobot (sizning ID raqamingiz) |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `GROQ_API_KEY` | console.groq.com → API Keys |

## 4. Serverga Docker o'rnatish (bir marta)

```bash
./deploy.sh setup
```

Docker o'rnatilgan bo'lsa, bu qadam hech narsani buzmaydi.

## 5. Deploy

```bash
./deploy.sh
```

Skript quyidagilarni bajaradi:
1. Kodni va `data/` dagi fayllarni serverga yuboradi (`rsync`)
2. Serverda `.env` bo'lmasa — lokal `.env` ni yuboradi
3. `docker compose up -d --build` — image ni build qilib, botni ishga tushiradi
4. Eski image larni tozalaydi
5. Konteyner holati va oxirgi 20 qator logni ko'rsatadi

Logda xato bo'lmasa va Telegramda bot `/start` ga javob bersa — tayyor.

---

## Kundalik ishlar

| Vazifa | Buyruq |
|---|---|
| Kodni yangilash | `./deploy.sh` |
| `.env` ni o'zgartirib yuborish | `./deploy.sh env` |
| Loglarni jonli kuzatish | `./deploy.sh logs` |
| Holatni ko'rish | `./deploy.sh status` |
| Qayta ishga tushirish | `./deploy.sh restart` |
| To'xtatish | `./deploy.sh stop` |

### `data/` papkasi haqida

- `context.md`, `topics.md`, `tech.md` — kompyuteringizda tahrirlaysiz, `./deploy.sh` ularni serverga yuboradi.
- `process.md` — bot o'zi yozadi (bajarilgan mavzular). Deploy uni **ustidan yozmaydi va o'chirmaydi**, faqat serverda turadi.

Serverdagi progressni ko'rish yoki zaxira nusxa olish:

```bash
ssh root@SERVER_IP cat /opt/english-teacher/data/process.md
scp root@SERVER_IP:/opt/english-teacher/data/process.md ./process.backup.md
```

---

## Muammolar

**Bot javob bermayapti**
```bash
./deploy.sh logs
```
- `Conflict: terminated by other getUpdates` — bot boshqa joyda (lokal kompyuterda) ham ishlayapti. Uni to'xtating.
- `ValidationError ... field required` — `.env` da biror kalit yetishmaydi. To'ldirib, `./deploy.sh env`.
- `Unauthorized` — `BOT_TOKEN` noto'g'ri.

**`Permission denied (publickey)`** — 1-qadamni qayta bajaring yoki `SERVER` dagi foydalanuvchi nomini tekshiring.

**`Serverda Docker yo'q`** — `./deploy.sh setup` ni ishga tushiring.

**Dars soati noto'g'ri vaqtda keladi** — `docker-compose.yml` da `TZ: Asia/Tashkent`, `.env` da `TIMEZONE` va `LESSON_HOUR` ni tekshiring.

**Server qayta yuklansa** — hech narsa qilish shart emas: `restart: unless-stopped` botni avtomatik ko'taradi.

---

## Xavfsizlik (tavsiya)

Bot faqat tashqariga so'rov yuboradi (polling), unga ochiq port kerak emas. Faqat SSH ni ochiq qoldiring:

```bash
ssh root@SERVER_IP
ufw allow OpenSSH
ufw enable
```
