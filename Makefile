.PHONY: build
build:
	docker compose up -d --build

.PHONY: worker
worker:
	docker compose up -d worker --build	

.PHONY: bot
bot:	
	docker compose up -d bot --build

.PHONY: nginx
nginx:	
	docker compose up -d nginx --build	

.PHONY: flask
flask:	
	docker compose up -d flask --build

.PHONY: frontend
frontend:	
	docker compose up -d frontend --build

# Обновить node_modules во фронтовом томе (после смены package.json / yarn.lock)
.PHONY: frontend-yarn
frontend-yarn:
	docker compose exec -T frontend yarn install --frozen-lockfile

.PHONY: tags-service
tags-service:	
	docker compose up -d tags_service --build

.PHONY: ip-service
ip-service:	
	docker compose up -d ip-service --build	

.PHONY: semantic-service
semantic-service:	
	docker compose up -d semantic_service --build	

.PHONY: cert
cert:
	docker compose run --rm certbot renew
	# docker compose up certbot --build
	# sudo chown -R rslsync:rslsync data/certbot/www/live

# ─── k3s: build, import & restart ───────────────────────────

.PHONY: k3s-html-renderer
k3s-html-renderer:
	docker build -t 1325gy/my_dev:v5 ./html-renderer-service
	docker save 1325gy/my_dev:v5 | k3s ctr images import -
	kubectl rollout restart deployment html-renderer -n jamming-bot

.PHONY: k3s-keywords-service
k3s-keywords-service:
	docker build -t keywords-service:latest ./keywords-service
	docker save keywords-service:latest | k3s ctr images import -
	kubectl rollout restart deployment keywords-service -n jamming-bot

.PHONY: k3s-semantic-service
k3s-semantic-service:
	docker build -t semantic-service:latest ./semantic-service
	docker save semantic-service:latest | k3s ctr images import -
	kubectl rollout restart deployment semantic-service -n jamming-bot

.PHONY: k3s-mood-service
k3s-mood-service:
	docker build -t mood-service:latest ./mood-service
	docker save mood-service:latest | k3s ctr images import -
	kubectl rollout restart deployment mood-service -n jamming-bot
	kubectl rollout restart deployment app-service worker-service worker-screenshots -n jamming-bot

.PHONY: k3s-image-analyze-service
k3s-image-analyze-service:
	docker build -t image-analyze-service:latest ./image-analyze-service
	docker save image-analyze-service:latest | k3s ctr images import -
	kubectl rollout restart deployment image-analyze-service -n jamming-bot

.PHONY: k3s-storage-service
k3s-storage-service:
	docker build -t storage-service:latest ./storage-service
	docker save storage-service:latest | k3s ctr images import -
	kubectl rollout restart deployment storage-service -n jamming-bot

.PHONY: k3s-tags-service
k3s-tags-service:
	docker build -t tags-service:latest ./tags-service
	docker save tags-service:latest | k3s ctr images import -
	kubectl rollout restart deployment tags-service -n jamming-bot

.PHONY: k3s-bot-service
k3s-bot-service:
	docker build -t bot-service:latest ./bot-service
	docker save bot-service:latest | k3s ctr images import -
	kubectl rollout restart deployment bot-service -n jamming-bot

.PHONY: k3s-ip-service
k3s-ip-service:
	docker build -t ip-service:latest ./ip-service
	docker save ip-service:latest | k3s ctr images import -
	kubectl rollout restart deployment ip-service -n jamming-bot

.PHONY: k3s-app-service
k3s-app-service:
	docker build -t app-service:latest ./app-service
	docker save app-service:latest | k3s ctr images import -
	kubectl rollout restart deployment app-service -n jamming-bot
	kubectl rollout restart deployment worker-service worker-screenshots -n jamming-bot

.PHONY: k3s-data-service
k3s-data-service:
	docker build -t data-service:latest ./data-service
	docker save data-service:latest | k3s ctr images import -
	kubectl rollout restart deployment data-service -n jamming-bot

.PHONY: k3s-frontend-static-app
k3s-frontend-static-app:
	docker build -f ./frontend/Dockerfile.prod -t frontend-static-app:latest ./frontend
	docker save frontend-static-app:latest | k3s ctr images import -
	kubectl rollout restart deployment frontend-static-app -n jamming-bot

.PHONY: k3s-services-map
k3s-services-map:
	docker build -f ./services-map/Dockerfile.prod -t services-map:latest .
	docker save services-map:latest | k3s ctr images import -
	kubectl rollout restart deployment services-map -n jamming-bot

