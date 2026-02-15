# 1. Базовый образ Python (Bookworm — стабильная версия Debian)
FROM python:3.11-slim-bookworm

# 2. Устанавливаем рабочую директорию
WORKDIR /app

# 3. Копируем файлы зависимостей
# Контекст сборки: docker build -t 1325gy/my_dev:v5 html-renderer-service/
COPY requirements.txt ./

# 4. Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# 5. Устанавливаем системные зависимости для Playwright (нужен root)
RUN playwright install-deps chromium

# 6. Создаем пользователя с домом
RUN useradd -r -m -g root -s /bin/bash pptruser

# 7. Переключаемся на нашего пользователя
USER pptruser

# 8. Устанавливаем браузер Chromium для Playwright
RUN playwright install chromium

# 9. Копируем код приложения
COPY --chown=pptruser:root src/ .

# 10. Открываем порт и запускаем
EXPOSE 3000
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]
