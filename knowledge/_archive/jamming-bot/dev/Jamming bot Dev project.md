---
title: Jamming Bot Dev Project
aliases:
  - Jamming bot Dev project
note_type: dev
project: "[[jamming-bot/Jamming Bot]]"
dev_area: infra
tags:
  - dev
  - infrastructure
  - jamming-bot
---

# Jamming Bot Dev Project

Техническая заметка по разработке и инфраструктуре проекта.

## Связанные заметки

- [[jamming-bot/Jamming Bot]]
- [[Jamming Bot MOC]]
- [[Jamming bot Tasks]]
- [[Jamming bot Redis Queue Jobs]]
- [[Jamming bot microservices]]
- [[Semantic dev notes]]
- [[jamming bot flask]]

## Графы и визуализация

- [[Graphs visualisation libraries]]

## Text clusterisation

- https://scikit-learn.org/stable/auto_examples/text/plot_document_clustering.html
- https://github.com/BishalLakha/Text-Clustering/tree/master

## UI и сервисы

- https://docs.sentry.io/platforms/python/
- https://www.gradio.app/playground
- https://exifaa.streamlit.app/
- https://codepen.io/Ni55aN/full/jBEKBQ/
- https://neptune.ai/blog/saving-trained-model-in-python
- https://bertlinker.streamlit.app/
- https://zero-shot-text-classifier.streamlit.app/

## Manuals

- https://habr.com/ru/articles/318952/
- https://dev.to/mindsers/https-using-nginx-and-lets-encrypt-in-docker-1ama
- https://cycloss.hashnode.dev/setting-up-free-auto-renewing-tlsssl-certificates-with-docker-docker-compose-certbot-cron-and-nginx
- https://ru.stackoverflow.com/questions/1538557/%D0%A3%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BA%D0%B0-ssl-%D1%81%D0%B5%D1%80%D1%82%D0%B8%D1%84%D0%B8%D0%BA%D0%B0%D1%82%D0%B0-%D0%B4%D0%BB%D1%8F-nginx-docker-%D1%81%D0%B0%D0%BC%D1%8B%D0%B9-%D0%BF%D1%80%D0%BE%D1%81%D1%82%D0%BE%D0%B9-%D0%BF%D1%83%D1%82%D1%8C

## API notes

```javascript
curl -X POST -H "Content-Type: application/json" http://localhost:5000/api/semantic
```

### `POST /api/semantic`

| name | type | data type | description |
| --- | --- | --- | --- |
| `text` | required | string | The specific text |

| http code | content-type | response |
| --- | --- | --- |
| `200` | `text/plain;charset=UTF-8` | JSON string |
| `400` | `application/json` | `{"code":"400","message":"Bad Request"}` |
