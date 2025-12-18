CREATE TABLE IF NOT EXISTS planchas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,

    camara1_ip INET,
    camara1_id VARCHAR(100),
    camara1_activa BOOLEAN DEFAULT TRUE,

    camara2_ip INET,
    camara2_id VARCHAR(100),
    camara2_activa BOOLEAN DEFAULT TRUE,

    fecha_registro TIMESTAMP DEFAULT NOW(),
    activo BOOLEAN DEFAULT TRUE,
    asignada BOOLEAN DEFAULT FALSE
);

ALTER TABLE sesiones
DROP COLUMN plancha_id;

ALTER TABLE sesiones
ADD COLUMN plancha_id INTEGER REFERENCES planchas(id),
ADD COLUMN plancha_nombre VARCHAR(255);


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
-- Plancha 1
(
  1,
  'Plancha 1',
  '172.21.82.120'::inet,
  '80ad645c-8506-bab2-422d-4a24bb181530',
  TRUE,
  '172.21.82.241'::inet,
  'e4:30:22:a2:6e:fd',
  TRUE,
  TRUE,
  FALSE
),

-- Plancha 2
(
  2,
  'Plancha 2',
  '172.21.82.122'::inet,
  '84ca2514-1028-5255-ae65-c2895d2556e7',
  TRUE,
  '172.21.82.237'::inet,
  'e4:30:22:a0:85:71',
  TRUE,
  TRUE,
  FALSE
),

-- Plancha 3 (IP corregida 172:21:82:235 → 172.21.82.235)
(
  3,
  'Plancha 3',
  '172.21.82.126'::inet,
  'ef4b03d1-4dc8-0931-69fb-bd6638ac5813',
  TRUE,
  '172.21.82.235'::inet,
  'e4:30:22:a2:6e:e0',
  TRUE,
  TRUE,
  FALSE
),

-- Plancha 4
(
  4,
  'Plancha 4',
  '172.21.82.124'::inet,
  '95e26609-c788-9364-46dc-4cbfc9f9f501',
  TRUE,
  '172.21.82.234'::inet,
  'e4:30:22:a0:85:6f',
  TRUE,
  TRUE,
  FALSE
),

-- Plancha 6
(
  6,
  'Plancha 6',
  '172.21.82.121'::inet,
  '5c1b8c9b-3c94-700a-2cce-321cd00a39a0',
  TRUE,
  '172.21.82.238'::inet,
  'e4:30:22:a2:98:c0',
  TRUE,
  TRUE,
  FALSE
),


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
