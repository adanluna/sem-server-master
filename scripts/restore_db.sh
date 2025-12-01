#!/bin/bash
# ============================================================
#  Restauración manual de base de datos SEMEFO
#  Autor: Adan Luna
#  Descripción:
#     - Restaura la base 'semefo' dentro del contenedor postgres_db
#     - Requiere archivo .sql local o en el grabador (/mnt/semefo/backups_db/)
#     - Pide confirmación antes de sobrescribir datos
# ============================================================

DB_CONTAINER="postgres_db"
DB_USER="semefo_user"
DB_NAME="semefo"

LOCAL_BACKUP_DIR="/opt/semefo/backups"
REMOTE_BACKUP_DIR="/mnt/semefo/backups_db"

echo "============================================================"
echo " Restauración de la base de datos SEMEFO"
echo "============================================================"
echo ""

# ============================================================
# Selección del archivo a restaurar
# ============================================================
echo "Seleccione origen del respaldo:"
echo " 1) Local ($LOCAL_BACKUP_DIR)"
echo " 2) Grabador SMB ($REMOTE_BACKUP_DIR)"
read -p "Opción: " ORIGEN

if [ "$ORIGEN" == "1" ]; then
    BACKUP_PATH="$LOCAL_BACKUP_DIR"
elif [ "$ORIGEN" == "2" ]; then
    if ! mount | grep -q "/mnt/semefo"; then
        echo "ERROR: El grabador no está montado en /mnt/semefo"
        exit 1
    fi
    BACKUP_PATH="$REMOTE_BACKUP_DIR"
else
    echo "Opción inválida"
    exit 1
fi

echo ""
echo "Buscando archivos .sql en: $BACKUP_PATH"
echo ""

# Mostrar lista de archivos de respaldo
select FILE in $(ls -t "$BACKUP_PATH"/*.sql 2>/dev/null); do
    if [ -n "$FILE" ]; then
        BACKUP_FILE="$FILE"
        break
    else
        echo "Selección inválida."
    fi
done

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: No se seleccionó un archivo válido."
    exit 1
fi

echo ""
echo "Archivo seleccionado:"
echo " $BACKUP_FILE"
echo ""

# ============================================================
# Confirmación antes de restaurar
# ============================================================
read -p "¿Seguro que deseas restaurar este respaldo? (y/n): " RESP

if [[ "$RESP" != "y" ]]; then
    echo "Restauración cancelada."
    exit 0
fi

# ============================================================
# Validar contenedor postgres
# ============================================================
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo "ERROR: El contenedor $DB_CONTAINER no está en ejecución."
    exit 1
fi

echo ""
echo "Deteniendo conexiones activas en PostgreSQL..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();
"

echo "Vaciando base de datos..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"

# ============================================================
# Restaurar
# ============================================================
echo ""
echo "Restaurando respaldo. Espere..."
cat "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo " Restauración completada correctamente"
    echo " Base restaurada: $DB_NAME"
    echo " Archivo usado: $BACKUP_FILE"
    echo "============================================================"
else
    echo "ERROR: Falló la restauración."
    exit 1
fi

exit 0
