#!/bin/bash
# ============================================================
#  Respaldo automático de la base de datos SEMEFO
#  Autor: Adan Luna
#  Fecha: $(date +%Y-%m-%d)
#  Descripción:
#     Genera un respaldo de la base de datos PostgreSQL
#     desde el contenedor docker "postgres_db" y lo guarda
#     en /opt/semefo/backups con retención de 7 días.
# ============================================================

# --- Configuración ---
BACKUP_DIR="/opt/semefo/backups"
DB_CONTAINER="postgres_db"
DB_USER="semefo_user"
DB_NAME="semefo"
DATE=$(date +'%Y-%m-%d_%H-%M-%S')
FILE="$BACKUP_DIR/semefo_backup_$DATE.sql"
LOGFILE="$BACKUP_DIR/backup.log"

# --- Crear carpeta de respaldo si no existe ---
mkdir -p "$BACKUP_DIR"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Iniciando respaldo..." >> "$LOGFILE"

# --- Generar respaldo ---
if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    docker exec -t "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$FILE"
    if [ $? -eq 0 ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Respaldo completado: $FILE" >> "$LOGFILE"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ Error: fallo el pg_dump." >> "$LOGFILE"
        rm -f "$FILE"
        exit 1
    fi
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ Error: el contenedor $DB_CONTAINER no está en ejecución." >> "$LOGFILE"
    exit 1
fi

# --- Rotación: elimina respaldos de más de 7 días ---
find "$BACKUP_DIR" -type f -mtime +7 -name "*.sql" -delete
echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🔁 Respaldos antiguos eliminados (mayores a 7 días)." >> "$LOGFILE"

# --- Rotación del log cada 7 días ---
if [ -f "$LOGFILE" ]; then
    LOG_MOD_TIME=$(stat -c %Y "$LOGFILE" 2>/dev/null)
    NOW_TIME=$(date +%s)
    if [ -n "$LOG_MOD_TIME" ]; then
        LOG_AGE_DAYS=$(( (NOW_TIME - LOG_MOD_TIME) / 86400 ))
        if [ "$LOG_AGE_DAYS" -ge 7 ]; then
            mv "$LOGFILE" "$BACKUP_DIR/backup_$(date +'%Y-%m-%d').log"
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🧹 Log anterior archivado y nuevo log iniciado." >> "$BACKUP_DIR/backup.log"
        fi
    fi
fi

echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ Proceso finalizado exitosamente." >> "$LOGFILE"
echo "--------------------------------------------------------------" >> "$LOGFILE"
exit 0
