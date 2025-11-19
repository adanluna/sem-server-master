#!/bin/bash
# ============================================================
# 📘 Crear base de datos y usuario PostgreSQL usando variables del .env
# ============================================================

set -e

# Cargar .env
if [ -f "/opt/semefo/.env" ]; then
  export $(grep -v '^#' /opt/semefo/.env | xargs)
else
  echo "❌ ERROR: No se encontró /opt/semefo/.env"
  exit 1
fi

USER_NAME=${DB_USER:-semefo_user}
USER_PASS=${DB_PASS:-Semefo123$!}
DB_NAME=${DB_NAME:-semefo}

echo "============================================================"
echo "🗄️ Creando base de datos '${DB_NAME}' y usuario '${USER_NAME}'..."
echo "============================================================"

docker exec -i postgres_db psql -U ${DB_USER} <<EOF

-- Crear usuario si no existe
DO \$\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_roles WHERE rolname = '${USER_NAME}'
   ) THEN
      CREATE ROLE ${USER_NAME} WITH LOGIN PASSWORD '${USER_PASS}' CREATEDB;
   END IF;
END
\$\$;

-- Crear base si no existe
DO \$\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database WHERE datname = '${DB_NAME}'
   ) THEN
      CREATE DATABASE ${DB_NAME}
      WITH OWNER = ${USER_NAME}
      ENCODING = 'UTF8';
   END IF;
END
\$\$;

EOF

echo "============================================================"
echo "💾 Conectando a la base y configurando permisos..."
echo "============================================================"

docker exec -i postgres_db psql -U ${USER_NAME} -d ${DB_NAME} <<EOF
GRANT ALL ON SCHEMA public TO ${USER_NAME};
ALTER SCHEMA public OWNER TO ${USER_NAME};
EOF

echo "============================================================"
echo "✅ Base de datos y usuario creados correctamente."
echo "============================================================"
