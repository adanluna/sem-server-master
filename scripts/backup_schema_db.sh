#!/bin/bash
# ============================================================
#  Respaldo MANUAL de ESTRUCTURA (SCHEMA) - SEMEFO
#  Autor: Adan Luna
#
#  Uso:
#    Ejecutar SOLO cuando haya cambios de estructura:
#    - nuevas tablas
#    - cambios de columnas
#    - enums
#    - funciones / triggers
# ============================================================

# ---------------- CONFIGURACIÓN ----------------
BACKUP_DIR="/opt/semefo/backups"
WAVE_BACKUP_DIR="/mnt/wave/_backups_db"

DB_CONTAINER="postgres_db"
DB_USER="semefo_user"
DB_NAME="semefo"

DATE=$(date +'%Y-%m-%d_%H-%M-%S')
SCHEMA_FILE="semefo_schema_$DATE.sql"

LOCAL_SCHEMA="$BACKUP_DIR/$SCHEMA_FILE"

LOGFILE="$BACKUP_DIR/backup_schema.log"

# ---------------- PRE-CHECKS ----------------
mkdir -p "$BACKUP_DIR"

echo "--------------------------------------------------------------" >> "$LOGFILE"
echo "[$(date +'%Y-%m-%d %H:%M:%S')] ===== INICIO BACKUP SCHEMA =====" >> "$LOGFILE"

# Validar contenedor PostgreSQL
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo "[ERROR] Contenedor PostgreSQL no está corriendo." >> "$LOGFILE"
    exit 1
fi

# Validar WAVE montado
if ! mountpoint -q /mnt/wave; then
    echo "[ERROR] WAVE NO está montado. Backup de schema abortado." >> "$LOGFILE"
    exit 1
fi

mkdir -p "$WAVE_BACKUP_DIR"

# ---------------- BACKUP SCHEMA ----------------
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Generando respaldo de ESTRUCTURA..." >> "$LOGFILE"

docker exec -t "$DB_CONTAINER" pg_dump \
    --schema-only \
    --no-owner \
    --no-privileges \
    -U "$DB_USER" "$DB_NAME" > "$LOCAL_SCHEMA"

if [ $? -ne 0 ]; then
    echo "[ERROR] Falló respaldo de estructura." >> "$LOGFILE"
    rm -f "$LOCAL_SCHEMA"
    exit 1
fi

# Copiar a WAVE
cp "$LOCAL_SCHEMA" "$WAVE_BACKUP_DIR/$SCHEMA_FILE"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Schema generado correctamente:" >> "$LOGFILE"
echo "  - Local: $LOCAL_SCHEMA" >> "$LOGFILE"
echo "  - WAVE : $WAVE_BACKUP_DIR/$SCHEMA_FILE" >> "$LOGFILE"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] ===== BACKUP SCHEMA FINALIZADO =====" >> "$LOGFILE"
echo "--------------------------------------------------------------" >> "$LOGFILE"

exit 0
