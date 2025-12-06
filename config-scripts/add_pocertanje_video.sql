#sudo docker exec -it postgres_db psql -U semefo_user -d semefo -c "ALTER TABLE sesion_archivos ADD COLUMN IF NOT EXISTS progreso_porcentaje FLOAT DEFAULT 0;"
#sudo docker exec -it postgres_db psql -U semefo_user -d semefo -c "ALTER TABLE sesiones ADD COLUMN IF NOT EXISTS progreso_porcentaje FLOAT DEFAULT 0;"

ALTER TABLE sesion_archivos
ADD COLUMN progreso_porcentaje FLOAT DEFAULT 0;
