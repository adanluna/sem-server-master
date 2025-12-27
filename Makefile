# ============================================================
# Makefile para SEMEFO
# ============================================================

# ========================
# Variables DB (PostgreSQL)
# ========================
DB_CONTAINER=postgres_db
DB_NAME=semefo
DB_USER=semefo_user

# ========================
# Docker Compose files
# ========================
COMPOSE_BASE=docker-compose.yml
COMPOSE_MAC=docker-compose.dev.yml

# ============================================================
# PRODUCCIÓN / LINUX (Server Master)
# ============================================================

up:
	docker compose -f $(COMPOSE_BASE) up -d --build

down:
	docker compose -f $(COMPOSE_BASE) down

stop:
	docker compose -f $(COMPOSE_BASE) stop

restart:
	docker compose -f $(COMPOSE_BASE) down
	docker compose -f $(COMPOSE_BASE) up -d --build

logs:
	docker compose -f $(COMPOSE_BASE) logs -f

# ============================================================
# DESARROLLO / MAC (emulación /mnt/wave)
# ============================================================

up-dev:
	docker compose \
		-f $(COMPOSE_BASE) \
		-f $(COMPOSE_MAC) \
		up -d --build

down-dev:
	docker compose \
		-f $(COMPOSE_BASE) \
		-f $(COMPOSE_MAC) \
		down

restart-dev:
	docker compose \
		-f $(COMPOSE_BASE) \
		-f $(COMPOSE_MAC) \
		down
	docker compose \
		-f $(COMPOSE_BASE) \
		-f $(COMPOSE_MAC) \
		up -d --build

logs-dev:
	docker compose \
		-f $(COMPOSE_BASE) \
		-f $(COMPOSE_MAC) \
		logs -f

# ============================================================
# BASH / ACCESO A CONTENEDORES
# ============================================================

bash-api:
	docker exec -it fastapi_app bash

bash-celery:
	docker exec -it celery_uniones bash

bash-db:
	docker exec -it $(DB_CONTAINER) bash

psql:
	docker exec -it $(DB_CONTAINER) psql -U $(DB_USER) -d $(DB_NAME)

# ============================================================
# BACKUPS DB
# ============================================================

backup-db:
	mkdir -p backups
	docker exec -t $(DB_CONTAINER) pg_dump -U $(DB_USER) $(DB_NAME) > backups/semefo_backup.sql

restore-db:
	cat backups/semefo_backup.sql | docker exec -i $(DB_CONTAINER) psql -U $(DB_USER) -d $(DB_NAME)

# ============================================================
# 🔥 Workers locales en Mac (NO Docker)
# ============================================================

stop-workers:
	@echo "🛑 Deteniendo todos los workers locales..."
	-pkill -f "celery -A" || true

start-workers:
	@echo "🚀 Iniciando workers locales con iniciar_workers.sh..."
	./scripts/iniciar_workers.sh

restart-workers: stop-workers start-workers
	@echo "✅ Workers locales reiniciados correctamente."

# ============================================================
# ♻️ Reinicio rápido de Celery en Docker
# ============================================================

restart-celery:
	@echo "♻️  Reiniciando workers de Celery en Docker..."
	docker compose -f $(COMPOSE_BASE) up -d --build --force-recreate celery_uniones celery_manifest
	@echo "✅ Workers de Celery reiniciados."
