#!/usr/bin/env bash
# Serverda ishga tushiriladi: git dan oxirgi kodni olib, botni qayta build qiladi.
#   ./deploy.sh

set -euo pipefail
cd "$(dirname "$0")"

[[ -f .env ]] || { echo "Xato: .env topilmadi (cp .env.example .env)"; exit 1; }

# process.md ni bot serverda yozadi — pull paytida yo'qolmasin.
cp data/process.md /tmp/process.md.bak 2>/dev/null || true

git fetch origin
git reset --hard "origin/$(git rev-parse --abbrev-ref HEAD)"

cp /tmp/process.md.bak data/process.md 2>/dev/null || true

docker compose up -d --build
docker image prune -f >/dev/null
docker compose logs --tail=20 bot
