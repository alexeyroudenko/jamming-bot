---
name: buildin-task-runner
description: Pick up a task from the Buildin.ai Tasks board at https://buildin.ai/9a2a7bd0-fc72-4c35-9721-9a5a7afbeebd (Category = "To Do"), move it to "In Progress", implement and verify it, open a PR with bidirectional links between the task and the commit/PR, then move the task to "Review". Use when the user asks to take/grab/do/pull a task from buildin, that board URL, the board, or the todo list, or says "возьми задачу", "следующая задача", "что в todo", "сделай задачу из buildin".
---

# Buildin Task Runner

Прогон одной задачи из Buildin.ai database `Tasks` через `To Do` → `In Progress` → `Review` с открытием PR и двусторонними ссылками между коммитом/PR и задачей.

**Источник задач (канон):** [Buildin — Tasks](https://buildin.ai/9a2a7bd0-fc72-4c35-9721-9a5a7afbeebd). Все `buildin_query_database` / выбор карточек — только по `database_id` этой доски, не по другим workspace-URL или hash-фрагментам в ссылке.

## Constants (verified)

- **MCP server**: `user-buildin` (use with `CallMcpTool`).
- **Database id** (совпадает с id страницы в canonical board URL): `9a2a7bd0-fc72-4c35-9721-9a5a7afbeebd` (название — "Tasks").
- **Board url (задачи брать отсюда)**: https://buildin.ai/9a2a7bd0-fc72-4c35-9721-9a5a7afbeebd
- **Status property**: `Category` (тип `select`).
- **Опции Category**:
  - `To Do` — стартовая колонка
  - `In Progress` — берём в работу
  - `Review` — отдаём на ревью
  - `Checked`, `Freezed` — не трогать в этом скилле
- **Default base branch**: `main`.
- **Commit trailer key**: `Buildin-Task` (значение — URL задачи).
- **Branch naming**: `task/<slug>-<short_id>`, где `<short_id>` — первые 8 символов `page_id` без дефисов.

## Workflow

Скопируй чек-лист в ответ и обновляй по ходу.

```
- [ ] 1. Выбрать задачу из "To Do"
- [ ] 2. Перевести в "In Progress" + создать ветку
- [ ] 3. Прочитать содержимое задачи
- [ ] 4. Выполнить задачу
- [ ] 5. Self-review и фиксы
- [ ] 6. Коммит со ссылкой на задачу
- [ ] 7. Push и создание PR со ссылкой на задачу
- [ ] 8. Дописать в задачу ссылки на коммит и PR
- [ ] 9. Перевести задачу в "Review"
- [ ] 10. Отчёт пользователю
```

### 1. Выбрать задачу из "To Do"

Доска: [https://buildin.ai/9a2a7bd0-fc72-4c35-9721-9a5a7afbeebd](https://buildin.ai/9a2a7bd0-fc72-4c35-9721-9a5a7afbeebd) — `database_id` ниже = эта доска.

Вызови `buildin_query_database`:

```json
{
  "database_id": "9a2a7bd0-fc72-4c35-9721-9a5a7afbeebd",
  "filter": { "property": "Category", "select": { "equals": "To Do" } },
  "sorts": [{ "timestamp": "created_time", "direction": "ascending" }],
  "page_size": 50
}
```

**Важно**: API возвращает шумные результаты — обязательно отфильтруй на клиенте, оставив только страницы, у которых `properties.Category.select.name === "To Do"`. Игнорируй страницы без `Category` или с другим значением.

Стратегия выбора:
- Если пользователь явно указал задачу (по названию/id/ссылке) — взять её.
- Иначе — самую старую из отфильтрованного списка.
- Если после фильтрации пусто — сообщить «В колонке To Do нет задач» и остановиться.

Запомни: `page_id`, `title` (`properties.title.title[0].plain_text`), `task_url` (`url` из ответа).

### 2. Перевести в "In Progress" + создать ветку

`buildin_update_page`:

```json
{
  "page_id": "<page_id>",
  "properties": {
    "Category": { "select": { "name": "In Progress" } }
  }
}
```

Затем создать ветку:

```bash
git fetch origin
git switch -c task/<slug>-<short_id> origin/main
```

`<slug>` — kebab-case транслитом из `title` (или просто латинская часть, если есть), обрезать до 30 символов. `<short_id>` — `page_id.replace(/-/g, '').slice(0, 8)`.

Если ветка уже существует — `git switch task/<slug>-<short_id>` без `-c`.

Сообщить пользователю одной строкой: «Беру: <title> (<task_url>). Статус → In Progress. Ветка: `task/<slug>-<short_id>`».

### 3. Прочитать содержимое задачи

- `buildin_get_page` — properties (Start/End Time, Parent item, Agent).
- `buildin_get_page_markdown` — тело задачи.

Если описание пустое или непонятное — пауза и вопрос пользователю. **Не угадывать.**

### 4. Выполнить задачу

- Соблюдать always_applied_workspace_rules проекта (`obsidian-core`, `writing-style`, `no-docker-compose-on-server`).
- Минимальные сфокусированные изменения по сути задачи.
- При двусмысленности или расширении скоупа — пауза и уточнение.
- Если задача затрагивает спеки — рассмотреть `openspec-propose` / `openspec-apply-change`.

### 5. Self-review и фиксы

- `ReadLints` по затронутым файлам — починить введённые проблемы.
- Запустить релевантные проверки проекта (тесты/линтеры), если применимо.
- Перечитать diff на типичные косяки (опечатки, ломаные импорты, забытые TODO).
- При красных проверках — фиксить, **не идти дальше**.

### 6. Коммит со ссылкой на задачу

Сообщение: Conventional Commits, заголовок ≤72 символов, далее тело и trailer.

```bash
git add <files>
git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>

<краткое тело: что и зачем>

Buildin-Task: <task_url>
EOF
)"
```

Получить идентификаторы:

```bash
COMMIT_SHA=$(git rev-parse HEAD)
REMOTE_URL=$(gh repo view --json url -q .url)
COMMIT_URL="$REMOTE_URL/commit/$COMMIT_SHA"
```

### 7. Push и PR

```bash
git push -u origin HEAD
```

Создать PR:

```bash
gh pr create --base main --title "<type>(<scope>): <subject>" --body "$(cat <<'EOF'
Задача: <task_url>

## Что сделано
- <bullet 1>
- <bullet 2>

## Как проверить
- <шаг 1>

## Риски / на что смотреть
- <bullet>
EOF
)"
```

```bash
PR_URL=$(gh pr view --json url -q .url)
```

Если PR на эту ветку уже существует — переиспользовать его URL и при необходимости обновить body через `gh pr edit --body`.

### 8. Дописать в задачу ссылки на коммит и PR

`buildin_append_markdown`:

```json
{
  "page_id": "<page_id>",
  "markdown": "\n---\n\n**→ Review** · <YYYY-MM-DD HH:mm UTC>\n\n- PR: <PR_URL>\n- Commit: <COMMIT_URL>\n- Branch: `task/<slug>-<short_id>`\n"
}
```

Время — UTC. Если коммитов несколько — перечислить все.

### 9. Перевести задачу в "Review"

`buildin_update_page`:

```json
{
  "page_id": "<page_id>",
  "properties": {
    "Category": { "select": { "name": "Review" } }
  }
}
```

### 10. Отчёт пользователю

```
## Готово к ревью: <title>

**Статус:** To Do → In Progress → Review
**Задача:** <task_url>
**PR:** <PR_URL>
**Commit:** <COMMIT_URL>
**Ветка:** task/<slug>-<short_id>

### Что сделано
- <bullet>

### Затронуто файлов
- `path/to/file`

### Проверки
- Линтер: ok / список фиксов
- Тесты: ok / не запускались (причина)

### На что обратить внимание ревьюеру
- <риск/допущение>
```

## Guardrails

- **Один прогон — одна задача.** Не забирать несколько из `To Do` за раз.
- **Шумный фильтр:** `buildin_query_database` подмешивает страницы без нужного значения `Category` — всегда фильтровать ответ на клиенте по `properties.Category.select.name`.
- **Не переводить в `Review` с красными проверками.** Оставить в `In Progress` и сообщить блокер.
- **Не менять другие свойства** задачи кроме `Category`, если пользователь не попросил.
- **Запрещено** `archived: true` для страницы.
- **Trailer `Buildin-Task: <url>` обязателен** в коммите. Если коммит уже запушен без trailer — сделать follow-up коммит с пометкой `References Buildin-Task: <url>` в теле, и в `buildin_append_markdown` добавить оба коммита. `--amend` использовать только для незапушенного локального коммита.
- **PR создавать только из ветки `task/<slug>-<short_id>`**, никогда из `main`/`master`.
- **Никаких force-push в `main`/`master`** ни при каких условиях.
- **Двусторонние ссылки атомарны:** если PR создан, но `append_markdown` падает — повторить append; если не выходит после 1 ретрая, **не** переводить в `Review`, оставить в `In Progress` и сообщить пользователю.
- **MCP-ошибки** — максимум 1 повтор, потом стоп и отчёт.
- **Если ветка уже на удалёнке и расходится с локальной** — пауза и спросить пользователя, не делать `--force` автоматически.
