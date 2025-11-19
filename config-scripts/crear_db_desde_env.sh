#!/bin/bash

set -e

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
echo "🗄️ Creando base de datos '${DB_NAME}' y usuario '${USER_NAME}'...".
echo "============================================================"

# 👉 Conectar a la DB correcta para evitar error "database does not exist"
docker exec -i postgres_db psql -U ${DB_USER} -d ${DB_NAME} <<EOF

DO \$\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_roles WHERE rolname = '${USER_NAME}'
   ) THEN
      CREATE ROLE ${USER_NAME} WITH LOGIN PASSWORD '${USER_PASS}' CREATEDB;
   END IF;
END
\$\$;

EOF

echo "============================================================"
echo "💾 Configurando permisos..."
echo "============================================================"

docker exec -i postgres_db psql -U ${USER_NAME} -d ${DB_NAME} <<EOF
GRANT ALL ON SCHEMA public TO ${USER_NAME};
ALTER SCHEMA public OWNER TO ${USER_NAME};
EOF

echo "============================================================"
echo "✅ Base de datos y usuario listos."
echo "============================================================"
