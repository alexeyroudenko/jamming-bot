# Запуск Flask+SocketIO с самоподписанным HTTPS (Werkzeug adhoc).
# Открой https://localhost:5000/rytm/ — в браузере один раз прими предупреждение о сертификате.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $env:FLASK_PORT) { $env:FLASK_PORT = "5000" }
$env:FLASK_SSL_ADHOC = "1"
# Без Docker-хоста redis:6379 не поднимается — не стартуем Pub/Sub sublink (см. SUBLINK_REDIS_LISTENER в app.py).
if (-not $env:SUBLINK_REDIS_LISTENER) { $env:SUBLINK_REDIS_LISTENER = "0" }

$port = $env:FLASK_PORT
Write-Host "Starting https://localhost:${port}/ (Ctrl+C to stop)" -ForegroundColor Cyan
python app.py
