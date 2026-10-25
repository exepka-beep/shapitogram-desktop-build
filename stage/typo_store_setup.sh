#!/bin/bash
# Настроить бота-магазин TypoGram: свежий .env, база grammystore, запуск.
set -uo pipefail

DIR=/root/shapito-store
CREDS=/root/typogram-credentials.txt
TOKEN="8680058020:AAG80lcZuH5CaB8KwqJKxgvIO7uGRKIgEuo"

PG_PW=$(grep -oP '(?<=^postgres    : telesrv / )\S+' "$CREDS")
API_TOKEN=$(grep -oP '(?<=Bearer )[^)]+' "$CREDS")
OTP_SECRET=$(grep -oP '(?<=^otp webhook : )\S+' "$CREDS")

echo "postgres pw len=${#PG_PW} api token len=${#API_TOKEN} otp len=${#OTP_SECRET}"

BOT_USER=$(curl -s -m 20 "https://api.telegram.org/bot${TOKEN}/getMe" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('result',{}).get('username','')) if d.get('ok') else print('')")
echo "bot username: ${BOT_USER:-<unknown>}"

cat > "$DIR/.env" <<EOF
# TypoGram — бот авторизации и магазин (grammystore).
BOT_TOKEN=$TOKEN
OWNER_IDS=803482266
BOT_PUBLIC_USERNAME=${BOT_USER:-typogrambot}
PRODUCT_NAME=TypoGram

GRAMSRV_API=http://127.0.0.1:2599
GRAMSRV_TOKEN=$API_TOKEN
GRAMSRV_ACTOR=grammystore
PUBLIC_BASE_URL=https://typogram.duckdns.org

DATABASE_URL=postgres://telesrv:${PG_PW}@127.0.0.1:15432/grammystore?sslmode=disable

BOT_MODE=random

CODE_HTTP_HOST=127.0.0.1
CODE_HTTP_PORT=2800
CODE_WEBHOOK_SECRET=$OTP_SECRET

REQUIRED_CHANNEL=
REQUIRED_CHANNEL_URL=
DEFAULT_LANGUAGE=ru
DEFAULT_NUMBER_COUNTRY=RU
REFERRAL_BONUS=100
DAILY_BONUS=15
NOTIFICATION_TTL_DAYS=30
RATE_LIMIT_MAX_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
TELEGRAM_PROXY_URL=
EOF
chmod 600 "$DIR/.env"

# отдельная база в кластере сервера
docker exec typogram-main-postgres-1 psql -U telesrv -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname='grammystore'" | grep -q 1 || \
  docker exec typogram-main-postgres-1 psql -U telesrv -d postgres -c "CREATE DATABASE grammystore" 

cd "$DIR"
sed -i 's/container_name: shapitogram-store/container_name: typogram-store/' docker-compose.yml
docker compose up -d 2>&1 | tail -5
sleep 6
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'typogram'
echo "--- healthz"
curl -s -m 8 http://127.0.0.1:2800/healthz; echo
echo "--- log"
docker logs --tail 12 typogram-store 2>&1 | tail -12
