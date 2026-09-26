#!/usr/bin/env bash
# Serverda ishga tushiriladi: git dan oxirgi kodni olib, botni qayta build qiladi.
#   ./deploy.sh

set -euo pipefail
cd "$(dirname "$0")"

[[ -f .env ]] || { echo "Xato: .env topilmadi (cp .env.example .env)"; exit 1; }

git fetch origin
git reset --hard "origin/$(git rev-parse --abbrev-ref HEAD)"

docker compose up -d --build
docker image prune -f >/dev/null
docker compose logs --tail=20 bot
