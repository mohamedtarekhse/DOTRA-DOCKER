SHELL := /bin/bash

.PHONY: help up down logs ps build stop restart seed backup status models

help:
	@echo "ACUSEEK deployment shortcuts"
	@echo "  make up        - build & start all services"
	@echo "  make down      - stop all services"
	@echo "  make restart   - restart all services"
	@echo "  make ps        - list running services"
	@echo "  make logs      - follow all logs"
	@echo "  make build     - rebuild images"
	@echo "  make seed      - seed 40 cameras + zones"
	@echo "  make backup    - backup postgres to ./backups"
	@echo "  make status    - health status of services"

up:
	@test -f .env || (echo "ERROR: create .env from .env.example first" && exit 1)
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=100

build:
	docker compose build

seed:
	docker compose exec api python ./seed_cameras.py

backup:
	@mkdir -p backups
	docker compose exec -T postgres pg_dump -U $$POSTGRES_USER $$POSTGRES_DB > backups/acuseek_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup saved to ./backups"

status:
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
