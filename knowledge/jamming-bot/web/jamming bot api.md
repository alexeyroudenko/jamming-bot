---
title: jamming bot api
aliases:
  - Jamming Bot API
note_type: note
project: "[[jamming-bot/Jamming Bot]]"
parent: "[[web/API|Jamming Bot API Index]]"
tags:
  - api
  - web
  - jamming-bot
---

# jamming bot api

Сводная карта HTTP-эндпоинтов проекта, собранная по `app-service`, сервисным API и ingress-конфигурации.

> [!note]
> В таблицах ниже указан внешний путь в том виде, в каком он доступен снаружи.

## App / gateway

| endpoint                                                 | описание                                              |
| -------------------------------------------------------- | ----------------------------------------------------- |
| `GET /`                                                  | Главная страница бота.                                |
| `GET /status`                                            | Простой health-check app-service.                     |
| `GET /login` / `POST /login`                             | Форма логина и отправка credentials.                  |
| `GET /logout`                                            | Выход из сессии.                                      |
| `GET /help/`                                             | Help page.                                            |
| `GET /metrics`                                           | Prometheus-метрики app-service.                       |
| `GET /screenshots/`                                      | UI-страница со скриншотами.                           |
| `GET /tags/`                                             | 2D tag cloud page.                                    |
| `GET /tags/3d/`                                          | 3D tag cloud page.                                    |
| `GET /geo/`                                              | Geo globe page.                                       |
| `GET /tags/phrases/`                                     | Phrases page.                                         |
| `GET /tags/constellation/`                               | Constellation page.                                   |
| `GET /tags/vectorfield/`                                 | 2D vector field page.                                 |
| `GET /tags/vectorfield-3d/`                              | 3D vector field page.                                 |
| `GET /tags/chaos-attractor/`                             | Chaos attractor page.                                 |
| `GET /tags/sentiment-vortex/`                            | Sentiment vortex page.                                |
| `GET /path/map/`                                         | Path map page.                                        |
| `GET /queue/`                                            | Очередь фоновых jobs.                                 |
| `GET /queue/job/<job_id>/`                               | Детальная страница job в очереди.                     |
| `GET /jobs/<job_id>`                                     | JSON-статус job.                                      |
| `GET /delete_job/<job_id>`                               | Удалить job из очереди.                               |
| `GET /queue/clear_failed/` / `POST /queue/clear_failed/` | Очистка failed jobs.                                  |
| `GET /queue/clear_all/` / `POST /queue/clear_all/`       | Полная очистка очереди.                               |
| `GET /ctrl/`                                             | Control panel.                                        |
| `GET /ctrl/<action>/`                                    | Триггер control action.                               |
| `GET /set/<v>/`                                          | Установить одно значение и отправить Socket.IO event. |
| `POST /set_values/`                                      | Отправить набор значений в realtime-канал.            |
| `GET /set_tick/` / `POST /set_tick/`                     | Control endpoint для tick / restart action.           |
| `POST /bot/events/<event_id>/`                           | Внешний bot event hook.                               |
| `POST /bot/sublink/add/`                                 | Добавление sublink event.                             |
| `GET /bot/step/` / `POST /bot/step/`                     | Основной ingest шага бота.                            |
| `GET /spacy/` / `POST /spacy/`                           | Тестовый spaCy proxy endpoint.                        |
| `GET /screenshoter/` / `POST /screenshoter/`             | Тестовый screenshots endpoint.                        |
| `GET /test/service/`                                     | Тестовый endpoint для tags-service cleanup.           |
| `GET /test/service_words/`                               | Тестовый endpoint для создания tag.                   |
| `GET /add_analyze_job/` / `POST /add_analyze_job/`       | Поставить analyze job в очередь.                      |
| `GET /add_wait_job/<num_iterations>`                     | Поставить wait job в очередь.                         |
| `POST /analyze/data/`                                    | Echo / test endpoint для analyze payload.             |
| `GET /semantic/vars/` / `POST /semantic/vars/`           | Вернуть semantic vars payload.                        |
| `GET /semantic/ent/` / `POST /semantic/ent/`             | Тестовый semantic entity proxy.                       |

## Public JSON API via app-service

| endpoint                                                               | описание                                                        |
| ---------------------------------------------------------------------- | --------------------------------------------------------------- |
| `GET /api/tags/get/`                                                   | Получить сгруппированные теги из tags-service.                  |
| `POST /api/tags/embeddings/`                                           | Построить embeddings и similarity links для tag visualizations. |
| `POST /api/tags/combine/`                                              | Прокси к semantic combine API.                                  |
| `GET /api/tags/sentiment-vortex/` / `POST /api/tags/sentiment-vortex/` | Собрать phrases и sentiment stats для vortex page.              |
| `POST /api/tags/add_one/`                                              | Добавить один tag.                                              |
| `GET /api/tags/add/` / `POST /api/tags/add/`                           | Добавить один или несколько tag batch-ами.                      |
| `GET /api/tags/add_tags_from_steps/`                                   | Фоновая пересборка тегов из steps.                              |
| `GET /api/tags/clean/`                                                 | Фоновая очистка tag storage.                                    |
| `GET /api/analyze_all/` / `POST /api/analyze_all/`                     | Полный semantic analysis текста через semantic-service.         |
| `POST /api/data`                                                       | Echo JSON endpoint.                                             |
| `GET /api/steps/`                                                      | Список steps из очереди / job metadata.                         |
| `GET /api/step/<step_num>/`                                            | Агрегированное состояние шага из Redis hash.                    |
| `GET /api/step/<step_num>`                                             | Legacy detail API по step number.                               |
| `GET /api/storage_step/<step_num>/`                                    | Прокси к storage-service: один сохранённый step.                |
| `GET /api/storage_latest/`                                             | Прокси к storage-service: последние сохранённые steps.          |
| `GET /api/storage_ids/`                                                | Прокси к storage-service: список id / numbers.                  |
| `GET /api/storage_geo/`                                                | Упрощённый geo JSON для globe page.                             |
| `GET /api/graph/`                                                      | Тестовый graph endpoint.                                        |

