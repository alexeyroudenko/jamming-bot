# Jamming Bot — STYLE-GUIDE (control room design system)

Спецификация визуального языка и компонентов для служебных страниц Flask и согласованных экранов (login, steps-service). Исходники: [`app-service/flask/static/style.css`](../app-service/flask/static/style.css), шаблоны в [`app-service/flask/templates/`](../app-service/flask/templates/).

## Цели и охват

- **Единый тёмный UI** без Bootstrap/Bootswatch на админ-маршрутах.
- **Префикс `jb-`** (Jamming Bot) для всех публичных классов и **`--jb-*`** для токенов — избегаем коллизий с внешними библиотеками и со старым inline CSS [`bot.html`](../app-service/flask/templates/bot.html) (полная миграция `bot.html` не входит в этот этап).
- **Страницы на системе:** `/ctrl/`, `/queue/`, `/queue/job/<id>/`, [`login.html`](../app-service/flask/templates/login.html) (маршрут `/login`).
- **Steps-service:** подключает тот же [`style.css`](../app-service/flask/static/style.css) и маппит локальные `--steps-*` на `--jb-*` в [`steps-service/app/main.py`](../steps-service/app/main.py).

## Подключение

```html
<link rel="stylesheet" href="/flask_static/style.css">
```

Flask монтирует статику с префиксом `/flask_static/` (см. [`app-service/flask/app.py`](../app-service/flask/app.py), `static_url_path`).

> **Прокси:** steps-service и Flask должны отдавать `style.css` с одного origin (как в проде за reverse proxy). Если сервисы на разных хостах, задайте полный URL через конфигурацию и подставьте в `<link href="…">`.

## Токены (`:root`)

| Переменная | Назначение | Пример |
|------------|------------|--------|
| `--jb-color-bg-page` | Фон страницы | `#000000` |
| `--jb-color-surface` | Плотная панель (login) | `rgba(12, 12, 12, 0.96)` |
| `--jb-surface-glass` | Полупрозрачные бару | `rgba(9, 9, 11, 0.84)` |
| `--jb-surface-raised` | Карточки/тултипы | `rgba(9, 9, 11, 0.94)` |
| `--jb-color-border` | Границы | `rgba(161, 161, 170, 0.22)` |
| `--jb-color-border-strong` | Акцентные границы | `rgba(255, 255, 255, 0.18)` |
| `--jb-color-text` | Основной текст | `#f4f4f5` |
| `--jb-color-text-muted` | Вторичный текст | `#a1a1aa` |
| `--jb-color-accent` | Ссылки, primary control room | `#22d3ee` |
| `--jb-color-accent-faint` | Обводки focus/hover | `rgba(34, 211, 238, 0.22)` |
| `--jb-color-danger` | Ошибки, destructive | `#f87171` |
| `--jb-color-success` | Успех (finished) | `#4ade80` |
| `--jb-color-warning` | Предупреждения | `#fbbf24` |
| `--jb-color-info` | В процессе (started) | `#38bdf8` |
| `--jb-font-sans` | Основной шрифт | `Inter, ui-sans-serif, system-ui, …` |
| `--jb-font-mono` | Код / метрики | `ui-monospace, …` |
| `--jb-radius-sm`, `--jb-radius-md`, `--jb-radius-pill` | Радиусы | `4px`, `8px`, `999px` |
| `--jb-space-1` … `--jb-space-5` | Шаг сетки | `4px` … `24px` |
| `--jb-touch-min` | Минимальная зона нажатия | `44px` |
| `--jb-focus-ring` | Кольцо фокуса | двойная обводка |

**Login:** на `body.jb-login-page` акцент переопределяется на красный бренда (`--jb-color-accent: #ff0000`), плюс `--jb-color-border-strong-login` для фокуса полей.

## Типографика

- Базовый размер на control room: **15px**, межстрочный **~1.45**.
- Заголовки: `h1` в [`jb-main`](../app-service/flask/static/style.css) через `clamp`; `h2`/`h3` компактные.
- `code`, преформатированный текст: [`jb-code`](../app-service/flask/static/style.css), [`jb-code-block`](../app-service/flask/static/style.css).

## Семантика HTML

- Страница control room: [`base_control.html`](../app-service/flask/templates/base_control.html) — `header` + `main#main` с `tabindex="-1"` для приёма фокуса после skip-link.
- Навигация: [`components/nav_control.html`](../app-service/flask/templates/components/nav_control.html) — `nav` с `aria-label`, текущий маршрут: `aria-current="page"`.
- Таблицы: [`caption`](../app-service/flask/templates/queue.html) (можно скрыть через `jb-visually-hidden`), `scope="col"` / `scope="row"`.
- Статус счётчика/latency: [`status_strip.html`](../app-service/flask/templates/components/status_strip.html) — `role="status"` и `aria-live="polite"`.

## Компоненты

