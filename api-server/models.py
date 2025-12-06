from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


# ============================================================
#  📁 TABLA: Investigaciones
# ============================================================
class Investigacion(Base):
    __tablename__ = "investigaciones"

    id = Column(Integer, primary_key=True)
    numero_expediente = Column(String(100), unique=True, nullable=False)
    nombre_carpeta = Column(String(255))
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    observaciones = Column(Text)

    sesiones = relationship(
        "Sesion", back_populates="investigacion", cascade="all, delete-orphan"
    )
    jobs = relationship(
        "Job", back_populates="investigacion", cascade="all, delete-orphan"
    )


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
    plancha_id = Column(String(100), nullable=False)
    tablet_id = Column(String(100), nullable=False)
    estado = Column(String(50), nullable=False, default="en_progreso")
    user_nombre = Column(String(200), nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    camara1_mac_address = Column(String(100), nullable=True)
    camara2_mac_address = Column(String(100), nullable=True)
    app_version = Column(String(50), nullable=True)
    progreso_porcentaje = Column(Float, default=0)
    sha256 = Column(String, nullable=True)
    duracion_archivo_seg = Column(Float, nullable=True)
    duracion_sesion_seg = Column(Float, nullable=True)

    investigacion = relationship("Investigacion", back_populates="sesiones")
    archivos = relationship(
        "SesionArchivo", back_populates="sesion", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="sesion",
                        cascade="all, delete-orphan")


# ============================================================
#  🎬 TABLA: Archivos de sesión (audio, video, transcripción)
# ============================================================
class SesionArchivo(Base):
    __tablename__ = "sesion_archivos"

    id = Column(Integer, primary_key=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id"), nullable=False)
    # audio, video, audio2, video2, transcripcion
    tipo_archivo = Column(String(50), nullable=False)
    ruta_original = Column(Text)
    ruta_convertida = Column(Text)
    conversion_completa = Column(Boolean, default=False)
    estado = Column(String(50), default="pendiente")
    mensaje = Column(Text, nullable=True)
    fecha_finalizacion = Column(DateTime, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)

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
    fecha = Column(DateTime, default=datetime.utcnow)


# ============================================================
#  🧵 TABLA: Jobs (cola de tareas)
# ============================================================
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    investigacion_id = Column(Integer, ForeignKey(
        "investigaciones.id"), nullable=False)
    sesion_id = Column(Integer, ForeignKey("sesiones.id"), nullable=False)
    tipo = Column(String(50), nullable=False)  # audio, video, transcripcion
    archivo = Column(Text, nullable=False)

    # pendiente, procesando, completado, error
    estado = Column(String(50), default="pendiente")
    resultado = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    investigacion = relationship("Investigacion", back_populates="jobs")
    sesion = relationship("Sesion", back_populates="jobs")
# ============================================================


class LogPausa(Base):
    __tablename__ = "log_pausas"

    id = Column(Integer, primary_key=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"))
    inicio = Column(DateTime, nullable=False)
    fin = Column(DateTime, nullable=False)
    duracion = Column(Float, nullable=False)
    fuente = Column(String(20), nullable=False)  # "app" | "auto"