.PHONY: k3s-backfill-worker
k3s-backfill-worker:
	docker build -t backfill-worker:latest ./backfill-worker
	docker save backfill-worker:latest | k3s ctr images import -
	-kubectl delete job backfill-worker -n jamming-bot 2>/dev/null; true
	kubectl apply -f deployment.yaml
	@echo "backfill-worker job started. Monitor: kubectl logs -n jamming-bot job/backfill-worker -f"

.PHONY: k3s-all
k3s-all: k3s-html-renderer k3s-keywords-service k3s-semantic-service k3s-mood-service k3s-image-analyze-service k3s-storage-service k3s-tags-service k3s-bot-service k3s-ip-service k3s-app-service k3s-data-service k3s-frontend-static-app

.PHONY: k3s-cert-manager
k3s-cert-manager:
	kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml
	@echo "Waiting for cert-manager pods to be ready..."
	kubectl wait --for=condition=Ready pods --all -n cert-manager --timeout=120s

.PHONY: k3s-apply
k3s-apply:
	@test -f k8s-secrets.yaml && kubectl apply -f k8s-secrets.yaml || echo "WARN: k8s-secrets.yaml not found — create it from k8s-secrets.yaml.template"
	kubectl apply -f deployment.yaml

.PHONY: k3s-traefik-stabilize
k3s-traefik-stabilize:
	kubectl -n kube-system patch deployment traefik --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/timeoutSeconds","value":5},{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/timeoutSeconds","value":5},{"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/initialDelaySeconds","value":10},{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/initialDelaySeconds","value":10}]'
	kubectl -n kube-system rollout restart deployment/traefik
	kubectl -n kube-system rollout status deployment/traefik --timeout=240s

# Coroot CE + operator (namespace coroot). HTTPS UI: https://coroot.jamming-bot.arthew0.online/
# Docs: docs/monitoring/coroot-runbook.md — chart versions pinned below.
COROOT_OPERATOR_CHART_VERSION ?= 0.9.4
COROOT_CE_CHART_VERSION ?= 0.3.3

.PHONY: k3s-coroot
k3s-coroot:
	helm repo add coroot https://coroot.github.io/helm-charts 2>/dev/null || true
	helm repo update coroot
	kubectl create namespace coroot --dry-run=client -o yaml | kubectl apply -f -
	kubectl label namespace coroot pod-security.kubernetes.io/enforce=privileged --overwrite
	helm upgrade --install coroot-operator coroot/coroot-operator \
		--namespace coroot \
		--version $(COROOT_OPERATOR_CHART_VERSION) \
		--wait --timeout 10m
	helm upgrade --install coroot coroot/coroot-ce \
		--namespace coroot \
		--version $(COROOT_CE_CHART_VERSION) \
		--values docs/monitoring/coroot-values.yaml \
		--wait --timeout 30m
	@echo "Coroot: kubectl get pods,ingress -n coroot"
	@echo "UI: https://coroot.jamming-bot.arthew0.online/"

.PHONY: k3s-coroot-prometheus-ksm-scrape
# Patches Coroot's Prometheus init config to scrape chart kube-state-metrics (UI health check).
k3s-coroot-prometheus-ksm-scrape:
	./scripts/coroot-prometheus-add-kube-state-metrics-scrape.sh

.PHONY: k3s-coroot-uninstall
k3s-coroot-uninstall:
	-helm uninstall coroot -n coroot
	-helm uninstall coroot-operator -n coroot
	@echo "Optional: kubectl delete namespace coroot"

# kube-state-metrics (namespace kube-state-metrics) — cluster state metrics for Prometheus/Coroot.
# Chart: https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-state-metrics
KUBE_STATE_METRICS_CHART_VERSION ?= 7.3.0

.PHONY: k3s-kube-state-metrics
k3s-kube-state-metrics:
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
	helm repo update prometheus-community
	kubectl create namespace kube-state-metrics --dry-run=client -o yaml | kubectl apply -f -
	helm upgrade --install kube-state-metrics prometheus-community/kube-state-metrics \
		--namespace kube-state-metrics \
		--version $(KUBE_STATE_METRICS_CHART_VERSION) \
		--wait --timeout 10m
	@echo "Smoke: kubectl get pods,svc -n kube-state-metrics"

.PHONY: k3s-kube-state-metrics-uninstall
k3s-kube-state-metrics-uninstall:
	-helm uninstall kube-state-metrics -n kube-state-metrics
	@echo "Optional: kubectl delete namespace kube-state-metrics"