# api_server/models.py
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.sql import func

from pydantic import BaseModel

from api_server.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ============================================================
#  📁 TABLA: Investigaciones
# ============================================================
class Investigacion(Base):
    __tablename__ = "investigaciones"

    id = Column(Integer, primary_key=True)
    numero_expediente = Column(String(100), unique=True, nullable=False)
    nombre_carpeta = Column(String(255))
    fecha_creacion = Column(DateTime(timezone=True),
                            default=utcnow, nullable=False)
    observaciones = Column(Text)

    sesiones = relationship(
        "Sesion", back_populates="investigacion", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="investigacion",
                        cascade="all, delete-orphan")


# ============================================================
#  🎥 TABLA: Sesiones de investigación
# ============================================================
class Sesion(Base):
    __tablename__ = "sesiones"

    id = Column(Integer, primary_key=True, index=True)
    investigacion_id = Column(Integer, ForeignKey(
        "investigaciones.id"), nullable=False)

    nombre_sesion = Column(String(200), nullable=False)
    observaciones = Column(Text)

    usuario_ldap = Column(String(100), nullable=False)
    user_nombre = Column(String(200), nullable=True)

    plancha_id = Column(Integer, ForeignKey("planchas.id"))
    plancha_nombre = Column(String(255))

    tablet_id = Column(String(100), nullable=False)

    estado = Column(String(50), nullable=False, default="en_progreso")

    fecha = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    camara1_mac_address = Column(String(100), nullable=True)
    camara2_mac_address = Column(String(100), nullable=True)

    app_version = Column(String(50), nullable=True)
    progreso_porcentaje = Column(Float, default=0)

    inicio = Column(DateTime(timezone=True), nullable=True)
    fin = Column(DateTime(timezone=True), nullable=True)
    duracion_real = Column(Float, nullable=True)

    investigacion = relationship("Investigacion", back_populates="sesiones")
    archivos = relationship(
        "SesionArchivo", back_populates="sesion", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="sesion",
                        cascade="all, delete-orphan")


# ============================================================
#  🎬 TABLA: Archivos de sesión
# ============================================================
class SesionArchivo(Base):
    __tablename__ = "sesion_archivos"

    __table_args__ = (
        UniqueConstraint("sesion_id", "tipo_archivo",
                         name="uq_sesion_archivo"),
    )

    id = Column(Integer, primary_key=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id"), nullable=False)

    # audio, audio2, video, video2, transcripcion
    tipo_archivo = Column(String(50), nullable=False)

    ruta_original = Column(Text)
    ruta_convertida = Column(Text)

    conversion_completa = Column(Boolean, default=False)

    estado = Column(String(50), default="pendiente", nullable=False)
    mensaje = Column(Text, nullable=True)

    fecha_finalizacion = Column(DateTime(timezone=True), nullable=True)
    fecha = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    sesion = relationship("Sesion", back_populates="archivos")


# ============================================================
#  📚 TABLA: Logs de eventos del sistema
# ============================================================
class LogEvento(Base):
    __tablename__ = "logs_eventos"

    id = Column(Integer, primary_key=True, index=True)
    tipo_evento = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=False)

    usuario_ldap = Column(String(200), nullable=True)

    fecha = Column(DateTime(timezone=True), default=utcnow, nullable=False)


# ============================================================
#  🧵 TABLA: Jobs (cola de tareas)
# ============================================================
class Job(Base):
    __tablename__ = "jobs"

    __table_args__ = (
        # 🔒 UN SOLO JOB por sesión + tipo
        UniqueConstraint("sesion_id", "tipo", name="uq_jobs_sesion_tipo"),
    )

    id = Column(Integer, primary_key=True)

    investigacion_id = Column(Integer, ForeignKey(
        "investigaciones.id"), nullable=False)
    sesion_id = Column(Integer, ForeignKey("sesiones.id"), nullable=False)

    tipo = Column(String(50), nullable=False)
    archivo = Column(Text, nullable=False)

    # pendiente, procesando, completado, error
    estado = Column(String(50), default="pendiente", nullable=False)

    resultado = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    fecha_creacion = Column(DateTime(timezone=True),
                            default=utcnow, nullable=False)
    fecha_actualizacion = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    investigacion = relationship("Investigacion", back_populates="jobs")
    sesion = relationship("Sesion", back_populates="jobs")


