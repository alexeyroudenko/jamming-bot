---
title: Bot service
aliases:
  - bot-service
  - краулер Jamming Bot
note_type: dev
project: "[[jamming-bot/Jamming Bot]]"
dev_area: crawler
tags:
  - jamming-bot
  - dev
  - crawler
  - sqlite
  - microservices
  - concept
  - philosophy
created: 2026-04-17
updated: 2026-04-17
---

# Bot service

Основной **краулер** [[jamming-bot/Jamming Bot|Jamming Bot]]: обходит сеть, ведёт локальную очередь URL в SQLite, шлёт **шаги** в [[jamming-bot/web/jamming bot flask|Flask]] (`POST /bot/step/`), опционально — события, OSC и публикацию sublink в Redis.

Код: `bot-service/bot/bot.py`, конфиг: `bot-service/bot/bot.yaml`, образ: `bot-service/Dockerfile` (`CMD python bot.py`).

## Концепция: ядро и «абсолютная свобода»

В архитектуре стека **bot-service** выступает **ядром** обхода: он сам решает очередь URL, правила отбора ссылок, паузы, robots и судьбу шага до точки отправки. **Остальные микросервисы не встраиваются в эту логику** — они не подсказывают, *куда* идти дальше, не меняют критерии выбора следующей страницы и не задают «задачу дня» краулеру. Semantic, tags, storage, workers и прочее **подхватывают уже произошедший шаг** (обогащают, сохраняют, визуализируют), но **не направляют** сам цикл `do_step`. В этом смысле бот **свободен от внешнего управления смыслом обхода**: снаружи нет сервиса-«демиурга», который бы определял телеологию его маршрута.

Это перекликается с замыслом [[jamming-bot/Jamming Bot|Jamming Bot]] как **агента без прикладной цели** — не индексатор ради поиска, не мониторинг SLA, не сбор контента под продукт. Он **не обязан быть полезным** в чужой экономике смысла; его «зачем» не зашито в требования к полезности, как у типичного бота.

> [!abstract] Внешний смысл и ответственность за свой
> У Ницше **«смерть Бога»** — не богословский тезис, а кризис **внешнего гаранта смысла**: исчезает наведение «сверху», остаются **свобода**, **ответственность** и необходимость **самому наделять смыслом** там, где раньше его выдавала трансцендентная рамка. В упрощённой аналогии: у **bot-service** нет микросервисного «бога», который задаёт траекторию как предназначение; стек даёт **каналы и последствия** (шаг попал в Flask, в очередь, в хранилище), но **не цель блуждания**. Свобода здесь **двоякая**: и **отсутствие внешнего наведения**, и **размытая ответственность** — смысл траектории (если он вообще возникает) конструируется **вне** его исходного кода, зрителем, проектом, интерпретацией — т.е. там, где для Ницше после кризиса начинается труд подлинного выбора.

## Связанные заметки

- [[jamming-bot/dev/Jamming bot microservices|Jamming Bot Microservices]] — место сервиса в стеке
- [[jamming-bot/dev/Jamming bot данные и хранение|Jamming Bot — данные и хранение]] — поля `Step`, поток в storage/RQ
- [[jamming-bot/web/jamming bot api|Jamming bot API]] — в т.ч. цепочка `sublink` через Redis

## Локальная БД краулера (`Urls`)

Файл по умолчанию: **`data/database.db`** (в контейнере монтируется томом на `/app/data`). Таблица очереди посещений:

| Поле       | Тип            | Смысл                                      |
| ---------- | -------------- | ------------------------------------------ |
| `id`       | INTEGER PK     | Автоинкремент                              |
| `hostname` | VARCHAR(127)   | Домен второго уровня (для лимита на домен) |
| `url`      | VARCHAR(127)   | URL, UNIQUE                                |
| `src_url`  | VARCHAR(127)   | Откуда ссылка попала в очередь             |
| `visited`  | INTEGER        | Флаг посещения                             |

