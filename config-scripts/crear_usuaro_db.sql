-- Crear usuario para SEMEFO
CREATE USER semefo_user WITH PASSWORD 'Claudia01$!';

-- Crear base de datos con ese propietario
CREATE DATABASE semefo
    WITH OWNER = semefo_user
    ENCODING = 'UTF8'
    CONNECTION LIMIT = -1;

-- Cambiar a esa base para dar permisos al schema public
\connect semefo

-- Dar permisos totales sobre el schema public
GRANT ALL ON SCHEMA public TO semefo_user;
ALTER SCHEMA public OWNER TO semefo_user;

-- Opcional: mostrar roles y bases al final
\du
\l
