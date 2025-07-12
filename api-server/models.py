from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Investigacion(Base):
    __tablename__ = "investigaciones"

    id = Column(Integer, primary_key=True)
    numero_expediente = Column(String(100), unique=True, nullable=False)
    nombre_carpeta = Column(String(255))
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    observaciones = Column(Text)

    sesiones = relationship(
        "Sesion", back_populates="investigacion", cascade="all, delete-orphan")


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
    user_nombre = Column(String(200), nullable=True)  # ✅ AGREGAR ESTA LÍNEA
    fecha = Column(DateTime, default=datetime.utcnow)

    investigacion = relationship("Investigacion", back_populates="sesiones")
    archivos = relationship(
        "SesionArchivo", back_populates="sesion", cascade="all, delete-orphan")


class SesionArchivo(Base):
    __tablename__ = "sesion_archivos"

    id = Column(Integer, primary_key=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id"), nullable=False)
    tipo_archivo = Column(String(50))
    ruta_original = Column(Text)
    ruta_convertida = Column(Text)
    conversion_completa = Column(Boolean, default=False)
    transcripcion_completa = Column(Boolean, default=False)

    sesion = relationship("Sesion", back_populates="archivos")


class LogEvento(Base):
    __tablename__ = "logs_eventos"

    id = Column(Integer, primary_key=True)
    tipo_evento = Column(String(100))
    descripcion = Column(Text)
    usuario_ldap = Column(String(255))
    fecha = Column(DateTime, default=datetime.utcnow)