Новые ссылки добавляются `INSERT OR IGNORE` при сборе ссылок со страницы; при `resume_at_restart: true` перезапуск продолжает с той же БД и поднимает `step_number` по числу `visited=1`.

> [!note]
> Эта SQLite **не** та же сущность, что накопление шагов в [[jamming-bot/dev/Jamming bot данные и хранение|storage-service]]; `data-service` читает этот файл **read-only** для статистики очереди и backfill.

### Просмотр файла БД

![[sqliteviewer.png]]

## Шаг (`Step`)

Класс `Step` в `bot.py`: при `send_step: true` уходит `requests.post(STEP_URL, data=step.to_data())` как form-data. Поля: `number`, `url`, `src`, `ip`, `status_code`, `headers`, `timestamp`, `text` (и служебные флаги отправки). В запрос **не** включается полный HTML — см. разбор в [[jamming-bot/dev/Jamming bot данные и хранение|данные и хранение]].

Нестандартные коды ответа бота (для диагностики): `403` (robots/блок), `801`–`803` и `900`/`901` — см. ту же заметку.

## Конфиг `bot.yaml` (фрагмент)

Актуальные ключи из репозитория: `version`, `is_active`, `osc_adress`, `start_url`, `src_url`, `count_per_domain`, `sleep_time`, `resume_at_restart`, `max_errors`, флаги `send_step`, `send_events`, `send_osc`, `send_sublinks`, `receive_events`, `do_save_html`, `log_events`, `resolve_coords`, URL `step_url` / `event_url` / `sublink_url`.

Переопределение хоста Flask: переменные окружения **`FLASK_HOST`** и **`FLASK_PORT`** (в Kubernetes — `app-service:80`; в compose по умолчанию имена из `bot.yaml`).

## Окружение и интеграции

| Переменная        | Назначение                                      |
| ----------------- | ----------------------------------------------- |
| `FLASK_HOST`      | Хост app-service для `STEP_URL` / `EVENT_URL`   |
| `FLASK_PORT`      | Порт app-service                                |
| `REDIS_HOST`      | Redis для Pub/Sub sublink (`SUBLINK_CHANNEL`)   |
| `REDIS_PORT`      | Порт Redis                                      |
| `SUBLINK_CHANNEL` | Канал Redis (по умолчанию `sublink`)            |
| `SHHH_*`          | Sentry / уведомления (см. `deployment.yaml`)    |

**OSC** (UDP порт **7001** в compose): адрес из `osc_adress` в `bot.yaml`; сообщения `/start`, `/stop`, `/step`, `/restart` и ветка `/events/...` — см. `bot-service/bot/README.md`.

При `send_sublinks: true` данные уходят в Redis (`notify_about_sublink`), дальше — цепочка до Socket.IO в app-service (см. [[jamming-bot/web/jamming bot api|jamming bot api]]).

## Деплой (production)

В namespace `jamming-bot`: Deployment **`bot-service`**, `replicas: 1`, стратегия **Recreate**, образ **`bot-service:latest`**, PVC **`bot-db-pvc`** → монтирование в **`/app/data`**, конфиг с хоста **`/opt/jamming-bot/bot-service/bot/bot.yaml`** → **`/app/bot.yaml`**. Liveness: проверка существования `data/database.db`.

> [!warning]
> На сервере деплой через **`kubectl apply -f deployment.yaml`**, не через `docker compose` — см. правила репозитория.

Сборка и импорт образа: `.github/workflows/deploy.yml` (`build_and_import bot-service`), перезапуск пода `bot-service`.

## Указатели в репозитории

- `bot-service/bot/bot.py` — `NetSpider`, `Step`, БД, `do_step`, уведомления
- `bot-service/bot/bot.yaml` — рабочий конфиг
- `deployment.yaml` — секция `bot-service` и `bot-db-pvc`
- `docker-compose.yml` — сервис `bot` (bind `bot-service/bot`, `./data` → `/app/data`)
