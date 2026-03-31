---
title: Constellation
note_type: web_entry
web_type: page
project: "[[Jamming Bot]]"
parent: "[[pages/_index|Jamming Bot Pages Index]]"
url: https://jamming-bot.arthew0.online/tags/constellation/
tags:
  - web
  - page
  - constellation
  - tags
  - jamming-bot
---

# Constellation

## URL

https://jamming-bot.arthew0.online/tags/constellation/

## Описание

В этом режиме теги превращаются не в облако и не в поток, а в сеть созвездий, где отдельные смысловые узлы соединяются в хрупкую структуру. Визуализация показывает интернет как тёмное пространство, в котором фрагменты языка вспыхивают связями и собираются в почти астрономическую карту памяти.

## Алгоритм

Constellation использует не отдельный dataset, а текущий поток тегов проекта. 
Страница берёт теги через
```
GET /api/tags/get/
```
 затем отправляет их в 
```
POST /api/tags/embeddings/
```
 где Flask строит компактное представление на базе spaCy-векторов.