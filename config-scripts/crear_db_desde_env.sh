#!/bin/bash
# ============================================================
# 📘 Crear base de datos y usuario PostgreSQL usando variables del .env
# ============================================================

set -e  # detener si hay error

# Cargar variables desde el archivo .env
if [ -f "/opt/semefo/.env" ]; then
  export $(grep -v '^#' /opt/semefo/.env | xargs)
else
  echo "❌ ERROR: No se encontró /opt/semefo/.env"
  exit 1
fi

# Variables requeridas
USER_NAME=${DB_USER:-semefo_user}
USER_PASS=${DB_PASS:-Semefo123$!}
DB_NAME=${DB_NAME:-semefo}

echo "============================================================"
echo "🗄️ Creando base de datos '${DB_NAME}' y usuario '${USER_NAME}'..."
echo "============================================================"

# Ejecutar SQL dinámico
docker exec -i postgres_db psql -U postgres <<EOF
DO
\$\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = '${USER_NAME}'
   ) THEN
      CREATE USER ${USER_NAME} WITH PASSWORD '${USER_PASS}';
   END IF;
END
\$\$;

DO
\$\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database WHERE datname = '${DB_NAME}'
   ) THEN
      CREATE DATABASE ${DB_NAME}
          WITH OWNER = ${USER_NAME}
          ENCODING = 'UTF8'
          CONNECTION LIMIT = -1;
   END IF;
END
\$\$;

\\connect ${DB_NAME}

GRANT ALL ON SCHEMA public TO ${USER_NAME};
ALTER SCHEMA public OWNER TO ${USER_NAME};

EOF

echo "✅ Base de datos y usuario creados correctamente."
echo "============================================================"
