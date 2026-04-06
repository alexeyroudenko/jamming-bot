---
title: Jamming Bot — данные и хранение
aliases:
  - Jamming bot данные и хранение
  - Jamming Bot data flow
note_type: dev
project: "[[jamming-bot/Jamming Bot]]"
parent: "[[dev/_index|Jamming Bot Dev Index]]"
dev_area: architecture
tags:
  - dev
  - data
  - storage
  - architecture
  - jamming-bot
created: 2026-04-07
updated: 2026-04-07
---

# Jamming Bot — данные и хранение

Конспект того, как проект собирает «шаги» обхода, где они лежат и как движутся между сервисами. Основано на коде `storage-service`, `app-service/flask`, `bot-service`, `backfill-worker`. Ниже — также **поля одного шага от краулера**, **обогащение микросервисами** и **своды по многим шагам** (ответы из обсуждения в репо).

> [!summary]
> **Источник правды по шагам** — SQL-база за [[Jamming bot microservices|storage-service]] (`steps`, `steps_analysis`). **Flask + RQ** обогащают запись и делают инкрементальные обновления. **Redis** — очереди и склейка состояния шага. **Бот** только шлёт сырой шаг в приложение.

## Кто такой Jamming Bot (кратко)

Художественный проект (data-driven / generative art) и рабочий стек: краулер, микросервисы, визуализации, веб. По замыслу — образ **бота без цели**, блуждающего по сети; технически — см. каноническую карточку [[Jamming Bot]] и [[Jamming Bot MOC]].

## Где лежат данные

- **PostgreSQL (или другая БД по `DATABASE_URI`)** — таблицы `steps` и `steps_analysis` в `storage-service`. Поля шага: номер, URL, текст, IP, статус, гео, теги/слова/фразы/сущности, семантика, длина текста, URL скриншота, `s3_key` и т.д. Анализ — отдельно (например палитра по `step_number`).
- **Redis** — очередь **RQ**, флаги (`do_storage`, `do_save`, фичефлаги пайплайна), хеши `step:{number}` для промежуточной склейки полей до записи в storage.

Код схемы: `storage-service/app/api/db.py`, модели входа/выхода: `storage-service/app/api/models.py`.

## Поток записи

1. **Краулер** (`bot-service`) — `POST` на [[jamming bot flask|Flask]] ` /bot/step/` (form-data).
2. **Flask** (`app.py`, маршрут `step`) кладёт черновик в Redis (`_save_to_step_hash`). При `do_storage == 1` сразу делает **`POST` JSON** на `storage-service` **`/store`** — ранняя запись с полями вроде `number`, `url`, `src`, `ip`, `status_code`, `timestamp`, усечённый `text`.
3. **RQ workers** (`app-service/flask/jobs.py`) — семантика, гео, analyze, screenshot и др. Результаты **дописываются** через **`PATCH /update/step/{number}`** (`_patch_storage` в `app.py`). Палитра и подобное — **`POST /analysis/store`**.
4. **Backfill-worker** читает URL из **data-service**, сверяет с storage (**`/exists/batch`**), затем прогоняет страницы через app-service в тихом режиме — та же цепочка записи.

> [!note]
> Отдельный путь: при `do_save` воркер семантики может писать в `/store` из `jobs.py` — это пересекается с общей политикой «сначала store, потом patch»; смотри актуальный `dostep` и флаги в Redis.

## Данные одного шага от краулера

Источник: класс `Step` в `bot-service/bot/bot.py`, отправка при `send_step`: `POST` на `/bot/step/` с `step.to_data()` (form-data). Перед отправкой из словаря убирается **`html`** (полный HTML в запрос **не уходит**).

**Поля в запросе:** `number`, `url`, `src`, `ip`, `status_code`, `headers` (JSON строка заголовков ответа, если был HTTP-ответ), `timestamp` (время создания `Step` в начале `do_step`), `text` (извлечённый текст только при успешном HTML и `200`).

**OSC** `/step`: `number`, `url`, `src`, `ip`, `status_code`, `timestamp` — без текста и заголовков.

**Нестандартные `status_code` у бота:** `403` (блоклист / robots), `900` / `901` (ошибки TLD), `801` (исключение при загрузке), `802` / `803` (прочие ошибки / пустая очередь URL).

Дальше Flask и RQ добавляют теги, гео, скриншоты и т.д. — это уже не поля самого бота.

## Данные после анализа микросервисами

Результаты RQ-джоб мержатся в Redis-хеш шага и для большинства событий уходят в storage через **`PATCH /update/step/{number}`** (`_patch_storage`). В строку `steps` попадают **только ключи из `STEP_FIELDS`** в `storage-service/app/api/db_manager.py` (лишние ключи в ответе джобы при обновлении игнорируются).

