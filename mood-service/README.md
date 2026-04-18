# mood-service

HTTP service for **mood + palette** from page text and semantic JSON (same shape as `analyze_semantic` / semantic-service).

## API

- `GET /health` — liveness.
- `POST /api/v1/mood/snapshot/` — JSON `{"text": "...", "semantic": { ... }}` → mood result (dominant mood, NN scores, rule scores, `palette[]` with `hex` / `name` / `mood` / `emotion`).

## First run

- Downloads **Color-Pedia** from Hugging Face and the **rubert-tiny2** emotion model; can take several minutes and significant disk/RAM.
- CPU-only PyTorch is installed in the Docker image (`torch` CPU wheels).

## Environment

- No required env vars for the service itself; bind port **8020** in Docker.

## Kubernetes (K3s)

- Манифесты в корне репозитория: [`deployment.yaml`](../deployment.yaml) — Deployment и Service **`mood-service`** (внутренний порт контейнера **8020**, Service **80 → 8020**).
- CI: [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) собирает образ при изменениях в `mood-service/`.
- Локально на ноде с k3s: `make k3s-mood-service`.

## Legacy

The prototype lived in `app-service/flask/jamming-analyze.py`; logic is now here with `analyze_mood_extended` implemented.
