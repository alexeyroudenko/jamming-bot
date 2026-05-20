---
title: jamming bot api
aliases:
  - Jamming Bot API
note_type: note
project: "[[jamming-bot/Jamming Bot]]"
parent: "[[web/API|Jamming Bot API Index]]"
updated: 2026-05-20
tags:
  - api
  - web
  - jamming-bot
---

# jamming bot api

Сводная карта HTTP-эндпоинтов проекта, собранная по `app-service`, сервисным API и ingress-конфигурации.

> [!note]
> В таблицах ниже указан внешний путь в том виде, в каком он доступен снаружи.
> Swagger UI у сервисов использует **относительный** `openapi.json`, чтобы за ingress с strip-префиксом схема подтягивалась с того же префикса (`/tags/openapi.json`, `/semantic/openapi.json`, …), а не с корня сайта.
> `sublink`-события для bot page теперь в штатном режиме идут через Redis Pub/Sub (`bot-service -> redis -> app-service -> Socket.IO`).
> `POST /bot/sublink/add/` оставлен как legacy fallback для совместимости.

## App / gateway

### Root / auth

| endpoint | описание |
| --- | --- |
| `GET /` | Главная страница бота. |
| `GET /status` | Простой health-check app-service. |
| `GET /login` | Форма логина. |
| `POST /login` | Отправка credentials. |
| `GET /logout` | Выход из сессии. |
| `GET /help/` | Help page. |
| `GET /metrics` | Prometheus-метрики app-service. |

### Pages

| endpoint | описание |
| --- | --- |
| `GET /screenshots/` | UI-страница со скриншотами. |
| `GET /tags/` | 2D tag cloud page. |
| `GET /tags/3d/` | 3D tag cloud page. |
| `GET /geo/` | Geo globe page. |
| `GET /path/map/` | Path map page. |
| `GET /steps/` | Steps page с fullscreen PNG и tooltip по шагам. |

## Tags

