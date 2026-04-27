# app-service monitoring runbook

Короткий набор действий для мониторинга `app-service` в Grafana/Prometheus: загрузка, latency, отказоустойчивость и проблемы downstream-сервисов.

## 1) Что уже есть в проекте

- `GET /metrics` в `app-service/flask/app.py`
- Сервисы для доступа к метрикам:
  - `app-service-metrics` (`NodePort 30500`)
  - `app-metrics-lb` (`LoadBalancer :5000`)
- RQ наблюдаемость:
  - `rq-exporter` (`ClusterIP 9726`, `LoadBalancer :9101`)
  - `ServiceMonitor` для `rq-exporter`

## 2) Импорт дашборда

1. Grafana -> Dashboards -> Import
2. Выбери файл `docs/monitoring/app-service-grafana-dashboard.json`
3. Назначь Prometheus datasource

Панели в дашборде:
- RPS и top endpoints
- p95/p99 latency
- 5xx ratio и 5xx by endpoint
- exceptions
- CPU/RAM процесса
- pipeline gauges (`step_number`, `steps_forwards`)
- RQ queued/failed

## 3) Alert rules

Файл: `docs/monitoring/app-service-alert-rules.yaml`

Применение:

```bash
kubectl apply -f docs/monitoring/app-service-alert-rules.yaml
```

Включает алерты:
- `AppServiceHigh5xxRatio`
- `AppServiceHighLatencyP95`
- `AppServiceUnhandledExceptions`
- `AppServiceNoTraffic`
- `RQQueueBacklogGrowing`
- `RQFailedJobsSpike`

## 4) Checklist: app-service реально скрейпится?

### Быстрый smoke test

```bash
curl -sS https://jamming-bot.arthew0.online/app/metrics | head
curl -sS http://jamming-bot.arthew0.online:30500/metrics | head
curl -sS http://jamming-bot.arthew0.online:5000/metrics | head
```

### Проверка из Prometheus UI

В `Targets` должен быть активный target для `app-service`.

### Проверка серий в Prometheus

Выполни в Explore:

```promql
flask_http_request_duration_seconds_count
```

Если пусто — app-service не скрейпится.

## 5) Рекомендуемый шаг в кластере (важно)

В репозитории сейчас нет `ServiceMonitor` для `app-service` (есть только для `rq-exporter`).

Рекомендуется добавить отдельный `ServiceMonitor` на `app-service-metrics` (port `5000`, path `/metrics`, interval `15s`) — это делает сбор метрик стабильным и независимым от внешних LB/NodePort маршрутов.

## 6) Как отличать проблему app-service от проблемы downstream

Сигналы, что болит сам `app-service`:
- растут `flask_http_request_exceptions_total`
- растет latency по всем endpoint
- CPU/RAM процесса упираются

Сигналы, что болят микросервисы вокруг:
- всплеск 5xx только на proxy endpoint (`/api/tags/*`, `/semantic/*`, `/api/storage/*`)
- рост `rq_jobs{status="failed"}` / backlog `rq_jobs{status="queued"}`
- предупреждения в логах `app-service`:
  - `do_storage: storage service error`
  - `analyze_semantic:`
  - `mood_snapshot:`
  - `api_data_service_urls: timeout`

