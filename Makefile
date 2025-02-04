.PHONY: build
build:
	docker compose up -d --build

.PHONY: test
test:
	python test.py

.PHONY: bot
bot:	
	python bot.py

.PHONY: run
run:	
	python app.py