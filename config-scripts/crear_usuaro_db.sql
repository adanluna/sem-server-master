-- Verificar si el usuario ya existe
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'semefo_user'
   ) THEN
      CREATE USER semefo_user WITH PASSWORD 'Claudia01$!';
   END IF;
END
$$;

-- Verificar si la base de datos ya existe
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database WHERE datname = 'semefo'
   ) THEN
      CREATE DATABASE semefo
          WITH OWNER = semefo_user
          ENCODING = 'UTF8'
          CONNECTION LIMIT = -1;
   END IF;
END
$$;

-- Conectarse a la base creada
\connect semefo

-- Dar permisos sobre el schema public
GRANT ALL ON SCHEMA public TO semefo_user;
ALTER SCHEMA public OWNER TO semefo_user;

-- Mostrar roles y bases como referencia
\du
\l
