---
title: Jamming bot microservices
note_type: dev
project: "[[Jamming Bot]]"
tags:
  - dev
  - microservices
  - architecture
  - jamming-bot
---

# Jamming bot microservices

Список микросервисов и инфраструктурных сервисов проекта по актуальному `docker-compose.yml`.

## Основные микросервисы

- `bot` — бот-краулер, основной runtime обхода.
- `flask` — app-service, входная точка `/bot/*`, orchestration и UI-роуты.
- `tags_service` — FastAPI-сервис тегов и tag API.
- `semantic_service` — FastAPI-сервис семантического анализа текста.
- `ip_service` — FastAPI-сервис геолокации и IP lookup.
- `storage_service` — FastAPI-сервис долговременного хранения шагов и экспорта.
- `data_service` — FastAPI-сервис чтения локальной SQLite-базы URL и статистики.
- `keywords_service` — отдельный сервис классификации текста по словарю ключевых слов.
- `html-renderer-service` — сервис рендеринга страниц в изображения для screenshot pipeline.
- `backfill-worker` — фоновый worker, который добирает пропущенные URL из `data_service` и прогоняет их через `app-service`.

## Фоновые исполнители

- `worker`
- `worker2`
- `worker3`

Эти контейнеры выполняют RQ jobs из `app-service/flask/jobs.py` и ходят в:
- `tags_service`
- `semantic_service`
- `storage_service`
- `ip_service`
- `html-renderer-service`

## Инфраструктурные сервисы

- `redis` — очередь задач и live state.
- `tags_db` — PostgreSQL для `tags_service`, `semantic_service`, `ip_service`.
- `jaeger` — tracing / OTEL backend.
- `rq-dashboard` — UI для мониторинга очередей RQ.
- `frontend` — frontend dev container.
- `spacyapi` — отдельный legacy spaCy API контейнер.

## Связи по данным

- `flask` принимает шаги через `/bot/step/`.
- `worker*` запускают jobs анализа, геообогащения, screenshot и сохранения.
- `semantic_service` возвращает semantic tags / phrases.
- `tags_service` хранит и отдает теги.
- `ip_service` добавляет геоданные по IP.
- `storage_service` сохраняет агрегированный step.
- `data_service` отдает URL и статистику для backfill.
- `html-renderer-service` делает screenshot страницы.
- `backfill-worker` читает `data_service`, сверяется со `storage_service` и отправляет шаги обратно в `flask`.

## Связанные заметки

- [[Jamming bot Dev project]]
- [[jamming bot flask]]
- [[Jamming bot Redis Queue Jobs]]
- [[шаг]]
