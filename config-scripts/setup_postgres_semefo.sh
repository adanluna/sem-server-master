#!/bin/bash

# Variables
DB_NAME="semefo"
DB_USER="semefo_user"
DB_PASS="Claudia01$!"

echo "🔧 Instalando PostgreSQL (si no está instalado)..."
brew install postgresql || true
brew services start postgresql

echo "⏳ Esperando a que PostgreSQL arranque..."
sleep 5

# Crear usuario si no existe
if ! psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
    echo "👤 Creando usuario '${DB_USER}'..."
    createuser -s ${DB_USER}
    psql postgres -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
else
    echo "ℹ️ Usuario '${DB_USER}' ya existe."
fi

# Crear base de datos si no existe
if ! psql -lqt | cut -d \| -f 1 | grep -qw ${DB_NAME}; then
    echo "🗄️ Creando base de datos '${DB_NAME}'..."
    createdb -O ${DB_USER} ${DB_NAME}
else
    echo "ℹ️ La base de datos '${DB_NAME}' ya existe."
fi

# Otorgar privilegios por seguridad
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

echo "✅ Base de datos '${DB_NAME}' y usuario '${DB_USER}' están listos."
