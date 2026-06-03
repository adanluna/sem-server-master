-- Sesiones de aplicación (LDAP / tablet): un login activo por usuario operador.
CREATE TABLE IF NOT EXISTS app_user_sessions (
    id SERIAL PRIMARY KEY,
    usuario_ldap VARCHAR(255) NOT NULL,
    tablet_id VARCHAR(255) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'idle',
    sesion_id INTEGER NULL REFERENCES sesiones(id) ON DELETE SET NULL,
    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    logged_in_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ NULL,
    revoke_reason VARCHAR(50) NULL,
    revoked_by VARCHAR(255) NULL
);

CREATE INDEX IF NOT EXISTS ix_app_user_sessions_usuario
    ON app_user_sessions (usuario_ldap);

CREATE INDEX IF NOT EXISTS ix_app_user_sessions_heartbeat
    ON app_user_sessions (last_heartbeat_at);

CREATE INDEX IF NOT EXISTS ix_app_user_sessions_active
    ON app_user_sessions (usuario_ldap)
    WHERE revoked_at IS NULL;
