ALTER TABLE sesiones
ADD COLUMN camara1_mac_address VARCHAR(100);

ALTER TABLE sesiones
ADD COLUMN camara2_mac_address VARCHAR(100);

ALTER TABLE sesiones
ADD COLUMN app_version VARCHAR(50);