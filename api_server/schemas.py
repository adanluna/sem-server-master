from pydantic import Field
from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional
from datetime import datetime
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
    plancha_id: Optional[int] = None
    plancha_nombre: Optional[str] = None
    tablet_id: str
    estado: Optional[str] = "en_progreso"
    user_nombre: Optional[str] = None
    camara1_mac_address: Optional[str] = None
    camara2_mac_address: Optional[str] = None
    app_version: Optional[str] = None


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


class SesionArchivoEstadoUpdate(BaseModel):
    estado: str
    mensaje: Optional[str] = None
    fecha_finalizacion: Optional[bool] = False
    ruta_convertida: Optional[str] = None
    conversion_completa: Optional[bool] = None


class PausaBase(BaseModel):
    inicio: datetime
    fin: datetime
    duracion: float
    fuente: str  # "app" o "auto"


class PausaCreate(PausaBase):
    sesion_id: int


class PausaResponse(PausaBase):
    id: int
    sesion_id: int

    class Config:
        orm_mode = True


class InvestigacionResponse(BaseModel):
    id: int
    numero_expediente: str
    nombre_carpeta: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_creacion: datetime

    model_config = {
        "from_attributes": True
    }


class SesionResponse(BaseModel):
    id: int
    investigacion_id: int
    nombre_sesion: str
    usuario_ldap: str
    plancha_id: str
    tablet_id: str
    estado: str
    user_nombre: Optional[str]
    camara1_mac_address: Optional[str]
    camara2_mac_address: Optional[str]
    app_version: Optional[str]
    fecha: datetime

    class Config:
        from_attributes = True


class InfraEstadoCreate(BaseModel):
    servidor: str  # "master" | "whisper"
    disco_total_gb: float
    disco_usado_gb: float
    disco_libre_gb: float


# ======================================================
# Planchas
# ======================================================

class PlanchaBase(BaseModel):
    nombre: str

    camara1_ip: Optional[IPvAnyAddress] = None
    camara1_id: Optional[str] = None
    camara1_activa: bool = True

    camara2_ip: Optional[IPvAnyAddress] = None
    camara2_id: Optional[str] = None
    camara2_activa: bool = True

    activo: bool = True
    asignada: bool = False


# ======================================================
# Planchas Create
# ======================================================

class PlanchaCreate(PlanchaBase):
    pass


# ======================================================
# Planchas Update (parcial)
# ======================================================

class PlanchaUpdate(BaseModel):
    nombre: Optional[str] = None

    camara1_ip: Optional[IPvAnyAddress] = None
    camara1_id: Optional[str] = None
    camara1_activa: Optional[bool] = None

    camara2_ip: Optional[IPvAnyAddress] = None
    camara2_id: Optional[str] = None
    camara2_activa: Optional[bool] = None

    activo: Optional[bool] = None
    asignada: Optional[bool] = None


# ======================================================
# Planchas Response
# ======================================================

class PlanchaResponse(PlanchaBase):
    id: int
    fecha_registro: datetime

    class Config:
        from_attributes = True


class LDAPLoginRequest(BaseModel):
    username: str
    password: str
