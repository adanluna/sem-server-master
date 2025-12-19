# Makefile para SEMEFO
# ========================
# Variables DB (PostgreSQL)
# ========================
DB_CONTAINER=postgres_db
DB_NAME=semefo
DB_USER=semefo_user

up:
	docker compose up -d --build

down:
	docker compose down

stop:
	docker compose stop

restart:
	docker compose down
	docker compose up -d --build

logs:
	docker compose logs -f

bash-api:
	docker exec -it fastapi_app bash

bash-celery:
	docker exec -it celery_worker bash

psql:
	docker exec -it $(DB_CONTAINER) psql -U $(DB_USER) -d $(DB_NAME)

bash-db:
	docker exec -it $(DB_CONTAINER) bash

backup-db:
	docker exec -t $(DB_CONTAINER) pg_dump -U $(DB_USER) $(DB_NAME) > backups/semefo_backup.sql

restore-db:
	cat backups/semefo_backup.sql | docker exec -i $(DB_CONTAINER) psql -U $(DB_USER) -d $(DB_NAME)


# 🔥 Workers locales en Mac

stop-workers:
	@echo "🚀 Deteniendo todos los workers locales..."
	-pkill -f "celery -A" || true

start-workers:
	@echo "🚀 Iniciando workers locales con iniciar_workers.sh..."
	./scripts/iniciar_workers.sh

restart-workers: stop-workers start-workers
	@echo "✅ Workers locales reiniciados correctamente."

restart-celery:
	@echo "♻️  Reiniciando workers de Celery en Docker..."
	docker compose up -d --build --force-recreate celery
	@echo "✅ Workers de Celery reiniciados y reconstruidos."
