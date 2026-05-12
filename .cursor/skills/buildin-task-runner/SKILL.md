---
name: buildin-task-runner
description: Pick up a task from the Buildin.ai Tasks board at https://buildin.ai/9a2a7bd0-fc72-4c35-9721-9a5a7afbeebd (Category = "To Do") that has no progress/review marker yet. Append a checklist of subtasks plus a "progress" status line to the task body, tick subtasks one by one while implementing, open a PR with bidirectional links, then flip the trailing line to "review". Use when the user asks to take/grab/do/pull a task from buildin, that board URL, the board, or the todo list, or says "возьми задачу", "следующая задача", "что в todo", "сделай задачу из buildin", "работай подряд задачи".
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
- **Progress marker (новое):** в конце тела задачи Buildin живёт секция-маркер.
  Формат:
  ```
  ---

  Подзадачи (auto):

  - [ ] subtask 1
  - [ ] subtask 2

  progress
  ```
  - Последний параграф — литеральное слово **`progress`** или **`review`** на отдельной строке.
  - Список подзадач — markdown task list (`- [ ]` / `- [x]`), он же `to_do`-блоки в Buildin.
  - Маркер ставим **один раз при старте задачи**. Если он уже есть — задача занята и пропускается.

## Workflow

Скопируй чек-лист в ответ и обновляй по ходу.

```
- [ ] 1. Выбрать задачу из "To Do" без progress/review-маркера
- [ ] 2. Перевести в "In Progress" + создать ветку
- [ ] 3. Прочитать содержимое задачи
- [ ] 4. Записать в задачу подзадачи + маркер `progress`
- [ ] 5. Выполнить подзадачи последовательно (тикать `- [ ]` → `- [x]`)
- [ ] 6. Self-review и фиксы
- [ ] 7. Коммит со ссылкой на задачу
- [ ] 8. Push и создание PR со ссылкой на задачу
- [ ] 9. Дописать в задачу ссылки на коммит и PR, переключить маркер `progress` → `review`
- [ ] 10. Перевести задачу в "Review"
- [ ] 11. Отчёт пользователю
```

### 1. Выбрать задачу из "To Do" без progress/review-маркера

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

Дальше для **каждой** оставшейся строки `buildin_get_page_markdown` и применяй фильтр маркера:
- если в теле уже есть отдельная строка-параграф `progress` или `review` — **пропускай**, задача уже взята или в ревью;
- если тело пустое или непонятное — тоже пропускай (см. шаг 3).

Стратегия выбора:
- Если пользователь явно указал задачу — взять её даже с маркером (но не двигать чужой маркер — продолжать поверх, не сбрасывая чекбоксы; если уже `review` — спросить).
- Иначе — самую старую из отфильтрованного списка **без** маркера.
- Если после фильтрации пусто — сообщить «В колонке To Do нет задач без progress/review» и остановиться.

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

### 4. Записать в задачу подзадачи + маркер `progress`

Сформируй короткий список **подзадач** (`subtasks`) из тела задачи — это атомарные шаги реализации, обычно 2–6 пунктов. Каждый — императив («создать роут `/pages/url/`», «добавить websocket-клиент» и т.п.).

`buildin_append_markdown`:

```json
{
  "block_id": "<page_id>",
  "markdown": "\n---\n\nПодзадачи (auto):\n\n- [ ] <subtask 1>\n- [ ] <subtask 2>\n- [ ] <subtask 3>\n\nprogress\n"
}
```

В ответе придёт массив `results[]` с id созданных блоков. **Сохрани**:
- `todoBlockIds[]` — id всех созданных `to_do`-блоков (в порядке `subtasks`),
- `statusBlockId` — id последнего параграфа со словом `progress`.

Эти id нужны на шагах 5 и 9 (и в новой сессии — восстанавливай через `buildin_get_page_children` по тексту блоков).

### 5. Выполнить подзадачи последовательно

Для каждой подзадачи:
1. Реализуй её в коде минимальными правками.
2. Отметь `to_do`-блок как done:

   ```json
   {
     "block_id": "<todoBlockIds[i]>",
     "block": { "to_do": { "checked": true } }
   }
   ```

   (`buildin_update_block` — schema поддерживает `to_do.checked`.)

3. Только потом переходи к следующей.

Если по ходу всплыла новая подзадача — допиши её отдельным `buildin_append_markdown` **перед** маркером `progress` (через параметр `after` на предпоследний блок) или добавь как новую отметку в этом же batch перед коммитом.

### 6. Self-review и фиксы

- `ReadLints` по затронутым файлам — починить введённые проблемы.
- Запустить релевантные проверки проекта (тесты/линтеры), если применимо.
- Перечитать diff на типичные косяки (опечатки, ломаные импорты, забытые TODO).
- При красных проверках — фиксить, **не идти дальше**.

