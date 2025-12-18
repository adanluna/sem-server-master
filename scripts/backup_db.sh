#!/bin/bash
# ============================================================
#  Respaldo automático de la base de datos SEMEFO (Producción)
#  Autor: Adan Luna
#
#  Estrategia:
#   - Respaldo DIARIO de DATOS (data.sql)
#   - Respaldo de ESTRUCTURA (schema.sql) si no existe
#   - Copia en WAVE
#   - Retención de 7 días
# ============================================================

# ---------------- CONFIGURACIÓN ----------------
BACKUP_DIR="/opt/semefo/backups"
WAVE_BACKUP_DIR="/mnt/wave/_backups_db"

DB_CONTAINER="postgres_db"
DB_USER="semefo_user"
DB_NAME="semefo"

DATE=$(date +'%Y-%m-%d_%H-%M-%S')
DATA_FILE="semefo_data_$DATE.sql"
SCHEMA_FILE="semefo_schema.sql"

LOCAL_DATA="$BACKUP_DIR/$DATA_FILE"
LOCAL_SCHEMA="$BACKUP_DIR/$SCHEMA_FILE"

LOGFILE="$BACKUP_DIR/backup.log"

# ---------------- PRE-CHECKS ----------------
mkdir -p "$BACKUP_DIR"

echo "--------------------------------------------------------------" >> "$LOGFILE"
echo "[$(date +'%Y-%m-%d %H:%M:%S')] ===== INICIO BACKUP SEMEFO =====" >> "$LOGFILE"

# Validar contenedor DB
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo "[ERROR] Contenedor PostgreSQL no está corriendo." >> "$LOGFILE"
    exit 1
fi

# Validar WAVE montado
if ! mountpoint -q /mnt/wave; then
    echo "[ERROR] WAVE NO está montado. Backup abortado." >> "$LOGFILE"
    exit 1
fi

mkdir -p "$WAVE_BACKUP_DIR"

# ---------------- BACKUP SCHEMA (solo si no existe) ----------------
if [ ! -f "$LOCAL_SCHEMA" ]; then
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

    cp "$LOCAL_SCHEMA" "$WAVE_BACKUP_DIR/$SCHEMA_FILE"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Schema respaldado correctamente." >> "$LOGFILE"
fi

# ---------------- BACKUP DATA (DIARIO) ----------------
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Generando respaldo de DATOS..." >> "$LOGFILE"

docker exec -t "$DB_CONTAINER" pg_dump \
    --data-only \
    --disable-triggers \
    --column-inserts \
    -U "$DB_USER" "$DB_NAME" > "$LOCAL_DATA"

if [ $? -ne 0 ]; then
    echo "[ERROR] Falló respaldo de datos." >> "$LOGFILE"
    rm -f "$LOCAL_DATA"
    exit 1
fi

cp "$LOCAL_DATA" "$WAVE_BACKUP_DIR/$DATA_FILE"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Respaldo DATA OK: $LOCAL_DATA" >> "$LOGFILE"
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Copia en WAVE OK: $WAVE_BACKUP_DIR/$DATA_FILE" >> "$LOGFILE"

# ---------------- ROTACIÓN (7 DÍAS) ----------------
find "$BACKUP_DIR" -type f -name "*.sql" -mtime +7 -delete
find "$WAVE_BACKUP_DIR" -type f -name "*.sql" -mtime +7 -delete

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Rotación (>7 días) OK." >> "$LOGFILE"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] ===== BACKUP SEMEFO FINALIZADO =====" >> "$LOGFILE"
echo "--------------------------------------------------------------" >> "$LOGFILE"

exit 0
