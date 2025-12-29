
INSERT INTO planchas (
  id,
  nombre,
  camara1_ip,
  camara1_id,
  camara1_activa,
  camara2_ip,
  camara2_id,
  camara2_activa,
  activo,
  asignada
)
VALUES
(
  1, 'Plancha 1',
  '172.21.82.120'::inet, '80ad645c-8506-bab2-422d-4a24bb181530', TRUE,
  '172.21.82.241'::inet, 'e4:30:22:a2:6e:fd', TRUE,
  TRUE, FALSE
),
(
  2, 'Plancha 2',
  '172.21.82.122'::inet, '84ca2514-1028-5255-ae65-c2895d2556e7', TRUE,
  '172.21.82.237'::inet, 'e4:30:22:a0:85:71', TRUE,
  TRUE, FALSE
),
(
  3, 'Plancha 3',
  '172.21.82.126'::inet, 'ef4b03d1-4dc8-0931-69fb-bd6638ac5813', TRUE,
  '172.21.82.235'::inet, 'e4:30:22:a2:6e:e0', TRUE,
  TRUE, FALSE
),
(
  4, 'Plancha 4',
  '172.21.82.124'::inet, '95e26609-c788-9364-46dc-4cbfc9f9f501', TRUE,
  '172.21.82.234'::inet, 'e4:30:22:a0:85:6f', TRUE,
  TRUE, FALSE
),
(
  5, 'Plancha 5',
  NULL, NULL, TRUE,
  '172.21.82.236'::inet, 'e4:30:22:a2:6e:e2', TRUE,
  TRUE, FALSE
),
(
  6, 'Plancha 6',
  '172.21.82.121'::inet, '5c1b8c9b-3c94-700a-2cce-321cd00a39a0', TRUE,
  '172.21.82.238'::inet, 'e4:30:22:a2:98:c0', TRUE,
  TRUE, FALSE
),
(
  8, 'Plancha 8',
  '172.21.82.125'::inet, 'd83faba3-b1b4-9cec-f999-fb2c9dc6e809', TRUE,
  NULL, 'Hanwha', TRUE,
  TRUE, FALSE
)
ON CONFLICT (id) DO UPDATE SET
  nombre = EXCLUDED.nombre,
  camara1_ip = EXCLUDED.camara1_ip,
  camara1_id = EXCLUDED.camara1_id,
  camara1_activa = EXCLUDED.camara1_activa,
  camara2_ip = EXCLUDED.camara2_ip,
  camara2_id = EXCLUDED.camara2_id,
  camara2_activa = EXCLUDED.camara2_activa,
  activo = EXCLUDED.activo,
  asignada = EXCLUDED.asignada;

/***************************************/
docker compose exec db psql -U semefo_user -d semefo

ALTER TABLE sesiones
ADD COLUMN duracion_real FLOAT;
ALTER TYPE tipo_archivo_enum
ADD VALUE IF NOT EXISTS 'manifest';
CREATE TABLE infra_estado (
    id SERIAL PRIMARY KEY,
    servidor VARCHAR(50) NOT NULL, -- master | whisper
    disco_total_gb DOUBLE PRECISION NOT NULL,
    disco_usado_gb DOUBLE PRECISION NOT NULL,
    disco_libre_gb DOUBLE PRECISION NOT NULL,
    fecha TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_infra_estado_servidor_fecha
ON infra_estado (servidor, fecha DESC);

CREATE TABLE workers_heartbeat (
    id SERIAL PRIMARY KEY,
    worker VARCHAR(50) NOT NULL,
    host VARCHAR(100),
    queue VARCHAR(100),
    status VARCHAR(20),
    last_seen TIMESTAMPTZ NOT NULL,
    pid INTEGER
);

CREATE UNIQUE INDEX uq_worker_host
ON workers_heartbeat (worker, host);

/**/
docker exec -it fastapi_app python api_server/bootstrap_auth.py

/* instalar vue */
npm create vite@latest semefo-dashboard
# Framework: Vue
# Variant: TypeScript
cd semefo-dashboard
npm install
npm install axios vue-router
npm install vue-router@4
npm run dev
/* */
docker compose exec db psql -U semefo_user -d semefo
/* */
/*  pass: Admin123!*/
INSERT INTO dashboard_users (
    username,
    password_hash,
    roles,
    activo,
    failed_attempts,
    locked_until,
    last_login_at,
    created_at
)
VALUES (
    'admin',
    '$2b$12$YasYtckBgxd17iPrDvVHie9g5FUOKuQyagGcqFCmmZDwcfTI2jyyi',
    'dashboard_admin,dashboard_read',
    true,
    0,
    NULL,
    NULL,
    NOW()
);
