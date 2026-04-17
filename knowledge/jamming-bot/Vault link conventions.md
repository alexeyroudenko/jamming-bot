---
title: Vault link conventions
aliases:
  - соглашения по ссылкам vault
note_type: dev
project: "[[jamming-bot/Jamming Bot]]"
tags:
  - jamming-bot
  - meta
  - obsidian
created: 2026-04-17
updated: 2026-04-17
---

# Соглашения по wikilinks (vault)

Коротко: **в точках входа** (MOC, `_index`, таблицы сервисов) предпочитать **путь от корня vault** (`knowledge/`), чтобы ссылки не ломались при переезде заметки внутри дерева.

## Правила

1. **Проект Jamming Bot** — префикс `jamming-bot/…`, например `[[jamming-bot/Jamming Bot]]`, `[[jamming-bot/dev/bot-service|Bot service]]`.
2. **Технические карточки в `dev/`** — полный путь: `[[jamming-bot/dev/Jamming bot microservices|…]]`, а не только имя файла, если заметка может дублироваться по смыслу или лежать вне привычного контекста поиска.
3. **Справочник `refs/`** — `[[refs/Python|Python]]` и т.п. с корня vault.
4. **Журнал** — `[[journal/2026-04-13]]` или короткое `[[2026-04-13]]` из папки `journal/` (как в [[journal/_index|Journal index]]).
5. **Короткие имена** (`[[Scene 1. Path]]`, `[[jamming bot flask]]`) допустимы там, где vault открыт с корнем `jamming-bot/`; при смешанном использовании править в первую очередь **индексы и MOC**, а не весь граф сразу.

## Именование новых файлов

- Новые dev-заметки по сервисам: осмысленное имя на английском или `Jamming Bot …` + **aliases** в YAML для поиска по-русски.
- Один канонический путь к карточке; при переносе оставлять **stub** в старом месте с ссылкой на канон (как [[bot-service]] в корне → [[jamming-bot/dev/bot-service]]).

## Связанные заметки

- [[jamming-bot/dev/_index|Jamming Bot Dev Index]]
- [[Jamming Bot MOC]]
