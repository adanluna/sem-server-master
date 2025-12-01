#!/bin/bash
# ============================================================
#  Respaldo automático de la base de datos SEMEFO (Producción)
#  Autor: Adan Luna
#  Descripción:
#     - Genera respaldo PostgreSQL desde docker "postgres_db"
#     - Guarda en /opt/semefo/backups
#     - Replica una copia al Grabador Windows (SMB)
#     - Mantiene retención de 7 días en ambos lados
# ============================================================

# --- Configuración ---
BACKUP_DIR="/opt/semefo/backups"
SMB_BACKUP_DIR="/mnt/semefo/backups_db"   # Copia remota de seguridad
DB_CONTAINER="postgres_db"
DB_USER="semefo_user"
DB_NAME="semefo"
DATE=$(date +'%Y-%m-%d_%H-%M-%S')
FILE_NAME="semefo_backup_$DATE.sql"
LOCAL_FILE="$BACKUP_DIR/$FILE_NAME"
LOGFILE="$BACKUP_DIR/backup.log"

# --- Crear carpeta local si no existe ---
mkdir -p "$BACKUP_DIR"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Iniciando respaldo..." >> "$LOGFILE"

# ============================================================
# 1. Generar respaldo local con pg_dump
# ============================================================
if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then

    docker exec -t "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$LOCAL_FILE"

    if [ $? -eq 0 ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Respaldo local completado: $LOCAL_FILE" >> "$LOGFILE"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: Falló pg_dump." >> "$LOGFILE"
        rm -f "$LOCAL_FILE"
        exit 1
    fi

else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: contenedor $DB_CONTAINER no está corriendo." >> "$LOGFILE"
    exit 1
fi


# ============================================================
# 2. Copiar respaldo al Grabador Windows (SMB)
# ============================================================
if mount | grep -q "/mnt/semefo"; then
    mkdir -p "$SMB_BACKUP_DIR"

    cp "$LOCAL_FILE" "$SMB_BACKUP_DIR/$FILE_NAME"

    if [ $? -eq 0 ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Copia en grabador completada: $SMB_BACKUP_DIR/$FILE_NAME" >> "$LOGFILE"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: No se pudo copiar al grabador SMB." >> "$LOGFILE"
    fi
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ADVERTENCIA: /mnt/semefo NO está montado. No se hizo copia remota." >> "$LOGFILE"
fi


# ============================================================
# 3. Rotación de respaldos locales (7 días)
# ============================================================
find "$BACKUP_DIR" -type f -mtime +7 -name "*.sql" -delete
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Respaldos locales antiguos eliminados (>7 días)." >> "$LOGFILE"


# ============================================================
# 4. Rotación de respaldos en Grabador (solo si está montado)
# ============================================================
if mount | grep -q "/mnt/semefo"; then
    find "$SMB_BACKUP_DIR" -type f -mtime +7 -name "*.sql" -delete
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Respaldos remotos antiguos eliminados (>7 días)." >> "$LOGFILE"
fi


# ============================================================
# 5. Rotación del log cada 7 días
# ============================================================
if [ -f "$LOGFILE" ]; then
    LOG_MOD_TIME=$(stat -c %Y "$LOGFILE" 2>/dev/null)
    NOW_TIME=$(date +%s)
    LOG_AGE=$(( (NOW_TIME - LOG_MOD_TIME) / 86400 ))

    if [ "$LOG_AGE" -ge 7 ]; then
        mv "$LOGFILE" "$BACKUP_DIR/backup_$(date +'%Y-%m-%d').log"
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Log rotado." >> "$BACKUP_DIR/backup.log"
    fi
fi


echo "[$(date +'%Y-%m-%d %H:%M:%S')] Proceso finalizado exitosamente." >> "$LOGFILE"
echo "--------------------------------------------------------------" >> "$LOGFILE"
exit 0
