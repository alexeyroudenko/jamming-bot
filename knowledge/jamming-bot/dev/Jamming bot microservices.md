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

## Сервисы

| Type             | Имя                     | Описание                                                                                               |
| ---------------- | ----------------------- | ------------------------------------------------------------------------------------------------------ |
| основные         | `bot`                   | Бот-краулер, основной runtime обхода.                                                                  |
| основные         | `flask`                 | `app-service`, входная точка `/bot/*`, orchestration и UI-роуты.                                       |
| основные         | `tags_service`          | FastAPI-сервис тегов и tag API.                                                                        |
| основные         | `semantic_service`      | FastAPI-сервис семантического анализа текста.                                                          |
| основные         | `ip_service`            | FastAPI-сервис геолокации и IP lookup.                                                                 |
| основные         | `storage_service`       | FastAPI-сервис долговременного хранения шагов и экспорта.                                              |
| основные         | `data_service`          | FastAPI-сервис чтения локальной SQLite-базы URL и статистики.                                          |
| основные         | `keywords_service`      | Отдельный сервис классификации текста по словарю ключевых слов.                                        |
| основные         | `html-renderer-service` | Сервис рендеринга страниц в изображения для screenshot pipeline.                                       |
| фоновые          | `backfill-worker`       | Фоновый worker, который добирает пропущенные URL из `data_service` и прогоняет их через `app-service`. |
| фоновые          | `worker`                | RQ worker, выполняет jobs из `app-service/flask/jobs.py`.                                              |
| фоновые          | `worker2`               | Дополнительный RQ worker, выполняет jobs из `app-service/flask/jobs.py`.                               |
| фоновые          | `worker3`               | Дополнительный RQ worker, выполняет jobs из `app-service/flask/jobs.py`.                               |
| инфраструктурные | `redis`                 | Очередь задач и live state.                                                                            |
| инфраструктурные | `tags_db`               | PostgreSQL для `tags_service`, `semantic_service`, `ip_service`.                                       |
| инфраструктурные | `jaeger`                | Tracing / OTEL backend.                                                                                |
| инфраструктурные | `rq-dashboard`          | UI для мониторинга очередей RQ.                                                                        |
| инфраструктурные | `frontend`              | Frontend dev container.                                                                                |
| инфраструктурные | `spacyapi`              | Отдельный legacy spaCy API контейнер.                                                                  |

> [!note]
> `worker`, `worker2` и `worker3` ходят в `tags_service`, `semantic_service`, `storage_service`, `ip_service` и `html-renderer-service`.

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