### 7. Коммит со ссылкой на задачу

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

### 8. Push и PR

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

### 9. Дописать ссылки и переключить `progress` → `review`

а) **Дотикать подзадачи**, которые ещё `- [ ]`, через `buildin_update_block` (`to_do.checked: true`). После шага 9 все `todoBlockIds[]` должны быть `checked`.

б) Дописать ссылки на коммит и PR **выше** маркера. Через `buildin_append_markdown` с `after = <предпоследний block_id>`:

```json
{
  "block_id": "<page_id>",
  "after": "<последний to_do block_id или параграф ВЫШЕ progress>",
  "markdown": "\n- PR: <PR_URL>\n- Commit: <COMMIT_URL>\n- Branch: `task/<slug>-<short_id>` · <YYYY-MM-DD HH:mm UTC>\n"
}
```

в) Переключить статус-параграф `progress` → `review` через `buildin_update_block`:

```json
{
  "block_id": "<statusBlockId>",
  "block": {
    "paragraph": {
      "rich_text": [{ "type": "text", "text": { "content": "review" } }]
    }
  }
}
```

Если `after` не сработает (или у тулзы нет такого параметра в текущей версии) — допустимо просто `append_markdown` ссылок в конце страницы, а маркер `progress`→`review` всё равно обновить. Главное — текст последнего status-параграфа должен стать `review`.

### 10. Перевести задачу в "Review"

`buildin_update_page`:

```json
{
  "page_id": "<page_id>",
  "properties": {
    "Category": { "select": { "name": "Review" } }
  }
}
```

### 11. Отчёт пользователю

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
- **Маркер `progress` / `review` обязателен.** Если он уже стоит — задача занята; не дублировать секцию и не сбрасывать чекбоксы чужого прогона. Брать только задачи **без** маркера, кроме случая явного указания пользователем.
- **Маркер всегда последняя строка** тела задачи в Buildin: один параграф из одного слова. Не оформлять его как заголовок или эмодзи — нужен литерал `progress` / `review` для надёжного поиска.
- **Шумный фильтр:** `buildin_query_database` подмешивает страницы без нужного значения `Category` — всегда фильтровать ответ на клиенте по `properties.Category.select.name`.
- **`Category` через MCP не применяется:** если после `buildin_update_page` повторный `buildin_get_page` всё ещё показывает старый `Category` (хотя `last_edited_time` мог обновиться), у токена интеграции Buildin, скорее всего, **нет права менять свойства строк базы** — только блоки (например `append_markdown`). Тогда колонку (`To Do` → `In Progress` → `Review`) нужно перенести **вручную в UI**. Формат запроса при рабочих правах (имя или UUID свойства `b32c8846-e56f-45da-b7bf-09e358024c10`): `"Category": { "select": { "name": "Review" } }` или с `"id"` опции из `buildin_get_database`.
- **URL задачи:** страница одна и та же для `https://buildin.ai/docs/<page_id>` и короткого `https://buildin.ai/<page_id>` — проблема «не переехала колонка» не из-за формата ссылки, а из-за прав API / ручного переноса.
- **GitHub CLI (`gh`):** при `HTTP 401` / `Bad credentials` выполни `gh auth status`. Если в окружении задан **невалидный `GITHUB_TOKEN`**, он перекрывает учётную запись из keyring — в PowerShell: `Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue`, затем снова `gh auth status`. Постоянно: убери битый токен из переменных среды пользователя / настроек Cursor. Интерактивное обновление: `gh auth login --web`.
- **Не переводить в `Review` с красными проверками.** Оставить в `In Progress` и сообщить блокер.
- **Не менять другие свойства** задачи кроме `Category`, если пользователь не попросил.
- **Запрещено** `archived: true` для страницы.
- **Trailer `Buildin-Task: <url>` обязателен** в коммите. Если коммит уже запушен без trailer — сделать follow-up коммит с пометкой `References Buildin-Task: <url>` в теле, и в `buildin_append_markdown` добавить оба коммита. `--amend` использовать только для незапушенного локального коммита.
- **PR создавать только из ветки `task/<slug>-<short_id>`**, никогда из `main`/`master`.
- **Никаких force-push в `main`/`master`** ни при каких условиях.
- **Двусторонние ссылки атомарны:** если PR создан, но `append_markdown` падает — повторить append; если не выходит после 1 ретрая, **не** переводить в `Review`, оставить в `In Progress` и сообщить пользователю.
- **MCP-ошибки** — максимум 1 повтор, потом стоп и отчёт.
- **Если ветка уже на удалёнке и расходится с локальной** — пауза и спросить пользователя, не делать `--force` автоматически.