Состав `STEP_FIELDS`: `number`, `url`, `src`, `ip`, `status_code`, `timestamp`, `text`, `city`, `latitude`, `longitude`, `error`, `tags`, `words`, `hrases`, `entities`, `text_length`, `semantic`, `semantic_words`, `semantic_hrases`, `screenshot_url`, `s3_key`.

| Джоба | Внешние сервисы | Что даёт для шага |
| --- | --- | --- |
| `dostep` | `semantic_service` `/api/v1/semantic/tags/`, регистрация имён в `tags_service` | Списки семантических токенов (`sim` → в ответе джобы: `tags`, `semantic`, `semantic_words`; `semantic_hrases` в этой ветке часто пустой). Очистка текста; вызов семантики если длина текста **> 128**. |
| `do_geo` | `ip_service` `GET .../api/v1/ip/{ip}/` | `city`, `latitude`, `longitude`, `error` (+ `ip`). |
| `analyze` | локально **spaCy NER**, при длине текста **> 128** снова `semantic_service` | `entities` (`text`, `label`), `text_length`, `tags` / `words` / `hrases` (из полей ответа semantic). `noun_phrases` в `STEP_FIELDS` **нет** — в БД шага патчом не сохраняется. |
| `do_screenshot` | `html-renderer-service` `/render`, загрузка в **S3** | `screenshot_url`, `s3_key`, при ошибке рендера — `error`. |
| `image_analyze` | `image-analyze-service` | **`palette`** уходит **не** в PATCH строки `steps`, а в **`steps_analysis`** через `POST /analysis/store`. |

> [!warning]
> В `dostep` в объекте результата есть поля вроде `step`, `code`, `src_url` — они **не совпадают** с именами `number`, `status_code`, `src` в `STEP_FIELDS`. Имеет смысл сверять с `update_step` в коде, что реально дописывается в БД.

Событие **`image_analyzed`** в `app.py` обрабатывается отдельно: `_store_step_analysis`, не `_patch_storage`.

## Чтение, экспорт и агрегаты по многим шагам

**storage-service** (накопленные строки `steps`):

| API | Смысл |
| --- | --- |
| `GET /get/latest` | До **3000** последних записей по `id`, плюс `total_lines` — всего шагов; к строкам подмешивается `palette` из `steps_analysis`. |
| `GET /get/ids` | Отсортированные числовые номера шагов. |
| `GET /export/csv` | Потоковый дамп всех шагов (батчи). |
| `GET /export/img` | Одно PNG: сетка по всем шагам, режимы `presence`, `status_code`, `text_length`, `timestamp_delta`, `screenshot`. |

Прокси Flask: `/api/storage_latest/`, `/api/storage_ids/`, `/api/storage_img/`, `/api/storage_step/<n>/`.

**steps-service** — периодически тянет CSV/PNG со storage и держит снимок для UI «Steps Presence» (не один гигантский ответ в браузер за раз).

**Теги по всему прогону:** `GET /api/tags/get/` → `tags_service` `tags/group/` (пагинация).

**Семантика по куче фраз:** `POST /api/tags/combine/` → `semantic_service` `combine/` (лимит `max_phrases`).

**Граф по словам:** `POST /api/tags/embeddings/` — `tag_embeddings.build_embeddings_response` (spaCy `en_core_web_md`), 2D/3D и связи по сходству; слова могут быть собраны с многих шагов.

**Очередь URL у бота (другой срез):** `data-service` читает SQLite `Urls`: `/api/urls/stats` (всего / посещено / хосты), `/api/urls`, `/api/urls/hostnames`.

**`/api/steps/`** в Flask — выборка из **RQ** (недавние джобы типа `step`), не полная замена storage для «всех шагов за всё время».

## Связанные заметки

- [[Jamming Bot]] — концепция и карточка проекта
- [[Jamming bot microservices|Jamming Bot Microservices]] — кто за что отвечает
- [[jamming bot flask|Jamming Bot Flask]] — входная точка `/bot/step/`
- [[Jamming bot Redis Queue Jobs|Jamming Bot Redis Queue Jobs]] — RQ и Redis
- [[jamming bot api]] — карта HTTP-эндпоинтов
- [[Анализ проекта Jamming Bot]] — обзорный разбор проекта

## Указатели в репозитории

- `storage-service/app/main.py` — HTTP API storage
- `storage-service/app/api/db_manager.py` — запросы к БД, `STEP_FIELDS`, `get_latest`, `iter_all_steps`, `get_image_rows`
- `app-service/flask/app.py` — приём шага, `_patch_storage`, `_store_step_analysis`, `_poll_job_and_emit`
- `app-service/flask/jobs.py` — `dostep`, `do_geo`, `analyze`, `do_screenshot`, `image_analyze`
- `app-service/flask/tag_embeddings.py` — эмбеддинги тегов для визуализаций
- `bot-service/bot/bot.py` — класс `Step`, `to_data`, `do_step`
- `data-service/app/main.py` — статистика и списки URL очереди бота
- `steps-service/app/main.py` — снимки CSV/PNG для presence
