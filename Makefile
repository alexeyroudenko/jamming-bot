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
	kubectl rollout restart deployment worker-service -n jamming-bot

.PHONY: k3s-all
k3s-all: k3s-html-renderer k3s-keywords-service k3s-semantic-service k3s-storage-service k3s-tags-service k3s-bot-service k3s-ip-service k3s-app-service

.PHONY: k3s-cert-manager
k3s-cert-manager:
	kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml
	@echo "Waiting for cert-manager pods to be ready..."
	kubectl wait --for=condition=Ready pods --all -n cert-manager --timeout=120s

.PHONY: k3s-apply
k3s-apply:
	@test -f k8s-secrets.yaml && kubectl apply -f k8s-secrets.yaml || echo "WARN: k8s-secrets.yaml not found — create it from k8s-secrets.yaml.template"
	kubectl apply -f deployment.yaml