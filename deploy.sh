#!/usr/bin/env bash
# Botni VPS ga joylash.
#
#   ./deploy.sh setup     # yangi serverga Docker o'rnatadi (bir marta)
#   ./deploy.sh           # kodni yuboradi, qayta build qilib ishga tushiradi
#   ./deploy.sh env       # lokal .env ni serverga qayta yuboradi va restart qiladi
#   ./deploy.sh logs      # loglarni kuzatish (Ctrl+C bilan chiqish)
#   ./deploy.sh status    # konteyner holati
#   ./deploy.sh restart   # konteynerni qayta ishga tushirish
#   ./deploy.sh stop      # botni to'xtatish
#
# Sozlamalar (muhit o'zgaruvchilari yoki deploy.env faylida):
#   SERVER=root@1.2.3.4   (majburiy)
#   SSH_PORT=22
#   REMOTE_DIR=/opt/english-teacher

set -euo pipefail

cd "$(dirname "$0")"

[[ -f deploy.env ]] && source deploy.env

SSH_PORT="${SSH_PORT:-22}"
REMOTE_DIR="${REMOTE_DIR:-/opt/english-teacher}"

log() { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mXato:\033[0m %s\n' "$*" >&2; exit 1; }

[[ -n "${SERVER:-}" ]] || die "SERVER o'rnatilmagan. Masalan: SERVER=root@1.2.3.4 ./deploy.sh (yoki deploy.env yarating)"

SSH=(ssh -p "$SSH_PORT" -o ServerAliveInterval=30 "$SERVER")

remote() { "${SSH[@]}" "cd '$REMOTE_DIR' && $*"; }

setup() {
    log "Docker o'rnatilmoqda ($SERVER)"
    "${SSH[@]}" bash -s <<'EOF'
set -euo pipefail
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    docker --version
else
    curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker
EOF
    "${SSH[@]}" "mkdir -p '$REMOTE_DIR/data'"
    log "Tayyor. Endi: ./deploy.sh"
}

upload_env() {
    [[ -f .env ]] || die ".env topilmadi. .env.example dan nusxa oling va to'ldiring."
    log ".env yuborilmoqda"
    scp -P "$SSH_PORT" -q .env "$SERVER:$REMOTE_DIR/.env"
    "${SSH[@]}" "chmod 600 '$REMOTE_DIR/.env'"
}

sync_code() {
    log "Kod yuborilmoqda → $SERVER:$REMOTE_DIR"
    "${SSH[@]}" "mkdir -p '$REMOTE_DIR/data'"
    # process.md va bot.db serverda yoziladi — ularni ustidan yozmaymiz va o'chirmaymiz.
    rsync -az --delete -e "ssh -p $SSH_PORT" \
        --exclude '.git/' \
        --exclude '.venv/' \
        --exclude '__pycache__/' \
        --exclude '*.pyc' \
        --exclude '.env' \
        --exclude 'deploy.env' \
        --exclude '.DS_Store' \
        --exclude '.vscode/' \
        --exclude '.idea/' \
        --exclude 'data/process.md' \
        --exclude 'data/bot.db' \
        ./ "$SERVER:$REMOTE_DIR/"
}

deploy() {
    command -v rsync >/dev/null || die "rsync o'rnatilmagan"
    "${SSH[@]}" "command -v docker >/dev/null" || die "Serverda Docker yo'q. Avval: ./deploy.sh setup"

    sync_code

    if ! "${SSH[@]}" "test -f '$REMOTE_DIR/.env'"; then
        upload_env
    fi

    log "Build va ishga tushirish"
    remote "docker compose up -d --build --remove-orphans"
    remote "docker image prune -f >/dev/null"

    sleep 3
    remote "docker compose ps"
    log "Oxirgi loglar:"
    remote "docker compose logs --tail=20 bot"
}

case "${1:-deploy}" in
    setup)   setup ;;
    deploy)  deploy ;;
    env)     upload_env && remote "docker compose up -d --force-recreate" ;;
    logs)    "${SSH[@]}" -t "cd '$REMOTE_DIR' && docker compose logs -f --tail=100 bot" ;;
    status)  remote "docker compose ps" ;;
    restart) remote "docker compose restart" ;;
    stop)    remote "docker compose down" ;;
    *)       die "Noma'lum buyruq: $1 (setup | deploy | env | logs | status | restart | stop)" ;;
esac