## Direct service APIs on main host

| endpoint                                            | описание                                          |
| --------------------------------------------------- | ------------------------------------------------- |
| `GET /tags/api/`                                    | Корень tags-service; API info / redirect target.  |
| `GET /tags/api/healthz`                             | Health-check tags-service.                        |
| `GET /tags/api/api/v1/tags/docs`                    | Swagger docs tags-service.                        |
| `GET /tags/api/api/v1/tags/openapi.json`            | OpenAPI schema tags-service.                      |
| `POST /tags/api/api/v1/tags/`                       | Создать tag напрямую в tags-service.              |
| `GET /tags/api/api/v1/tags/`                        | Получить все tags.                                |
| `GET /tags/api/api/v1/tags/{id}/`                   | Получить tag по id.                               |
| `PUT /tags/api/api/v1/tags/{id}/`                   | Обновить tag по id.                               |
| `DELETE /tags/api/api/v1/tags/{id}/`                | Удалить tag по id.                                |
| `GET /tags/api/api/v1/tags/tags/group/`             | Получить сгруппированные tags с `count` и `page`. |
| `GET /tags/api/3d/`                                 | Legacy redirect / 404 для старого UI path.        |
| `GET /tags/api/phrases/`                            | Legacy redirect / 404 для старого UI path.        |
| `GET /semantic/health`                              | Health-check semantic-service.                    |
| `GET /semantic/api/v1/semantic/docs`                | Swagger docs semantic-service.                    |
| `GET /semantic/api/v1/semantic/openapi.json`        | OpenAPI schema semantic-service.                  |
| `POST /semantic/api/v1/semantic/tags/`              | Извлечь words / phrases / sim из текста.          |
| `GET /semantic/api/v1/semantic/analyze_all/`        | Полный semantic analysis по query param `text`.   |
| `POST /semantic/api/v1/semantic/analyze_all/`       | Полный semantic analysis по JSON body.            |
| `POST /semantic/api/v1/semantic/combine/`           | Сгенерировать phrases из списка words.            |
| `POST /semantic/api/v1/semantic/sentiment-phrases/` | Sentiment analysis для phrases.                   |
| `GET /ip/api/v1/ip/docs`                            | Swagger docs ip-service.                          |
| `GET /ip/api/v1/ip/openapi.json`                    | OpenAPI schema ip-service.                        |
| `GET /ip/api/v1/ip/{ip}/`                           | Геолокация по IP.                                 |
| `POST /storage/store`                               | Сохранить step в storage-service.                 |
| `PATCH /storage/update/step/{number}`               | Частично обновить сохранённый step.               |
| `POST /storage/exists/batch`                        | Проверить набор step numbers на существование.    |
| `GET /storage/get/step/{number}`                    | Получить сохранённый step по number.              |
| `GET /storage/get/latest`                           | Получить последние сохранённые steps.             |
| `GET /storage/get/ids`                              | Получить список ids / numbers из storage.         |
| `GET /storage/export/csv`                           | Экспорт steps в CSV.                              |
| `GET /data/healthz`                                 | Health-check data-service.                        |
| `GET /data/api/urls/stats`                          | Статистика по таблице URL.                        |
| `GET /data/api/urls`                                | Список URL c пагинацией и фильтрами.              |
| `GET /data/api/urls/hostnames`                      | Distinct hostnames с counts.                      |
| `GET /data/api/urls/export`                         | Экспорт URL-таблицы в CSV.                        |
| `POST /keywords/classify`                           | Классификация текста по keywords dictionary.      |
| `GET /render/`                                      | Root html-renderer service с краткой справкой.    |
| `GET /render/render`                                | Рендер страницы в screenshot по query params.     |

## Alternate app hosts

| endpoint | описание |
| --- | --- |
| `https://app.jamming-bot.arthew0.online/...` | Тот же `app-service`, что и на основном host, без дополнительных prefix-ов сервисов. |
| `https://b0ts.arthew0.online/...` | Альтернативный host для `app-service`. |
| `https://rq.jamming-bot.arthew0.online/` | RQ dashboard ingress. |
| `https://jaeger.jamming-bot.arthew0.online/` | Jaeger UI ingress. |

## Related

- [[web/API|Jamming Bot API Index]]
- [[Jamming bot web|Jamming Bot Web]]
- [[Get tags]]
