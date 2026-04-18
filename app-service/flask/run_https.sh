#!/usr/bin/env bash
# Запуск с самоподписанным HTTPS. Открой https://localhost:${FLASK_PORT:-5000}/rytm/
set -euo pipefail
cd "$(dirname "$0")"
export FLASK_SSL_ADHOC=1
export FLASK_PORT="${FLASK_PORT:-5000}"
echo "Starting https://localhost:${FLASK_PORT}/ (Ctrl+C to stop)"
exec python app.py