### Skip link

- **Класс:** `jb-skip-link`
- **Поведение:** скрыт до фокуса клавиатуры; ведёт к `#jb-main` или к форме логина.

### Layout

| Класс | Роль |
|-------|------|
| `jb-page` | Тело служебных страниц Flask |
| `jb-header` | Верхняя полоса: нав + статус |
| `jb-main` | Основной контент, ограничение ширины |
| `jb-stack`, `jb-toolbar` | Вертикальный/горизонтальный стек |

### Навигация

- **Блок:** `jb-nav-bar` — flex-обёртка.
- **Список:** `jb-nav` — без маркеров, переносится на узком экране.
- **Бренд:** `jb-nav__brand`
- **Активная ссылка:** `aria-current="page"` (задаётся из шаблона через `nav_active`).

Переменная шаблона: `nav_active` ∈ `home`, `steps`, `path`, `ctrl`, `queue` (строка сравнивается в Jinja).

### Статус (counter / latency)

- Разметка: [`status_strip.html`](../app-service/flask/templates/components/status_strip.html)
- Обновление: только Socket.IO + `textContent` (без jQuery).

### Кнопки и ссылки-кнопки

| Класс | Использование |
|-------|----------------|
| `jb-btn` | База |
| `jb-btn--primary` | Основное действие (cyan; на login — красная тема) |
| `jb-btn--danger` | Удаление, clear failed |
| `jb-btn--warning` | Clear all |
| `jb-btn--ghost` | Вторичные действия |
| `jb-btn--sm` | Компактная высота |

Для GET-действий допускается `<a class="jb-btn" href="…">` (как на control).

**a11y:** видимый `:focus-visible` через `--jb-focus-ring`; минимальная высота клика — `--jb-touch-min`.

### Панели

- `jb-panel`, `jb-panel__header`, `jb-panel__body`
- `jb-panel__header--danger` — блок исключений на странице job.

### Алерты

- `jb-alert`, модификаторы `jb-alert--danger`, `jb-alert--warning`
- `role="alert"` на критичных сообщениях.

### Бейджи состояния job

Макрос: [`macros/jb.html`](../app-service/flask/templates/macros/jb.html) — `job_badge(state)`.

| Модификатор | Состояние |
|-------------|-----------|
| `jb-badge--finished` | finished |
| `jb-badge--started` | started |
| `jb-badge--failed` | failed |
| `jb-badge--queued` | queued |
| `jb-badge--neutral` | тип job и пр. |

### Таблица

- Обёртка: `jb-table-scroll` — горизонтальный скролл на мобильных.
- Таблица: `jb-table`; ключ-значение: `jb-table--kv`.

### Прогресс

- `jb-progress`, внутри `jb-progress__bar` с inline `width: …%`
- На разметке очереди: `role="progressbar"` и `aria-valuenow` / `min` / `max`.

### Формы (control)

- Группы: `jb-fieldset` + `legend`
- Чекбоксы: список `jb-check-grid`, элемент `jb-check`
- Слайдеры: `jb-range-row`, `jb-range`
- Текст: `jb-input-text`

## Доступность (чеклист)

- [ ] У интерактивных элементов виден фокус (`:focus-visible`).
- [ ] Skip link есть на каждой полноэкранной форме/странице control room.
- [ ] У таблиц есть смысловой `caption` (можно скрыть визуально).
- [ ] Динамический счётчик/latency не ломает озвучивание чрезмерно (`aria-atomic="true"` осознанно).
- [ ] Подтверждение на деструктивных ссылках: `onclick="return confirm('…')"` (позже можно заменить на модальный диалог).
- [ ] `prefers-reduced-motion` уменьшает анимации глобально в [`style.css`](../app-service/flask/static/style.css).

## Адаптивность

- Шапка и `jb-nav` переносятся (`flex-wrap`), отступы через `--jb-space-*`.
- Таблица очереди: горизонтальный скролл, `min-width` у таблицы — контент не сжимается до нечитаемого вида.
- Login: одна колонка ниже **860px** (`jb-login-shell`).

## Jinja: переиспользование

- База: `{% extends "base_control.html" %}`
- Затем: `{% set nav_active = 'ctrl' %}` (или `queue`, и т.д.)
- Блоки: `title`, `head_extra`, `content`, `scripts`

## Миграция и кэш

- Bootstrap CDN удалён с `ctrl` / `queue` / `queue_job`.
- `meta refresh` на ctrl/queue снят (обновление через сокеты и ручная навигация).
- При агрессивном кэшировании прокси можно версионировать URL: `/flask_static/style.css?v=2`.

## Changelog (кратко)

- Введён единый [`style.css`](../app-service/flask/static/style.css), компоненты `jb-*`, документ STYLE-GUIDE.
- Steps-service: `<link>` на общий CSS и алиасы `--steps-*` → `--jb-*`.
