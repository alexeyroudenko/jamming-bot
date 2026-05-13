#!/usr/bin/env bash
# Запуск с самоподписанным HTTPS. Открой https://localhost:${FLASK_PORT:-5000}/rytm/
# Перезапуск при правках: FLASK_USE_RELOADER=1 (по умолчанию в docker-compose); для Socket.IO включается threading.
set -euo pipefail
cd "$(dirname "$0")"
export FLASK_SSL_ADHOC=1
export SUBLINK_REDIS_LISTENER="${SUBLINK_REDIS_LISTENER:-0}"
export FLASK_PORT="${FLASK_PORT:-5000}"
export FLASK_USE_RELOADER="${FLASK_USE_RELOADER:-1}"
echo "Starting https://localhost:${FLASK_PORT}/ (Ctrl+C to stop)"
exec python app.py
