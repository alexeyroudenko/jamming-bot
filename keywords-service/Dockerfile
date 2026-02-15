FROM python:3.11

WORKDIR /app

# Копируем файлы
COPY requirements.txt .
COPY app /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем приложение
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7771"]