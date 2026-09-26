# Deploy

## Birinchi marta (serverda)

```bash
# Docker o'rnatish
curl -fsSL https://get.docker.com | sh

# Loyihani yuklab olish
git clone https://github.com/Aslonbek2001/personal-bot.git /opt/english-teacher
cd /opt/english-teacher

# .env ni to'ldirish
cp .env.example .env
nano .env

# Ishga tushirish
./deploy.sh
```

## Yangilash

Kompyuterda:
```bash
git push
```

Serverda:
```bash
cd /opt/english-teacher && ./deploy.sh
```

## Foydali buyruqlar (serverda)

```bash
docker compose logs -f bot   # loglar
docker compose restart       # qayta ishga tushirish
docker compose down          # to'xtatish
```

> Lokal botni o'chirib qo'ying — bitta token bilan bot faqat bitta joyda ishlaydi.
