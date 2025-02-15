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

.PHONY: ip-service
ip-service:	
	docker compose up -d ip-service --build	