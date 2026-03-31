---
title: Jamming Bot Redis Queue Jobs
aliases:
  - Jamming bot Redis Queue Jobs
note_type: dev
project: "[[Jamming Bot]]"
dev_area: infra
tags:
  - dev
  - queue
  - redis
  - jamming-bot
---

# Jamming Bot Redis Queue Jobs

- `jobs.dostep(data)` — store in queue
- `jobs.dopass(ip)` — use `maxminddb` for geolocation detection
- `jobs.analyze(html_string)` — `BeautifulSoup` for parsing, `spacy` for words and noun phrases
- `jobs.screenshot(data)`
- `jobs.save(data)`
