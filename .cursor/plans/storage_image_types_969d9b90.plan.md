---
name: storage image types
overview: Добавить поддержку `type` в цепочку `/steps/ -> /api/storage_img/ -> /export/img`, чтобы сервер мог рендерить разные PNG-режимы на основе полей step из storage. Сохранить совместимость с текущим режимом presence и нормализовать пользовательские названия типов.
todos:
  - id: storage-render-types
    content: Спроектировать и реализовать type-aware рендер PNG в storage-service на основе step-полей и alias-нормализации
    status: completed
  - id: app-proxy-type
    content: Расширить app-service proxy `/api/storage_img/` пробросом и, при необходимости, нормализацией `type`
    status: completed
  - id: steps-type-propagation
    content: Связать `/steps/?type=...` с серверным запросом картинки и переделать кэширование PNG на per-type
    status: completed
  - id: path-map-query-sync
    content: Добавить чтение и синхронизацию query param `type` на `/path/map/`
    status: completed
  - id: verify-type-modes
    content: Проверить все режимы и alias'ы локально и на публичных маршрутах после реализации
    status: completed
isProject: false
---

# План поддержки `type` в `/api/storage_img/`

## Что уже есть

- В `[app-service/flask/app.py](app-service/flask/app.py)` route `/api/storage_img/` сейчас проксирует только `width` в `storage-service /export/img`.
- В `[storage-service/app/main.py](storage-service/app/main.py)` `GET /export/img` строит только grayscale PNG присутствия по `steps.number`.
- В `[steps-service/app/main.py](steps-service/app/main.py)` страница `/steps/` уже знает UI-типы `status_code`, `text_length`, `timestamp_delta`, `screenshot`, но `type` пока не влияет на серверный PNG.
- В `[app-service/flask/templates/path_map.html](app-service/flask/templates/path_map.html)` у `/path/map/` уже есть режимы `status`, `text-length`, `screenshot`, `delta-time`, но они не синхронизированы с query param `type`.

## Предлагаемый подход

- Считать каноничными API-значениями: `status_code`, `text_length`, `timestamp_delta`, `screenshot`.
- Поддержать alias'ы из пользовательского формата: `text length`, `delta time`, `screenshots`.
- Оставить текущее поведение `/export/img` по умолчанию, если `type` не передан или неизвестен: presence-map.
- Перенести вычисление цветового/тонового значения пикселя в `storage-service`, потому что именно там есть доступ к полям step.

## Изменения по слоям

### 1. `storage-service`

Файлы:

- `[storage-service/app/main.py](storage-service/app/main.py)`
- `[storage-service/app/api/db_manager.py](storage-service/app/api/db_manager.py)`

Что добавить:

- Расширить `GET /export/img` параметром `type`.
- Добавить выборку данных не только по `number`, но и по полям, нужным для рендера: `status_code`, `text_length`, `timestamp`, `screenshot_url`.
- Добавить нормализацию типа и серверный рендер значений:
  - `status_code`: интенсивность по HTTP-коду.
  - `text_length`: интенсивность по длине текста.
  - `timestamp_delta`: интенсивность по разнице timestamp между соседними шагами после сортировки по `number`.
  - `screenshot`: бинарная маска наличия `screenshot_url`.
- Сохранить существующую геометрию карты: координаты пикселя по `step.number`, параметр `width`, PNG-формат ответа.

Ключевая неочевидная деталь:

```195:205:storage-service/app/main.py
@app.get("/export/img")
async def export_img(width: int = 0):
    payload = await db_manager.get_ids()
    step_ids = payload.get("data", [])
    ...
    rows = _rasterize_presence(step_ids, img_width, img_height)
```

Сейчас endpoint работает только от списка id; для `type` его нужно перевести на рендер по данным step.

### 2. `app-service`

Файл:

- `[app-service/flask/app.py](app-service/flask/app.py)`

Что изменить:

- В proxy `/api/storage_img/` начать пробрасывать `type` вместе с `width`.
- При желании добавить мягкую нормализацию alias'ов на этом слое, но источник истины лучше держать в `storage-service`.

Ключевой участок:

```1515:1527:app-service/flask/app.py
@app.route("/api/storage_img/", methods=["GET"])
def api_storage_img():
    params = {}
    width = request.args.get("width", "").strip()
    if width:
        params["width"] = width
    resp = requests.get(f"{STORAGE_SERVICE_URL}/export/img", params=params, timeout=30)
```

### 3. `steps-service`

Файл:

- `[steps-service/app/main.py](steps-service/app/main.py)`

Что изменить:

- Привязать `type` из `/steps/?type=...` к URL картинки, а не только к UI overlay.
- Сделать загрузку и кэш PNG зависящей от `type`, иначе сейчас весь процесс держит одну общую `presence_raw.png`.
- Нормализовать старые/новые имена типа в одном месте, чтобы фронт не расходился с API.

Ключевая проблема текущей схемы:

```701:708:steps-service/app/main.py
async def refresh_presence() -> None:
    png_bytes, csv_rows = await asyncio.gather(
        asyncio.to_thread(fetch_bytes, DEFAULT_IMAGE_URL),
        asyncio.to_thread(fetch_csv_rows, DEFAULT_STEPS_CSV_URL),
    )
```

Сейчас fetch идёт в один фиксированный `DEFAULT_IMAGE_URL`, без `type`, поэтому `/steps/?type=timestamp_delta` не меняет серверную картинку.

### 4. `/path/map/`

Файл:

- `[app-service/flask/templates/path_map.html](app-service/flask/templates/path_map.html)`

Что изменить:

- Считать `type` из query string и замапить его на существующие display modes страницы (`status`, `text-length`, `delta-time`, `screenshot`).
- Синхронизировать URL при смене режима, чтобы пример вида `/path/map/?type=timestamp_delta` работал консистентно.
- Это отдельная UI-совместимость: страница сейчас не использует `/api/storage_img/`, но должна понимать те же значения `type`.

## Риски

- `timestamp_delta` не хранится отдельным полем, его нужно считать производно по отсортированным шагам; важно определить поведение для первого шага и пропусков.
- Для `text_length` и `status_code` нужно выбрать простую и стабильную шкалу интенсивности, иначе картинка будет трудно читаемой.
- В `steps-service` глобальный кэш PNG сейчас одноэкземплярный; при поддержке `type` потребуется либо per-type snapshot, либо проксирование картинки без этого кэша.

## Проверка после реализации

- Локально проверить ответы:
  - `/api/storage_img/?type=status_code`
  - `/api/storage_img/?type=text_length`
  - `/api/storage_img/?type=timestamp_delta`
  - `/api/storage_img/?type=screenshot`
- Проверить alias'ы:
  - `type=text length`
  - `type=delta time`
  - `type=screenshots`
- Проверить, что `/steps/?type=timestamp_delta` реально запрашивает соответствующий PNG.
- Проверить, что `/path/map/?type=timestamp_delta` выставляет правильный режим UI.

## Рекомендуемый порядок

1. Сначала реализовать `type` в `storage-service` и proxy в `app-service`.
2. Затем обновить `steps-service`, чтобы query param реально влиял на image URL и кэш.
3. Отдельно довести совместимость `/path/map/` с query param `type`.
4. В конце добавить короткую документацию по допустимым значениям `type`.

