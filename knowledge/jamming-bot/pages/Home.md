---
title: Home
note_type: web_entry
web_type: page
project: "[[jamming-bot/Jamming Bot]]"
parent: "[[pages/_index|Jamming Bot Pages Index]]"
url: https://jamming-bot.arthew0.online/
tags:
  - web
  - page
  - jamming-bot
---

# Home

## URL

https://jamming-bot.arthew0.online/

## Описание

Главная страница собирает проект как единое произведение data-driven generative art, где бот выступает последним выжившим существом в разрушенном интернете. Отсюда открывается доступ к визуализациям, API и служебным интерфейсам, через которые хаос собранных данных превращается в художественный джем.

## Данные

На главной странице отображаются основные навигационные и служебные блоки проекта:

- визуализации: `tag cloud`, `3D cloud`, `geo globe`, `screenshot`, `path map`, `phrases`, `sentiment vortex`, `react UI`
- API и действия: `get tags`, `add tags`, `add_tags_from_steps`, `clean tags`, `api`
- служебные панели: `dashboard`, `queue`
- статусные поля: `value`, `counter`, `latency`
- управление ботом: `step`, `stop`, `start`, `restart`, `add`
- сессия: `login`, `logout`

## Лог-блоки

- `log_text` — основной текстовый блок текущего шага. Сюда анимированно выводится текст страницы, которую бот в данный момент обрабатывает.
- `log_phrases` — блок структурированного смыслового вывода. Здесь показываются фразы, `struct_text` и результаты анализа вроде noun phrases.
- `log_sub` — лог найденных субссылок. Блок накапливает URL, которые бот извлёк со страницы как возможные следующие переходы.
- `log_events` — лог внутренних событий пайплайна. Он показывает последовательность событий работы бота и время между ними, то есть ритм выполнения системы.