> [!note]
> Тот же tag-related UI и поток данных можно открывать с выделенного host [https://tags.jamming-bot.arthew0.online/](https://tags.jamming-bot.arthew0.online/) — ingress ведёт на **tags-service**; при настроенном `TAGS_UI_REDIRECT_ORIGIN` корень `/` редиректит на `GET /tags/` основного app. REST API tags-service с этого host — без внешнего префикса `/tags/`, см. [[#Tags service — прямой host]].

### Tag pages

| endpoint | описание |
| --- | --- |
| `GET /tags/phrases/` | Phrases page. |
| `GET /tags/constellation/` | Constellation page. |
| `GET /tags/vectorfield/` | 2D vector field page. |
| `GET /tags/vectorfield-3d/` | 3D vector field page. |
| `GET /tags/chaos-attractor/` | Chaos attractor page. |
| `GET /tags/sentiment-vortex/` | Sentiment vortex page. |

## App / gateway

### Queue

| endpoint | описание |
| --- | --- |
| `GET /queue/` | Очередь фоновых jobs. |
| `GET /queue/job/<job_id>/` | Детальная страница job в очереди. |
| `GET /jobs/<job_id>` | JSON-статус job. |
| `GET /delete_job/<job_id>` | Удалить job из очереди. |
| `GET /queue/clear_failed/` | Очистка failed jobs. |
| `POST /queue/clear_failed/` | Очистка failed jobs. |
| `GET /queue/clear_all/` | Полная очистка очереди. |
| `POST /queue/clear_all/` | Полная очистка очереди. |
| `GET /add_analyze_job/` | Поставить analyze job в очередь. |
| `POST /add_analyze_job/` | Поставить analyze job в очередь. |
| `GET /add_wait_job/<num_iterations>` | Поставить wait job в очередь. |

### Control

| endpoint | описание |
| --- | --- |
| `GET /ctrl/` | Control panel. |
| `GET /ctrl/<action>/` | Триггер control action. |
| `GET /set/<v>/` | Установить одно значение и отправить Socket.IO event. |
| `POST /set_values/` | Отправить набор значений в realtime-канал. |
| `GET /set_tick/` | Control endpoint для tick / restart action. |
| `POST /set_tick/` | Control endpoint для tick / restart action. |

### Bot / test endpoints

| endpoint | описание |
| --- | --- |
| `POST /bot/events/<event_id>/` | Внешний bot event hook. |
| `POST /bot/sublink/add/` | Legacy fallback для sublink event. |
| `POST /bot/inject/text/` | Сценарий inject: stop → разбор графа на `/` → RQ `analyze` + `analyze_semantic` → показ на главной и сборка графа на `/semantic3d/` → через 60 с после `semantic_collect` — `start` и возврат demo на 3D. См. [[#Text inject — POST /bot/inject/text/]]. |
| `GET /bot/step/` | Основной ingest шага бота. |
| `POST /bot/step/` | Основной ingest шага бота. |
| `GET /spacy/` | Тестовый spaCy proxy endpoint. |
| `POST /spacy/` | Тестовый spaCy proxy endpoint. |
| `GET /screenshoter/` | Тестовый screenshots endpoint. |
| `POST /screenshoter/` | Тестовый screenshots endpoint. |
| `GET /test/service/` | Тестовый endpoint для tags-service cleanup. |
| `GET /test/service_words/` | Тестовый endpoint для создания tag. |
| `POST /analyze/data/` | Echo / test endpoint для analyze payload. |
| `GET /semantic/vars/` | Вернуть semantic vars payload. |
| `POST /semantic/vars/` | Вернуть semantic vars payload. |
| `GET /semantic/ent/` | Тестовый semantic entity proxy. |
| `POST /semantic/ent/` | Тестовый semantic entity proxy. |

### Text inject — POST /bot/inject/text/

Публичный эндпоинт (префикс `/bot/`, без логина). Параллельный второй inject → **409** (`inject already active`).

**Тело:** `application/json` `{"text": "…"}` или form `text=…`. Не пустой, до 8000 символов.

**Ответ:** `202` `{"ok": true, "inject_id": "<uuid>"}` — сценарий в фоновом потоке.

**Последовательность (сервер):**

1. Redis `ctrl` → `stop` (бот `spider.is_active = false`).
2. Socket.IO: `inject_begin`, `graph_dismantle` (`interval_ms`: 20).
3. Пауза 5 с + оценка разбора графа (~3 с).
4. RQ `jobs.analyze` → emit `analyzed`; `inject_display` с текстом.
5. Socket.IO `semantic_inject_begin` → RQ `jobs.analyze_semantic` → `semantic_collect`.
6. Через **60 с** после успешного `semantic_collect` — Redis `ctrl` → `start`, `semantic_restore_demo`, `inject_end`. При ошибке анализа — restore не позже **120 с** от старта inject.

**Socket.IO (server → client):**

| event | страницы | назначение |
| --- | --- | --- |
| `inject_begin` | `/` | флаг inject; не добавлять узлы на `step` |
| `graph_dismantle` | `/` | снять узлы графа по одному каждые 20 ms |
| `inject_display` | `/` | показать переданный текст в `#log_text` |
| `analyzed` | `/` | phrases/words (как после шага бота) |
| `semantic_inject_begin` | `/semantic3d/` | очистить 3D-граф, `demoCompleted = true` |
| `semantic_collect` | `/semantic3d/` | собрать граф из `dependency_lines` |
| `semantic_restore_demo` | `/semantic3d/` | `semanticReset` + demo edges |
| `inject_end` | `/` | сброс флага inject |

**Client → server (опционально):** `graph_dismantle_done` после завершения разбора на главной.

**Пример:**

```bash
curl -sS -X POST https://jamming-bot.arthew0.online/bot/inject/text/ \
  -H 'Content-Type: application/json' \
  -d '{"text":"Пример фразы для семантического разбора."}'
```

## Public JSON API via app-service

### Tags

| endpoint | описание |
| --- | --- |
| `GET /api/tags/get/` | Получить сгруппированные теги из tags-service. |
| `POST /api/tags/embeddings/` | Построить embeddings и similarity links для tag visualizations (прокси к semantic `tag-embeddings/`). Body и ответ — см. [[#Tag embeddings — формат запроса]]. |
| `POST /api/tags/combine/` | Прокси к semantic combine API. |
| `GET /api/tags/sentiment-vortex/` | Собрать phrases и sentiment stats для [[pages/Sentiment vortex|Sentiment vortex]] (см. [[#Sentiment vortex — прокси app-service]]). |
| `POST /api/tags/sentiment-vortex/` | То же, что GET (тело запроса не используется). |
| `POST /api/tags/add_one/` | Добавить один tag. |
| `GET /api/tags/add/` | Добавить один или несколько tag batch-ами. |
| `POST /api/tags/add/` | Добавить теги списком (прокси в tags-service `POST .../tags/bulk/`). |
| `GET /api/tags/add_tags_from_steps/` | Фоновая пересборка тегов из steps. |
| `GET /api/tags/clean/` | Фоновая очистка tag storage. |

#### Sentiment vortex — прокси app-service

`GET` и `POST /api/tags/sentiment-vortex/` без тела выполняют одну цепочку:

1. `GET` …/tags/tags/group/ у **tags-service** → имена тегов, отсортированные по `count`.
2. `POST` …/semantic/combine/ у **semantic-service** — `words`, `limit: 128`, `max_phrases: 256` → список фраз.
3. `POST` …/semantic/sentiment-phrases/ — те же фразы, `limit: 256` → VADER: у каждой фразы `polarity` = `compound`, `subjectivity` = `1 - neu` (см. `semantic-service`).

Успешный JSON: `{ "phrases": [ { "text", "polarity", "subjectivity" }, ... ], "stats": { "mean_polarity", "pct_positive", "pct_negative", "pct_neutral", "count" } }`. Ошибка любого шага — ответ **502**, `phrases: []`, ослабленный `stats`, поле `error`.

Страница визуализации: [[pages/Sentiment vortex|Sentiment vortex]].

### Analyze

| endpoint | описание |
| --- | --- |
| `GET /api/analyze_all/` | Полный разбор текста (spaCy `en_core_web_lg`) — см. [[#Analyze all — полный разбор текста]]. |
| `POST /api/analyze_all/` | То же, тело JSON или form — см. [[#Analyze all — полный разбор текста]]. |
| `POST /api/data` | Echo JSON endpoint. |

#### Analyze all — полный разбор текста

Публичный URL на проде: [https://jamming-bot.arthew0.online/api/analyze_all/](https://jamming-bot.arthew0.online/api/analyze_all/)

**Назначение.** Один запрос прогоняет входной текст через spaCy (`en_core_web_lg`) и возвращает структурированный срез: noun chunks, глаголы, NER, ключевые слова, подлежащие/дополнения и дерево зависимостей. В `app-service` это тонкий **прокси** в **semantic-service** (`POST …/api/v1/semantic/analyze_all/` с телом `{"text": "…"}`); логика разбора — в `semantic-service/app/api/semantic.py`, функция `_analyze_all`.

> [!warning]
> **Авторизация на основном host.** Путь `/api/analyze_all/` **не** входит в `PUBLIC_PREFIXES` app-service. Запрос без сессии (браузер, `curl` без cookie) получает **302 на `/login`** — поэтому открытие ссылки в адресной строке показывает форму входа, а не JSON. Для API: сначала `POST /login` с `AUTH_USER` / `AUTH_PASS`, затем запрос с cookie сессии. Альтернатива без логина в app — прямой вызов semantic host (ниже).

**Методы и параметры**

| метод | как передать `text` | примечание |
| --- | --- | --- |
| `GET` | query `?text=…` | удобно для быстрых проверок и ссылок; длинный текст — URL-encode |
| `POST` | JSON `{"text": "…"}` | предпочтительно для больших фрагментов |
| `POST` | form field `text` | fallback, если JSON не отправлен |

Пустой `text` → **400** `{"error": "text parameter is required"}` (прокси app-service). Semantic-service при пустом тексте отдаёт **400** с `detail: "text parameter is required"` / `"text is required"`.

**Успешный ответ (200, JSON)**

| поле | тип | описание |
| --- | --- | --- |
| `noun_phrases` | `string[]` | Noun chunks spaCy (`doc.noun_chunks`), порядок как в модели |
| `verbs` | `string[]` | Леммы глаголов (`pos_ == "VERB"`) |
| `entities` | `{text, label}[]` | Named entities (NER): `text` — span, `label` — тип (`PERSON`, `ORG`, …) |
| `keywords` | `string[]` | Токены `NOUN`/`ADJ` без стоп-слов, в нижнем регистре (без ранжирования по частоте, в отличие от `POST …/tags/`) |
| `subjects` | `string[]` | Токены с `dep_ == "nsubj"` |
| `objects` | `string[]` | Токены с `dep_ == "dobj"` |
| `dependency` | `{token, dep, head}[]` | По одному токену: текст, тип зависимости, голова |

**Ошибки прокси (app-service)**

| код | когда |
| --- | --- |
| **400** | нет `text` |
| **503** | semantic-service недоступен, таймаут или не-2xx: `{"error": "Semantic service unavailable", "detail": "…"}` |

Таймаут HTTP-прокси: **30 с**. В фоновой очереди (`analyze_semantic` в `jobs.py`) к semantic уходит тот же URL с таймаутом `HTTP_SEMANTIC_ANALYZE_ALL_TIMEOUT_SEC` (по умолчанию **12 с**) и обрезкой сниппета до **2500** символов.

**Пример GET (после логина)**

```http
GET /api/analyze_all/?text=Jammingbot%20is%20a%20fantasy%20on%20the%20theme%20of%20a%20post-apocalyptic%20future HTTP/1.1
Host: jamming-bot.arthew0.online
Cookie: session=…
```

Пример из журнала: [[journal/2026-03-17]] (раздел `/api/analyze_all/`).

**Пример POST (JSON)**

```bash
# 1) сессия
curl -sS -c /tmp/jb-cookies.txt -b /tmp/jb-cookies.txt \
  -X POST 'https://jamming-bot.arthew0.online/login' \
  -d 'username=YOUR_USER&password=YOUR_PASS' -L -o /dev/null

# 2) analyze
curl -sS -b /tmp/jb-cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"text":"Jammingbot is a fantasy on the theme of a post-apocalyptic future."}' \
  'https://jamming-bot.arthew0.online/api/analyze_all/'
```

**Пример фрагмента ответа**

```json
{
  "noun_phrases": ["Jammingbot", "a fantasy", "the theme", "a post-apocalyptic future"],
  "verbs": ["be"],
  "entities": [],
  "keywords": ["jammingbot", "fantasy", "theme", "future"],
  "subjects": ["Jammingbot"],
  "objects": [],
  "dependency": [
    {"token": "Jammingbot", "dep": "nsubj", "head": "is"},
    {"token": "is", "dep": "ROOT", "head": "is"}
  ]
}
```

**Прямой вызов semantic-service (без app-login)**

На выделенном host префикса `/semantic/` нет; ingress не требует сессии app-service:

| URL | метод |
| --- | --- |
| `https://semantic.jamming-bot.arthew0.online/api/v1/semantic/analyze_all/?text=…` | `GET` |
| `https://semantic.jamming-bot.arthew0.online/api/v1/semantic/analyze_all/` | `POST`, body `{"text": "…"}` |

На основном сайте те же контракты: `GET /semantic/api/v1/semantic/analyze_all/` и `POST /semantic/api/v1/semantic/analyze_all/` (после strip `/semantic/`).

Если spaCy не загружен (`nlp_lg is None`), semantic отвечает **503** `SpaCy model not loaded`.

**Отличие от `POST …/semantic/tags/`**

| | `analyze_all` | `POST /semantic/api/v1/semantic/tags/` (и тестовые `/spacy/`, `/semantic/ent/`) |
| --- | --- | --- |
| Предобработка | сырой текст в spaCy | стоп-слова, пунктуация, леммы, топ keywords по частоте |
| Выход | `noun_phrases`, `verbs`, `entities`, `dependency`, … | `words`, `hrases`, `sim`, `entities`, `dependency` (строки `token>head`) |
| Использование | полный срез для пайплайна / отладки | лёгкий тегинг и similarity к эталонному запросу «happiness love life…» |

**Внутренний пайплайн бота**

После успешного `analyze` шага бот может поставить RQ-job `analyze_semantic`: сниппет страницы → тот же `analyze_all` в semantic → результат в `semantic` JSON job meta (`noun_phrases`, `entities`, `dependency_lines`, …). Ручной аналог очереди — `POST /add_analyze_job/` (другой job `analyze`, не путать с `analyze_all`).

**CORS.** На маршруте включён `@cross_origin()`; глобально app разрешает credentials для origin из `CORS_ALLOWED_ORIGINS` (в т.ч. `https://jamming-bot.arthew0.online`). Без сессии браузерный `fetch` всё равно упрётся в редирект на login.

### Steps

| endpoint | описание |
| --- | --- |
| `GET /api/steps/` | Список steps из очереди / job metadata. |
| `GET /api/step/<step_num>/` | Агрегированное состояние шага из Redis hash. |
| `GET /api/step/<step_num>` | Legacy detail API по step number. |

### Storage

| endpoint                            | описание                                               |
| ----------------------------------- | ------------------------------------------------------ |
| `GET /api/storage_step/<step_num>/` | Прокси к storage-service: один сохранённый step.       |
| `GET /api/storage_latest/`          | Прокси к storage-service: последние сохранённые steps. |
| `GET /api/storage_ids/`             | Прокси к storage-service: список id / numbers.         |
| `GET /api/storage_geo/`             | Упрощённый geo JSON для globe page.                    |
|                                     |                                                        |

### Graph

| endpoint | описание |
| --- | --- |
| `GET /api/graph/` | Тестовый graph endpoint. |

## Steps service

> [!note]
> `GET /steps/?type=` поддерживает режимы `status_code`, `text_length`, `timestamp_delta`, `screenshot`, `latitude_longitude`, `error`.
> Сам PNG-фон и latest-данные внутри `steps-service` берутся через app-service proxy endpoints `storage_img` и `storage_latest`.

| endpoint | описание |
| --- | --- |
| `GET /steps/` | HTML-страница steps-service с fullscreen PNG-фоном. |
| `GET /steps/?type=<mode>` | Та же страница, но с выбранным режимом tooltip / auto-mode. |
| `GET /steps/healthz` | Health-check steps-service и статус кэша PNG. |
| `GET /steps/api/image` | Актуальный PNG, который steps-service проксирует и кэширует. |
| `GET /steps/api/latest` | Прокси latest-steps JSON для UI-режимов и tooltip. |

## Direct service APIs on main host

### Tags service — прямой host

На основном сайте к tags-service обращаются с префиксом `/tags/` (после strip у сервиса пути без этого префикса). На отдельном ingress host префикса нет:

| URL | описание |
| --- | --- |
| `https://tags.jamming-bot.arthew0.online/` | Корень tags-service: при редиректе — на UI `.../tags/` app-service; иначе JSON с `api`, `docs`, `openapi`. |
| `https://tags.jamming-bot.arthew0.online/docs` | Swagger UI tags-service. |
| `https://tags.jamming-bot.arthew0.online/openapi.json` | OpenAPI schema. |
| `https://tags.jamming-bot.arthew0.online/api/v1/tags/...` | Те же REST-методы, что в таблице ниже для путей вида `/tags/api/...` на основном host (см. маппинг путей в `tags-service`). |
| `https://tags.jamming-bot.arthew0.online/healthz` | Health-check. |

### Tags service

| endpoint | описание |
| --- | --- |
| `GET /tags/api/` | Корень tags-service; API info / redirect target. |
| `GET /tags/api/healthz` | Health-check tags-service. |
| `GET /tags/docs` | Swagger UI tags-service (после strip `/tags` → `/docs` у сервиса). |
| `GET /tags/openapi.json` | OpenAPI schema tags-service. |
| `GET /tags/api/api/v1/tags/` | Получить все tags. |
| `POST /tags/api/api/v1/tags/` | Создать tag напрямую в tags-service. |
| `POST /tags/api/api/v1/tags/bulk/` | Массовое добавление: тело `{"names": [...]}` (та же семантика count, что у POST /). |
| `GET /tags/api/api/v1/tags/{id}/` | Получить tag по id. |
| `PUT /tags/api/api/v1/tags/{id}/` | Обновить tag по id. |
| `DELETE /tags/api/api/v1/tags/{id}/` | Удалить tag по id. |
| `GET /tags/api/api/v1/tags/tags/group/` | Получить сгруппированные tags с `count` и `page`. |
| `GET /tags/api/3d/` | Legacy redirect / 404 для старого UI path. |
| `GET /tags/api/phrases/` | Legacy redirect / 404 для старого UI path. |

### Semantic service — прямой host

На основном сайте к semantic-service обращаются с префиксом `/semantic/` (после strip у сервиса путь без этого префикса). На отдельном ingress host префикса нет:

| URL | описание |
| --- | --- |
| `https://semantic.jamming-bot.arthew0.online/health` | Health-check semantic-service. |
| `https://semantic.jamming-bot.arthew0.online/docs` | Swagger UI. |
| `https://semantic.jamming-bot.arthew0.online/openapi.json` | OpenAPI schema. |
| `https://semantic.jamming-bot.arthew0.online/api/v1/semantic/tag-embeddings/` | **POST** — embeddings для массива слов (см. [[#Tag embeddings — формат запроса]]). |
| `https://semantic.jamming-bot.arthew0.online/api/v1/semantic/...` | Остальные методы из таблицы ниже, без внешнего префикса `/semantic/`. |

### Semantic service

| endpoint | описание |
| --- | --- |
| `GET /semantic/health` | Health-check semantic-service. |
| `GET /semantic/docs` | Swagger UI semantic-service (после strip `/semantic` → `/docs`). |
| `GET /semantic/openapi.json` | OpenAPI schema semantic-service. |
| `POST /semantic/api/v1/semantic/tags/` | Извлечь words / phrases / sim из текста. |
| `GET /semantic/api/v1/semantic/analyze_all/` | Полный semantic analysis по query param `text`. |
| `POST /semantic/api/v1/semantic/analyze_all/` | Полный semantic analysis по JSON body. |
| `POST /semantic/api/v1/semantic/combine/` | Сгенерировать phrases из списка words. |
| `POST /semantic/api/v1/semantic/sentiment-phrases/` | Sentiment analysis для phrases. |
| `POST /semantic/api/v1/semantic/tag-embeddings/` | Embeddings + similarity links для массива слов. Тот же **POST** на прямом host: `https://semantic.jamming-bot.arthew0.online/api/v1/semantic/tag-embeddings/`. Body и ответ — см. [[#Tag embeddings — формат запроса]]. |

### IP service

| endpoint | описание |
| --- | --- |
| `GET /ip/api/v1/ip/docs` | Swagger docs ip-service. |
| `GET /ip/api/v1/ip/openapi.json` | OpenAPI schema ip-service. |
| `GET /ip/api/v1/ip/{ip}/` | Геолокация по IP. |

### Storage service

| endpoint | описание |
| --- | --- |
| `GET /storage/docs` | Swagger UI storage-service (после strip `/storage` → `/docs`). |
| `GET /storage/openapi.json` | OpenAPI schema storage-service. |
| `POST /storage/store` | Сохранить step в storage-service. |
| `PATCH /storage/update/step/{number}` | Частично обновить сохранённый step. |
| `POST /storage/exists/batch` | Проверить набор step numbers на существование. |
| `GET /storage/get/step/{number}` | Получить сохранённый step по number. |
| `GET /storage/get/latest` | Получить последние сохранённые steps. |
| `GET /storage/get/ids` | Получить список ids / numbers из storage. |
| `GET /storage/export/csv` | Экспорт steps в CSV. |

### Data / keywords

| endpoint | описание |
| --- | --- |
| `GET /data/docs` | Swagger UI data-service (после strip `/data` → `/docs`). |
| `GET /data/openapi.json` | OpenAPI schema data-service. |
| `GET /data/healthz` | Health-check data-service. |
| `GET /data/api/urls/stats` | Статистика по таблице URL. |
| `GET /data/api/urls` | Список URL c пагинацией и фильтрами. |
| `GET /data/api/urls/hostnames` | Distinct hostnames с counts. |
| `GET /data/api/urls/export` | Экспорт URL-таблицы в CSV. |
| `POST /keywords/classify` | Классификация текста по keywords dictionary. |

### Render

| endpoint | описание |
| --- | --- |
| `GET /render/` | Root html-renderer service с краткой справкой. |
| `GET /render/render` | Рендер страницы в screenshot по query params. |

## Alternate app hosts

| endpoint | описание |
| --- | --- |
| `https://app.jamming-bot.arthew0.online/...` | Тот же `app-service`, что и на основном host, без дополнительных prefix-ов сервисов. |
| `https://b0ts.arthew0.online/...` | Альтернативный host для `app-service`. |
| `https://tags.jamming-bot.arthew0.online/...` | **tags-service** на корневом path `/` (не путать с HTML-страницами `GET /tags/...` у app-service на основном host). Подробнее — [[#Tags service — прямой host]]. |
| `https://semantic.jamming-bot.arthew0.online/...` | **semantic-service** на корневом path `/`. Embeddings: `POST .../api/v1/semantic/tag-embeddings/`. Подробнее — [[#Semantic service — прямой host]]. |
| `https://rq.jamming-bot.arthew0.online/` | RQ dashboard ingress. |
| `https://jaeger.jamming-bot.arthew0.online/` | Jaeger UI ingress. |

## Tag embeddings — формат запроса

**Эндпоинты:**
- `POST https://semantic.jamming-bot.arthew0.online/api/v1/semantic/tag-embeddings/` — напрямую semantic-service (выделенный host, без префикса `/semantic/`)
- `POST /semantic/api/v1/semantic/tag-embeddings/` — тот же сервис на основном host (после strip `/semantic/`)
- `POST /api/tags/embeddings/` — через app-service прокси

**Request body (JSON):**

| поле | тип | default | описание |
| --- | --- | --- | --- |
| `words` | `string[]` | `[]` | Массив слов для embedding. |
| `max_words` | `int` | `48` | Максимум слов (clamp 4–80). |
| `min_sim` | `float` | `0.38` | Порог cosine similarity для links (clamp 0.15–0.99). |
| `max_links` | `int` | `160` | Максимум similarity links (clamp 8–400). |

**Пример запроса:**
```json
{
  "words": ["love", "chaos", "rhythm", "light"],
  "max_words": 48,
  "min_sim": 0.38,
  "max_links": 160
}
```

**Response (JSON):**

| поле | тип | описание |
| --- | --- | --- |
| `ok` | `bool` | Успешность. |
| `mode` | `string` | `"vectors"` — полный режим, `"sparse"` — < 2 валидных слов, `"unavailable"` — spaCy не загружен. |
| `words` | `string[]` | Отфильтрованный список слов, для которых есть вектор. |
| `vectors2d` / `vectors3d` | `float[][]` | 2D/3D проекции (первые компоненты spaCy-вектора, нормализованные). |
| `vectors2d_current` / `vectors3d_current` | `float[][]` | То же, что `vectors2d`/`vectors3d`. |
| `vectors2d_alt` / `vectors3d_alt` | `float[][]` | Альтернативная проекция (компоненты 3–5 вектора). |
| `directions2d` / `directions3d` | `float[][]` | Направления (нормализованные). |
| `links` | `{i, j, sim}[]` | Пары индексов слов с similarity ≥ `min_sim`, отсортированные по убыванию `sim`. |

> [!note]
> При батчевом экспорте всех тегов (`analyze/embed_tags.py`) слова отправляются порциями по `--batch-size` (default 80), т.к. `max_words` имеет ограничение 80. Подробнее — [[2026-03-31_Embed всех тэгов]].

## Related

- [[web/API|Jamming Bot API Index]]
- [[Jamming bot web|Jamming Bot Web]]
- [[Get tags]]
