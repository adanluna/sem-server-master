#!/bin/bash
# ============================================================
#  Respaldo automático de la base de datos SEMEFO (Producción)
#  Autor: Adan Luna
#
#  - Genera respaldo PostgreSQL desde Docker (MASTER)
#  - Guarda copia local
#  - Replica respaldo en WAVE (/mnt/wave)
#  - Retención de 7 días
# ============================================================

set -e

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Docker / DB
DB_CONTAINER="postgres_db"
DB_USER="semefo_user"
DB_NAME="semefo"

# Rutas
WAVE_MOUNT="/mnt/wave"
BACKUP_DIR="/opt/semefo/backups"
WAVE_BACKUP_DIR="$WAVE_MOUNT/_backups_db"

# Archivos
DATE=$(date +'%Y-%m-%d_%H-%M-%S')
FILE_NAME="semefo_backup_${DATE}.sql"
LOCAL_FILE="$BACKUP_DIR/$FILE_NAME"
REMOTE_FILE="$WAVE_BACKUP_DIR/$FILE_NAME"
LOGFILE="$BACKUP_DIR/backup.log"

# Retención
RETENTION_DAYS=7

# ============================================================
# INICIO
# ============================================================

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ===== INICIO BACKUP SEMEFO =====" >> "$LOGFILE"

# ============================================================
# 1. Validar contenedor PostgreSQL
# ============================================================

if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Contenedor $DB_CONTAINER no está corriendo." >> "$LOGFILE"
    exit 1
fi

# ============================================================
# 2. Generar respaldo local
# ============================================================

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Generando respaldo local..." >> "$LOGFILE"

if docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$LOCAL_FILE"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Respaldo local OK: $LOCAL_FILE" >> "$LOGFILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Falló pg_dump." >> "$LOGFILE"
    rm -f "$LOCAL_FILE"
    exit 1
fi

# ============================================================
# 3. Copia a WAVE (Grabador)
# ============================================================

if mountpoint -q "$WAVE_MOUNT"; then
    mkdir -p "$WAVE_BACKUP_DIR"

    if cp "$LOCAL_FILE" "$REMOTE_FILE"; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Copia en WAVE OK: $REMOTE_FILE" >> "$LOGFILE"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: No se pudo copiar a WAVE." >> "$LOGFILE"
    fi
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ADVERTENCIA: WAVE no montado, respaldo solo local." >> "$LOGFILE"
fi

# ============================================================
# 4. Rotación de respaldos locales
# ============================================================

find "$BACKUP_DIR" -type f -name "*.sql" -mtime +"$RETENTION_DAYS" -delete
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rotación local (> $RETENTION_DAYS días) OK." >> "$LOGFILE"

# ============================================================
# 5. Rotación de respaldos en WAVE
# ============================================================

if mountpoint -q "$WAVE_MOUNT"; then
    find "$WAVE_BACKUP_DIR" -type f -name "*.sql" -mtime +"$RETENTION_DAYS" -delete
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rotación WAVE (> $RETENTION_DAYS días) OK." >> "$LOGFILE"
fi

# ============================================================
# 6. Rotación de log
# ============================================================

if [ -f "$LOGFILE" ]; then
    LOG_AGE_DAYS=$(( ( $(date +%s) - $(stat -c %Y "$LOGFILE") ) / 86400 ))
    if [ "$LOG_AGE_DAYS" -ge "$RETENTION_DAYS" ]; then
        mv "$LOGFILE" "$BACKUP_DIR/backup_$(date +'%Y-%m-%d').log"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log rotado." >> "$BACKUP_DIR/backup.log"
    fi
fi

# ============================================================
# FIN
# ============================================================

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ===== BACKUP SEMEFO FINALIZADO =====" >> "$LOGFILE"
echo "--------------------------------------------------------------" >> "$LOGFILE"

exit 0