# ============================================================
#  ⏸️ TABLA: Pausas
# ============================================================
class LogPausa(Base):
    __tablename__ = "log_pausas"

    id = Column(Integer, primary_key=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"))

    inicio = Column(DateTime(timezone=True), nullable=False)
    fin = Column(DateTime(timezone=True), nullable=False)

    duracion = Column(Float, nullable=False)
    fuente = Column(String(20), nullable=False)  # "app" | "auto"


# ============================================================
#  🏗️ TABLA: Infra Estado
# ============================================================
class InfraEstado(Base):
    __tablename__ = "infra_estado"

    id = Column(Integer, primary_key=True)
    servidor = Column(String(50), nullable=False)  # master | whisper
    disco_total_gb = Column(Float, nullable=False)
    disco_usado_gb = Column(Float, nullable=False)
    disco_libre_gb = Column(Float, nullable=False)

    fecha = Column(DateTime(timezone=True), default=utcnow,
                   index=True, nullable=False)


# ============================================================
#  🧱 TABLA: Planchas
# ============================================================
class Plancha(Base):
    __tablename__ = "planchas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)

    camara1_ip = Column(INET, nullable=True)
    camara1_id = Column(String(100), nullable=True)
    camara1_activa = Column(Boolean, default=True)

    camara2_ip = Column(INET, nullable=True)
    camara2_id = Column(String(100), nullable=True)
    camara2_activa = Column(Boolean, default=True)

    activo = Column(Boolean, default=True)
    asignada = Column(Boolean, default=False)

    fecha_registro = Column(DateTime(timezone=True),
                            server_default=func.now(), nullable=False)


# ============================================================
#  🔐 AUTH: Usuarios Dashboard (local)
# ============================================================
class DashboardUser(Base):
    __tablename__ = "dashboard_users"

    id = Column(Integer, primary_key=True)

    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # CSV simple: "dashboard_admin,dashboard_read"
    roles = Column(String(255), nullable=False, default="dashboard_read")

    activo = Column(Boolean, default=True, nullable=False)

    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    last_login_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True),
                        default=utcnow, nullable=False)


# ============================================================
#  🔐 AUTH: Service Clients (workers / integraciones)
# ============================================================
class ServiceClient(Base):
    __tablename__ = "service_clients"

    id = Column(Integer, primary_key=True)

    client_id = Column(String(120), unique=True, nullable=False)
    client_secret_hash = Column(String(255), nullable=False)

    # Ej: "worker" o "worker,integracion_read"
    roles = Column(String(255), nullable=False, default="worker")

    activo = Column(Boolean, default=True, nullable=False)

    # Opcional (si luego quieres allowlist):
    allowed_ips = Column(Text, nullable=True)

    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True),
                        default=utcnow, nullable=False)


# ============================================================
#  🔁 AUTH: Refresh Tokens (hash)
# ============================================================
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)

    # subject: "ldap:juan.perez" o "dash:admin"
    subject = Column(String(200), nullable=False, index=True)

    # ID del refresh (para rotación/revocación)
    jti = Column(String(120), unique=True, nullable=False)

    # hash del refresh token completo (no guardes el token raw)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)

    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Para relacionar rotaciones si quieres
    rotated_to_id = Column(Integer, ForeignKey(
        "refresh_tokens.id"), nullable=True)
    rotated_to = relationship("RefreshToken", remote_side=[id])

    created_at = Column(DateTime(timezone=True),
                        default=utcnow, nullable=False)

# ============================================================
#  ❤️ TABLA: Workers Heartbeat (salud real de workers)
# ============================================================


class WorkerHeartbeatModel(Base):
    __tablename__ = "workers_heartbeat"

    id = Column(Integer, primary_key=True)

    # Identidad del worker
    # audio | video | video2 | transcripcion | manifest
    worker = Column(String(50), nullable=False)
    # server-master | server-whisper
    host = Column(String(100), nullable=False)
    # nombre de cola RabbitMQ
    queue = Column(String(100), nullable=True)
    pid = Column(Integer, nullable=True)               # PID del proceso

    # Estado operativo
    status = Column(String(20), nullable=False)        # listening | processing

    # Última señal
    last_seen = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        index=True
    )

    __table_args__ = (
        UniqueConstraint("worker", "host", name="uq_worker_host"),
    )

# ============================================================
#  (Compat) Pydantic requests que hoy ya usas desde models.py
#  Recomendación: moverlos a schemas.py, pero los dejo para no romper imports
# ============================================================


class LDAPLoginRequest(BaseModel):
    username: str
    password: str


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ServiceTokenRequest(BaseModel):
    client_id: str
    client_secret: str
