# Задание для Cursor: перенос логики accent-треугольников на production semantic3d

## Цель

Перенести на страницу **[https://jamming-bot.arthew0.online/semantic3d/](https://jamming-bot.arthew0.online/semantic3d/)** полную логику полупрозрачных белых треугольников между узлами 3D force-graph, как уже реализовано в локальном репозитории.

**Эталон (source of truth):** `semantic3d/semantic_demo_3d.js`, функция `createSemanticGraph3D`, блок `accent*` (примерно строки **668–1005** и точки интеграции **1048–1049**, **1213**, **1236**, **1247**).

**Не трогать:** `semantic3d_force_graph.iife.js` (вендор). Менять только код инициализации графа (аналог `semantic_demo_3d.js` на сервере).

---

## Контекст

| Что | Где |
|-----|-----|
| Локальная demo | `texts-wbgl/semantic3d/index.html` + `semantic_demo_3d.js` |
| Production URL | https://jamming-bot.arthew0.online/semantic3d/ |
| API origin (прокси локально) | `https://jamming-bot.arthew0.online` (`serve_with_proxy.py`) |
| Стек | `ForceGraph3D` (3d-force-graph), глобальный `THREE`, `graphData = { nodes, links }` |

На production, скорее всего, отдельный репозиторий/деплой **jamming-bot** (UI: Counter, Latency, Socket.IO). Нужно найти файл с `createSemanticGraph3D` / `ForceGraph3D()(containerEl)` и внести туда тот же блок, что в эталоне.

---

## Поведение (спецификация)

### 1. Визуал

- `THREE.Mesh` с `BufferGeometry` (один треугольник = 3 вершины).
- Материал: `MeshBasicMaterial`, цвет `#ffffff`, `transparent: true`, **`opacity: 0.04`** (`0.24 / 3 / 2`).
- `side: THREE.DoubleSide`, `depthWrite: false`, `renderOrder: 2`.
- Меши добавляются в сцену: `fg.scene().add(mesh)`.

### 2. Привязка к узлам

- В `mesh.userData.accentNodes` хранится массив из **трёх ссылок на объекты нод** (те же объекты, что в `graphData.nodes`).
- Каждый кадр в `fg.onEngineTick`: **`accentUpdateTriangles()`** копирует `node.x/y/z` в `position` атрибут геометрии, `needsUpdate = true`, `computeVertexNormals()`.
- Если у любой из трёх нод нет конечных координат — меш **dispose** и удаление из списков.

### 3. Статические треугольники (накопление)

| Параметр | Значение |
|----------|----------|
| `ACCENT_TRIANGLES_PER_SPAWN` | **9** |
| Интервал спавна | каждые **3–5** вызовов `addNode` (`accentRandomInt(3, 5)`) |
| Выбор вершин | `accentPickNearestTrio()`: случайный seed из пула → **2 ближайших** по `distSq` в 3D |
| Пул узлов | все `graphData.nodes` с позицией; если &lt; 3 — fallback `recentNodes` (кольцо **32**) |
| Дубликаты | не создавать, если та же тройка `id` уже есть (`accentTrioKey` + `accentHasTriangleTrio`) |

При срабатывании интервала: **`accentSpawnTriangleBatch()`** → 9× `accentMaybeAddTriangle()`.

### 4. Пара «блуждающих» треугольников

| Параметр | Значение |
|----------|----------|
| `ACCENT_WANDER_COUNT` | **2** |
| Цикл переназначения | **1–2 с** случайно: `1000 + Math.random() * 1000` мс |
| Выбор вершин при переназначении | `accentPickRandomTrio()` (3 случайные различные ноды из пула) |
| Флаг | `mesh.userData.accentWander = true`, список `accentWanderMeshes` |

В `onEngineTick` после `accentUpdateTriangles`: **`accentWanderStep(now)`** — создаёт пару при ≥3 нодах, по таймеру меняет `accentNodes` на новую случайную тройку.

### 5. Жизненный цикл / очистка

| Событие | Действие |
|---------|----------|
| `addNode` (в конце, после `pushGraph`) | `accentOnNodeAdded(node)` |
| `removeNode` | убрать ноду из `recentNodes`; **`accentRemoveTrianglesForNode(removed)`** |
| `removeAllNodes` | **`accentClearTriangles()`** (все меши + сброс wander-таймера) |

`accentDisposeMesh`: `scene.remove`, `geometry.dispose`, `material.dispose`, удаление из `accentTriangles` и `accentWanderMeshes`.

---

## Интеграция в `createSemanticGraph3D` (чеклист)

Внутри замыкания, **после** `var fg = ForceGraph3D()(containerEl)...` и **до** `return { ... }`:

1. [ ] Скопировать константы и переменные состояния (`recentNodes`, `accentTriangles`, `accentWanderMeshes`, счётчики).
2. [ ] Скопировать все функции `accent*` из эталона (один блок, префикс `accent` сохранить).
3. [ ] В существующий `fg.onEngineTick` добавить в начало тела (после расчёта `now`):
   ```javascript
   accentUpdateTriangles();
   accentWanderStep(now);
   ```
4. [ ] В `addNode` после `pushGraph()`:
   ```javascript
   accentOnNodeAdded(node);
   ```
5. [ ] В `removeNode` при удалении объекта ноды — `accentRemoveTrianglesForNode(removed)`.
6. [ ] В `removeAllNodes` в начале — `accentClearTriangles()`.

**Зависимости в замыкании:** `graphData`, `fg`, глобальный `THREE`. Других внешних API не нужно.

---

## Поиск кода на production

1. Открыть https://jamming-bot.arthew0.online/semantic3d/ → DevTools → Network → JS-файл с `ForceGraph3D` / `addNode` / `createSemanticGraph3D`.
2. В репозитории jamming-bot (или том, откуда деплой) найти тот же файл.
3. Сравнить с `texts-wbgl/semantic3d/semantic_demo_3d.js`: если на сервере старая версия без `accent*` — вставить блок из эталона.
4. Альтернатива: **скопировать целиком** актуальный `semantic_demo_3d.js` из `texts-wbgl/semantic3d/`, если production использует тот же модуль и отличается только оболочка HTML/Socket.IO.

---

## Деплой

После правок:

1. Собрать/залить статику на хост `jamming-bot.arthew0.online` (путь `/semantic3d/`).
2. Сбросить CDN/cache браузера (hard reload).
3. Проверить, что грузится обновлённый JS (поиск в файле строки `accentWanderStep` или `ACCENT_TRIANGLES_PER_SPAWN`).

Локальная проверка перед деплоем:

```bash
cd semantic3d
python serve_with_proxy.py
# http://127.0.0.1:<port>/ — визуально сравнить с production
```

---

## Критерии приёмки (QA)

На https://jamming-bot.arthew0.online/semantic3d/ после play / прихода рёбер с Socket.IO:

- [ ] Появляются **бледные белые плоскости** между узлами (не только сферы/рёбра).
- [ ] Плоскости **двигаются вместе** с узлами при симуляции.
- [ ] При росте графа накапливается много треугольников; примерно каждые 3–5 новых узлов — **пачка** новых (до 9, без дублей тройки id).
- [ ] Видны **2** треугольника, которые **раз в 1–2 с** «перепрыгивают» на другие случайные тройки узлов.
- [ ] **Reset / очистка графа** убирает все accent-меши, без утечек (повторный play без артефактов).
- [ ] Удаление узла снимает треугольники, в которых он участвовал.
- [ ] Нет ошибок в консоли (`THREE`, `fg.scene`, dispose).

---

## Подсказки для агента

- Не выносить в отдельный файл без запроса — достаточно блока внутри `createSemanticGraph3D`, как в эталоне.
- Имена с префиксом `accent` — чтобы не конфликтовать с остальным кодом страницы.
- Если на production `addNode` называется иначе или вызывается из другого места — повесить `accentOnNodeAdded` на **единственную** точку добавления ноды в `graphData.nodes`.
- Если `onEngineTick` уже есть — **дополнить**, не дублировать второй подписчик без необходимости.
- `refreshSpawnFromPartner` менять не обязательно: позиции подтянутся через `accentUpdateTriangles` после появления `x/y/z`.

---

## Ссылка на эталонный фрагмент

Файл: `semantic3d/semantic_demo_3d.js`

- Объявления и функции: ~668–1005  
- `onEngineTick`: ~1048–1049  
- `addNode`: ~1213  
- `removeNode`: ~1236  
- `removeAllNodes`: ~1247  

При расхождении номеров строк ориентироваться на поиск по `accentSpawnTriangleBatch` / `ACCENT_WANDER_COUNT`.
