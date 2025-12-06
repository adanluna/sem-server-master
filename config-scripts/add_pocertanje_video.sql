#sudo docker exec -it postgres_db psql -U semefo_user -d semefo -c "ALTER TABLE sesion_archivos ADD COLUMN IF NOT EXISTS progreso_porcentaje FLOAT DEFAULT 0;"
#sudo docker exec -it postgres_db psql -U semefo_user -d semefo -c "ALTER TABLE sesiones ADD COLUMN IF NOT EXISTS progreso_porcentaje FLOAT DEFAULT 0;"
#sudo docker exec -it postgres_db psql -U semefo_user -d semefo -c "ALTER TABLE sesion_archivos ADD COLUMN sha256 TEXT; ALTER TABLE sesion_archivos ADD COLUMN duracion_archivo_seg FLOAT; ALTER TABLE sesion_archivos ADD COLUMN duracion_sesion_seg FLOAT;"


ALTER TABLE sesion_archivos
ADD COLUMN progreso_porcentaje FLOAT DEFAULT 0;
