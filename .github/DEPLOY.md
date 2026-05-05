# K3s Deployment Setup

This guide explains how to configure the CI/CD pipeline to deploy jamming-bot to your K3s cluster at `b0ts.arthew0.online`.

## Prerequisites

1. **K3s cluster** running on `b0ts.arthew0.online`
2. **SSH access** to the server with Docker and kubectl available
3. **Git repository** cloned on the server at the deploy path

## One-time Server Setup

SSH into your server and run:

```bash
# Clone the repo (if not already present)
sudo mkdir -p /opt
sudo git clone https://github.com/YOUR_USERNAME/jamming-bot.git /opt/jamming-bot
cd /opt/jamming-bot

# Ensure kubectl uses k3s config
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
# Or add to ~/.bashrc for your deploy user
```

## GitHub Secrets

Add these secrets in your repo: **Settings → Secrets and variables → Actions**

| Secret | Required | Description |
|--------|----------|-------------|
| `K3S_SSH_HOST` | No | SSH host (default: `b0ts.arthew0.online`) |
| `K3S_SSH_USER` | **Yes** | SSH username (e.g. `root` or `deploy`) |
| `K3S_SSH_PRIVATE_KEY` | One of these | Full contents of your SSH private key (recommended) |
| `K3S_SSH_PASSWORD` | One of these | SSH password (alternative to key) |
| `K3S_SSH_PORT` | No | SSH port (default: `22`) |
| `K3S_DEPLOY_PATH` | No | Path to repo on server (default: `/opt/jamming-bot`) |

**Error: "can't connect without a private SSH key or password"** — Add either `K3S_SSH_PRIVATE_KEY` or `K3S_SSH_PASSWORD`.

### Generate SSH key for deploy

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""
# Add deploy_key.pub to server's ~/.ssh/authorized_keys
# Add deploy_key contents to K3S_SSH_PRIVATE_KEY secret
```

## Workflow Triggers

- **Push to `main`** – deploys automatically
- **Manual** – run via Actions → Deploy to K3s → Run workflow

## Deployment Flow

1. GitHub Actions SSHs into the server
2. Pulls latest code from `main`
3. Builds all Docker images locally on the server
4. Imports images into K3s (`k3s ctr images import`)
5. Applies `deployment.yaml`
6. Restarts all deployments for rolling update

### Coroot (опционально)

Мониторинг уровня кластера через Coroot CE не входит в стандартный CI-деплой `deployment.yaml`. Разово на сервере:

```bash
cd /opt/jamming-bot
make k3s-coroot
```

Подробнее: [`docs/monitoring/coroot-runbook.md`](../docs/monitoring/coroot-runbook.md).

### Traefik stability (K3s)

Если ingress (`traefik` в `kube-system`) уходит в `CrashLoopBackOff` из-за слишком агрессивных probe-таймаутов, примените фикс:

```bash
cd /opt/jamming-bot
make k3s-traefik-stabilize
```

Команда:
- увеличивает `timeoutSeconds` для `liveness/readiness` до `5`,
- ставит `initialDelaySeconds` в `10`,
- перезапускает `traefik` и ждёт успешный rollout.

### OpenTelemetry: Jaeger + Coroot (K3s)

В [`deployment.yaml`](../deployment.yaml) поднят **`otel-collector`**: приложения (`app-service`, `worker-service`, `bot-service`) шлют OTLP на `http://otel-collector:4318`, collector экспортирует трассы в **Jaeger** (`http://jaeger:4318`) и в **Coroot** (gRPC `coroot-coroot.coroot.svc.cluster.local:4317`, заголовок `x-api-key`).

В [`k8s-secrets.yaml`](../k8s-secrets.yaml) (из шаблона [`k8s-secrets.yaml.template`](../k8s-secrets.yaml.template)) обязательно задайте ключ **`COROOT_OTEL_API_KEY`** — API key проекта Coroot (Settings → API keys). Без него под `otel-collector` не стартует (`secretKeyRef`).

### kube-state-metrics (опционально)

Метрики состояния объектов API: `make k3s-kube-state-metrics` (namespace `kube-state-metrics`). Для индикатора KSM во **встроенном** Prometheus Coroot нужен доп. scrape, см. `make k3s-coroot-prometheus-ksm-scrape` и [`docs/monitoring/coroot-runbook.md`](../docs/monitoring/coroot-runbook.md) (раздел про UI).

### RQ: очередь скриншотов (`screenshots`)

- Джобы **`do_screenshot`** ставятся в очередь **`screenshots`**, забирает их Deployment **`worker-screenshots`** (тот же образ, что и **`worker-service`**, переменная **`RQ_QUEUE_NAMES=screenshots`**).
- Очередь **`default`** обрабатывают поды **`worker-service`** (**`RQ_QUEUE_NAMES=default`**, минимум 2 реплики через KEDA).
- После апдейта со старой схемой (скрины жили в `default`) можно разово перенести висящие задачи:
  ```bash
  kubectl -n jamming-bot exec deploy/app-service -- python migrate_screenshot_jobs.py --dry-run
  kubectl -n jamming-bot exec deploy/app-service -- python migrate_screenshot_jobs.py
  ```
  (скрипт в образе: каталог `/app`, файл `migrate_screenshot_jobs.py`.)

### mood-service (K3s)

- Образ **`mood-service:latest`** собирается из каталога **`mood-service/`** (см. `build_and_import` в [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)).
- В кластере: Deployment **`mood-service`**, Service **`mood-service`** (ClusterIP, порт 80 → 8020), см. [`deployment.yaml`](deployment.yaml).
- **Ресурсы:** запрос ~2 Gi RAM, лимит до 6 Gi; первый старт долгий (загрузка Color-Pedia и модели) — readiness с большим `initialDelaySeconds`.
- **Flask и RQ worker** получают **`MOOD_SERVICE_URL=http://mood-service`** в том же манифесте. Локальная сборка одного образа: `make k3s-mood-service`.
