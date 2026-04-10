---
title: Sentiment vortex
note_type: web_entry
web_type: page
project: "[[jamming-bot/Jamming Bot]]"
parent: "[[pages/_index|Jamming Bot Pages Index]]"
url: https://jamming-bot.arthew0.online/tags/sentiment-vortex/
updated: 2026-04-08
tags:
  - web
  - page
  - sentiment
  - jamming-bot
---

# Sentiment vortex

## URL

https://jamming-bot.arthew0.online/tags/sentiment-vortex/

## Описание

Здесь акцент смещён с фактов и сущностей на эмоциональную динамику потока данных. Воронка настроений показывает, как бот пытается осмыслить хаос не только через структуру, но и через аффект, превращая анализ тональности в художественное переживание.

## Как это работает (технически)

Страница `GET /tags/sentiment-vortex/` отдаёт HTML-шаблон с клиентским Three.js: частицы — это **фразы**, полученные из текущих тегов; их **полярность** и **субъективность** считаются на бэкенде через **VADER** (`compound` и прокси субъективности). Данные подгружаются с `GET /api/tags/sentiment-vortex/` (тело не используется; `POST` эквивалентен для удобства). Подробнее по HTTP — [[jamming bot api|Jamming Bot API]].

### Цепочка на сервере (app-service)

1. **Теги** — `GET` в tags-service `.../tags/tags/group/`, сортировка по `count`, извлечение имён тегов.
2. **Фразы** — `POST` в semantic-service `.../semantic/combine/` с `words`, `limit: 128`, `max_phrases: 256`.
3. **Тональность** — `POST` в `.../semantic/sentiment-phrases/` со списком фраз, `limit: 256`. Сервис для каждой фразы возвращает `polarity` = VADER `compound`, `subjectivity` = `1 - neu` (чем выше нейтральная доля VADER, тем ниже «субъективность» в визуализации).

Ответ API: `phrases` — массив `{ text, polarity, subjectivity }`, плюс `stats` — `mean_polarity`, `pct_positive` / `pct_negative` / `pct_neutral` (пороги ±0.05 для compound), `count`. При ошибке tags/combine/sentiment возвращается 502 и пустой набор с полем `error`.

### Визуализация в браузере

- До **360** частиц; шейдерные **Points** с мягким кругом; опциональный полупрозрачный **trail**-слой.
- Каждая частица в **полярных координатах** (`θ`, `r`, `z`): **compound** задаёт радиальный **drift** (положительная тональность — наружу, отрицательная — внутрь); при очень нейтральной полярности (`|p| < 0.06`) drift заменяется на слабый синусоидальный шум.
- **Субъективность** усиливает случайный шум по `r` и `z` — «дрожание» нейтрально-оценочных фраз сильнее.
- **Цвет** — градиент от холодного/приглушённого к тёплому по полярности; **размер** точки зависит от `|polarity|` и `subjectivity`.
- Вращение: угловая скорость масштабируется полярностью; глобальный **kick** по Socket.IO и резкий сдвиг средней полярности дают кратковременный **glitch** (случайный сдвиг позиций).

### UI и обновления

- Панель: **Show text** (CSS2D-подписи фраз), **Auto camera** (OrbitControls отключаются, камера ездит по спирали), **Freeze** / **Export PNG** через общий `tags_vis_controls.js`.
- Подсказка внизу страницы: *VADER compound → radial drift · neutral fraction → subjectivity noise · refresh on tags_updated*.
- **Перезагрузка данных**: при событиях Socket.IO `analyzed` и `tags_updated`, плюс интервал **60 с**; при приходе данных обновляется строка статуса (`n`, `μ_pol`, доли +/−/0).

> [!note]
> Код страницы и симуляции: `app-service/flask/templates/tags_sentiment_vortex.html`. Прокси и оркестрация API: `app-service/flask/app.py` (`tags_sentiment_vortex`, `sentiment_vortex_api`). Разбор VADER: `semantic-service/app/api/semantic.py` (`sentiment-phrases`).
