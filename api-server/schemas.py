from pydantic import Field
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InvestigacionCreate(BaseModel):
    numero_expediente: str
    nombre_carpeta: Optional[str] = None
    observaciones: Optional[str] = None


class InvestigacionUpdate(BaseModel):
    nombre_carpeta: Optional[str] = None
    observaciones: Optional[str] = None


class SesionArchivoCreate(BaseModel):
    sesion_id: int
    tipo_archivo: str
    ruta_original: Optional[str] = None
    ruta_convertida: Optional[str] = None
    conversion_completa: Optional[bool] = False


class SesionCreate(BaseModel):
    investigacion_id: int
    nombre_sesion: str
    observaciones: Optional[str] = None
    usuario_ldap: str
    user_nombre: Optional[str] = None
    plancha_id: str
    tablet_id: str


class SesionArchivoResponse(BaseModel):
    id: int
    sesion_id: int
    tipo_archivo: str
    ruta_original: Optional[str]
    ruta_convertida: Optional[str]
    conversion_completa: bool
    fecha: datetime

    model_config = {
        "from_attributes": True
    }


class JobCreate(BaseModel):
    numero_expediente: str
    id_sesion: int
    tipo: str = Field(...,
                      pattern="^(audio|audio2|video|video2|transcripcion)$")
    archivo: str
    estado: str = Field(default="pendiente")
    resultado: Optional[str] = None
    error: Optional[str] = None


class JobUpdate(BaseModel):
    estado: Optional[str] = None
    resultado: Optional[str] = None
    error: Optional[str] = None


class SesionArchivoCreate(BaseModel):
    sesion_id: int
    tipo_archivo: str = Field(...,
                              pattern="^(audio|audio2|video|video2|transcripcion)$")
    ruta_original: Optional[str] = None
    ruta_convertida: Optional[str] = None
    conversion_completa: Optional[bool] = False


class SesionArchivoEstadoUpdate(BaseModel):
    estado: str
    mensaje: Optional[str] = None
    fecha_finalizacion: Optional[bool] = False
    ruta_convertida: Optional[str] = None
    conversion_completa: Optional[bool] = None
