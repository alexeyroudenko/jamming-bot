# Coroot (jamming-bot)

Цель: развернуть [Coroot Community Edition](https://docs.coroot.com/installation/kubernetes/) и открыть UI по адресам:

- HTTPS: `https://coroot.jamming-bot.arthew0.online/`
- HTTP редиректится ингрессом Traefik/cert-manager типичным образом (если настроен только HTTPS).

Метрики Flask/RQ см. [app-service-monitoring-runbook.md](app-service-monitoring-runbook.md); здесь только Coroot.

## Трассы OpenTelemetry (Jaeger + Coroot)

В кластере в namespace `jamming-bot` развёрнут **OpenTelemetry Collector** (`Deployment`/`Service` **`otel-collector`**, см. [`deployment.yaml`](../../deployment.yaml)): `app-service`, `worker-service` и `bot-service` отправляют OTLP HTTP на **`http://otel-collector:4318`**; collector дублирует трассы в **Jaeger** и в **Coroot** (OTLP gRPC на `coroot-coroot.coroot.svc.cluster.local:4317` с заголовком **`x-api-key`**).

Ключ API проекта Coroot хранится в Secret **`jamming-bot-secrets`**, ключ **`COROOT_OTEL_API_KEY`** (шаблон: [`k8s-secrets.yaml.template`](../../k8s-secrets.yaml.template)). Должен совпадать с ключом в UI Coroot для этого проекта.

Локально в Docker Compose тот же collector описан в [`docker/otel-collector-config.yaml`](../../docker/otel-collector-config.yaml); переменные окружения **`COROOT_OTEL_API_KEY`** и **`COROOT_OTLP_GRPC_ADDR`** (по умолчанию `host.docker.internal:4317`, см. `docker-compose.yml`).

## Зафиксированные версии Helm chart (актуализировать при апгрейде)

Проверка доступных версий:

```bash
helm repo add coroot https://coroot.github.io/helm-charts
helm repo update coroot
helm search repo coroot/coroot-operator -l | head -5
helm search repo coroot/coroot-ce -l | head -5
```

На момент добавления runbook в репозитории зафиксировано:

| Chart             | Версия |
|-------------------|--------|
| coroot-operator   | 0.9.4  |
| coroot-ce         | 0.3.3  |

## Предварительные условия

- Установлены `kubectl`, `helm` и доступ к kubeconfig кластера (например k3s: `KUBECONFIG=/etc/rancher/k3s/k3s.yaml`).
- Уже есть **ClusterIssuer** `letsencrypt-prod` (в репозитории задаётся в [`deployment.yaml`](../../deployment.yaml)); cert-manager выпускает TLS-секрет для ingress.
- DNS **A/AAAA** для хоста `coroot.jamming-bot.arthew0.online` указывает на ваш ingress/load balancer так же, как для `jamming-bot.arthew0.online`.
- У node-agent Coroot нужны привилегированные возможности для eBPF; при ошибках Pod Security см. раздел Troubleshooting ниже.

## Установка (Makefile)

На машине с доступом к кластеру из корня репозитория:

```bash
make k3s-coroot
```

Цель ставит оператор и Coroot CE в namespace `coroot`, использует [`coroot-values.yaml`](coroot-values.yaml) (ingress + размеры PVC).

## Установка вручную

```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml   # при необходимости

helm repo add coroot https://coroot.github.io/helm-charts
helm repo update coroot

kubectl create namespace coroot --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace coroot pod-security.kubernetes.io/enforce=privileged --overwrite

helm upgrade --install coroot-operator coroot/coroot-operator \
  --namespace coroot \
  --version 0.9.4 \
  --wait --timeout 10m

helm upgrade --install coroot coroot/coroot-ce \
  --namespace coroot \
  --version 0.3.3 \
  --values docs/monitoring/coroot-values.yaml \
  --wait --timeout 30m
```

Smoke после установки:

```bash
kubectl get pods -n coroot
kubectl get ingress -n coroot
```

Ожидается ingress на хост `coroot.jamming-bot.arthew0.online` с TLS secret `coroot-jamming-bot-tls` (после выпуска cert-manager).

## Обнаружение сервисов namespace `jamming-bot`

Coroot поднимает node/cluster агентов и собирает метрики по подам кластера. После установки в UI должны появиться рабочие нагрузки из `jamming-bot` (например `app-service`, `worker-service`, `redis`, `tags-service`, `storage-service`), когда поды запущены и экспортируют стандартные Kubernetes/Prometheus сигналы.

Если список пустой:

- убедитесь, что DaemonSet node-agent в `Running` на всех нужных нодах;
- проверьте события: `kubectl describe pod -n coroot -l app.kubernetes.io/name=coroot-node-agent` (лейблы могут отличаться — используйте `kubectl get pods -n coroot --show-labels`).

## Upgrade

```bash
helm repo update coroot
helm upgrade coroot-operator coroot/coroot-operator -n coroot --version <NEW> --wait
helm upgrade coroot coroot/coroot-ce -n coroot --version <NEW> -f docs/monitoring/coroot-values.yaml --wait
```

Оператор Coroot по документации обновляет связанные компоненты автоматически.

## Rollback

```bash
helm rollback coroot -n coroot
helm rollback coroot-operator -n coroot
```

Либо удалить релиз и переустановить предыдущие версии chart из секции выше.

## Полное удаление

```bash
helm uninstall coroot -n coroot
helm uninstall coroot-operator -n coroot
kubectl delete namespace coroot
```

PVC в namespace при удалении namespace удалятся вместе с данными — при необходимости сделайте бэкап заранее.

## Troubleshooting

### Pod Security / privileged

Если агент на нодах не стартует из-за политики безопасности подов:

```bash
kubectl label namespace coroot pod-security.kubernetes.io/enforce=privileged --overwrite
```

См. [официальную заметку](https://docs.coroot.com/installation/kubernetes/).

### TLS / сертификат не выпускается

- `kubectl describe certificate -n coroot`
- `kubectl describe challenge -n coroot`
- Убедитесь, что ClusterIssuer `letsencrypt-prod` существует и HTTP-01 доступен снаружи.

### Дисковое место ClickHouse / Prometheus

Размеры PVC заданы в [`coroot-values.yaml`](coroot-values.yaml); при нехватке места увеличьте `storage.size` для `clickhouse` / `prometheus` и переустановите или расширьте PVC по политике StorageClass.

### В UI: «kube-state-metrics: no kube-state-metrics installed»

Встроенный Prometheus от **coroot-operator** по умолчанию скрейпит только `127.0.0.1:9090`. Проверка в UI ищет метрики `kube_*` в **этом** Prometheus, поэтому отдельный Helm chart `kube-state-metrics` сам по себе индикатор не «вылечит», пока Prometheus не начнёт скрейпить его Service.

В репозитории:

1. `make k3s-kube-state-metrics` — Service `kube-state-metrics.kube-state-metrics:8080`.
2. `make k3s-coroot-prometheus-ksm-scrape` — скрипт [`scripts/coroot-prometheus-add-kube-state-metrics-scrape.sh`](../../scripts/coroot-prometheus-add-kube-state-metrics-scrape.sh) дописывает `scrape_configs` и **`metric_relabel_configs`**: ко всем точкам из job `kube-state-metrics` добавляется лейбл `coroot_project_id=<id проекта>`. Иначе Coroot при запросах к Prometheus всегда накладывает селектор `{coroot_project_id="…"}` ([`db/project.go` в upstream](https://github.com/coroot/coroot/blob/master/db/project.go)), и «сырые» метрики KSM не попадают в модель — в настройках проекта остаётся «no kube-state-metrics installed». Id проекта скрипт берёт из SQLite Coroot (должен быть **ровно один** проект) или из переменной **`COROOT_PROJECT_ID`**.

**Важно:** при работающем `coroot-operator` он сразу откатывает патч Deployment. По умолчанию скрипт **останавливает** `coroot-operator` (`kubectl scale … --replicas=0`), патчит Prometheus и **не** поднимает оператор обратно — иначе конфиг снова затрётся. Если нужен живой оператор (реконсил CR Coroot), после `kubectl scale deployment/coroot-operator -n coroot --replicas=1` снова выполните `make k3s-coroot-prometheus-ksm-scrape` (или держите оператор на 0, пока не обновляете CR вручную).

Отключить паузу оператора (патч почти наверняка не сохранится): `COROOT_PAUSE_OPERATOR=0 make k3s-coroot-prometheus-ksm-scrape`.

### Локальный доступ без ingress

```bash
kubectl port-forward -n coroot svc/coroot-coroot 8080:8080
# UI: http://localhost:8080
```

Официальная подсказка из [документации Coroot](https://docs.coroot.com/installation/kubernetes/).
