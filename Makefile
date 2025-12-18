# Makefile para SEMEFO

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

psql:
	docker exec -it postgres_db psql -U postgres -d semefo

bash-db:
	docker exec -it postgres_db bash

bash-api:
	docker exec -it fastapi_app bash

bash-celery:
	docker exec -it celery_worker bash

backup-db:
	docker exec -t postgres_db pg_dump -U postgres semefo > backups/semefo_backup.sql

restore-db:
	cat backups/semefo_backup.sql | docker exec -i postgres_db psql -U postgres -d semefo

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
	docker compose up -d --build --force-recreate celery celery_video2
	@echo "✅ Workers de Celery reiniciados y reconstruidos."
