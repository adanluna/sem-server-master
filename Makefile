# Makefile para SEMEFO

up:
	docker-compose up -d --build

down:
	docker-compose down

restart:
	docker-compose down
	docker-compose up -d --build

logs:
	docker-compose logs -f

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
