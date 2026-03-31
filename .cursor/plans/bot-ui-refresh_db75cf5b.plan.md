---
name: bot-ui-refresh
overview: Подготовить поэтапный план апдейта дизайна главного интерфейса Jamming Bot с минимальным риском для текущей логики и без полного переписывания страницы. План сфокусирован на `bot.html` и `login.html`, с опорой на более современный стиль, уже использованный в `geo_globe.html`.
todos:
  - id: audit-header-structure
    content: "Зафиксировать новую структуру верхней панели `bot.html`: навигация, статусные метрики, admin actions."
    status: completed
  - id: align-visual-language
    content: Сформировать набор базовых UI-токенов и компонентов в стиле `path_map.html` для применения в `bot.html` и `login.html`.
    status: completed
  - id: stage-layout-refactor
    content: Спланировать поэтапную замену части absolute-positioned UI-обвязки на более устойчивый layout без риска сломать текущую визуализацию.
    status: completed
  - id: refresh-login-screen
    content: Подготовить обновлённую структуру и стиль `login.html`, согласованные с редизайном основного экрана.
    status: completed
isProject: false
---

# План редизайна Jamming Bot

## Цель

Сделать главный экран более читаемым и управляемым: отделить пользовательскую навигацию от служебных действий, собрать понятную визуальную иерархию и привести login-flow к единому стилю.

## Что менять

- Основная страница: [app-service/flask/templates/bot.html](app-service/flask/templates/bot.html)
- Экран логина: [app-service/flask/templates/login.html](app-service/flask/templates/login.html)
- Визуальный референс для стиля и токенов: [app-service/flask/templates/geo_globe.html](app-service/flask/templates/geo_globe.html)

## Наблюдения по текущему состоянию

- В [app-service/flask/templates/bot.html](app-service/flask/templates/bot.html) верхняя панель собрана как одна длинная строка в `#debug`, где перемешаны метрики, ссылки на визуализации, API и admin-controls.
- Основной layout держится на большом количестве `position: absolute`, из-за чего адаптивность строится через точечные media-query вместо устойчивой композиции.
- В [app-service/flask/templates/login.html](app-service/flask/templates/login.html) логин минималистичен, но стилистически не связан с более свежими экранами.
- В [app-service/flask/templates/path_map.html](app-service/flask/templates/path_map.html) уже есть более аккуратные surface-компоненты, border/token-подход и компактные toolbar-группы, которые можно переиспользовать.

## Предлагаемый подход

### Этап 1. Пересобрать верхнюю панель `bot.html`

- Заменить поток внутри `#debug` на 3 явные группы:
  - `primary navigation`: `tag cloud`, `3D cloud`, `geo globe`, `path map`, `react UI`
  - `system status`: `value`, `counter`, `latency`
  - `admin tools`: `step`, `stop`, `start`, `restart`, `queue`, `dashboard`, raw API links
- Убрать визуальные разделители `|` и заменить их spacing, pills и button/link groups.
- Для guest/admin состояний сохранить существующую логику `admin-only` / `guest-only`, но поменять контейнеры и подачу.

Ключевой текущий узел:

```619:658:app-service/flask/templates/bot.html
<div id="debug">
  <code>
      | value:<span id="value"></span>
      | counter:<span id="counter"></span>
      | latency:<span id="latency"></span>
      <a href="/screenshots/">screenshot</a>|
      ...
      <button onclick="start()">start</button>
      ...
      <a href="/queue/">queue:<span id="queue"></span></a>
```

### Этап 2. Ввести базовую дизайн-систему прямо в шаблоне

- Добавить CSS-переменные для `background`, `surface`, `border`, `text`, `muted`, `accent`.
- Разделить типографику: UI-текст и кнопки обычным sans/ui шрифтом, данные и counters через monospace.
- Нормализовать кнопки, ссылки, pills, hover/focus состояния.
- Взять за ориентир surface-стили из [app-service/flask/templates/geo_globe.html](app-service/flask/templates/geo_globe.html)

### Этап 3. Упростить композицию основного экрана

### Этап 5. Адаптивность и мобильная версия

- Сократить количество device-specific media queries в пользу 2-3 устойчивых breakpoint-режимов.
- На мобильном свернуть навигацию и admin tools в компактные группы или строки с переносом.
- Проверить, чтобы ключевые статусы и login были доступны без наложения на визуализацию.

## Риски

- `bot.html` смешивает стили, layout и JS-логику в одном файле, поэтому при переразметке легко задеть селекторы, на которые опирается существующий JS.
- Некоторые overlay-элементы (`#log_text`, `#log_words`, `#log_phrases` и т.д.) завязаны на конкретные размеры и позиции; их лучше переносить постепенно.
- Нельзя ломать текущую механику `admin-only` / `guest-only` и login overlay.

## Порядок внедрения

1. Сначала правки только в header/login и общих стилях.
2. Затем мягкая реструктуризация overlay-контейнеров без изменения бизнес-логики.
3. После этого адаптивная чистка и вынос secondary/admin элементов из первого экрана.

## Критерий готовности

- Первый экран читается как продуктовый dashboard, а не debug-поток.
- Пользователь сразу понимает, где навигация, где состояние системы, где управляющие действия.
- Логин и основная страница выглядят как части одной системы.
- Существующие кнопки, ссылки и admin-поведение продолжают работать без изменения backend/API.

