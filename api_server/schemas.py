# api_server/schemas.py
from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional, List
from datetime import datetime
from typing import Optional, Union


# ======================================================
# Investigaciones
# ======================================================
class InvestigacionCreate(BaseModel):
    numero_expediente: str
    nombre_carpeta: Optional[str] = None
    observaciones: Optional[str] = None


class InvestigacionUpdate(BaseModel):
    nombre_carpeta: Optional[str] = None
    observaciones: Optional[str] = None


class InvestigacionResponse(BaseModel):
    id: int
    numero_expediente: str
    nombre_carpeta: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_creacion: datetime

    model_config = {"from_attributes": True}


# ======================================================
# Sesiones / Archivos
# ======================================================
class SesionArchivoCreate(BaseModel):
    sesion_id: int
    tipo_archivo: str
    ruta_original: Optional[str] = None
    ruta_convertida: Optional[str] = None
    conversion_completa: Optional[bool] = False
    estado: Optional[str] = "pendiente"
    mensaje: Optional[str] = None
    fecha_finalizacion: Optional[datetime] = None


class SesionArchivoResponse(BaseModel):
    id: int
    sesion_id: int
    tipo_archivo: str
    ruta_original: Optional[str]
    ruta_convertida: Optional[str]
    conversion_completa: bool
    estado: str
    mensaje: Optional[str] = None
    fecha: datetime
    fecha_finalizacion: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SesionArchivoEstadoUpdate(BaseModel):
    estado: str
    mensaje: Optional[str] = None
    fecha_finalizacion: Optional[Union[datetime, bool]] = None
    ruta_convertida: Optional[str] = None
    conversion_completa: Optional[bool] = None


class SesionCreate(BaseModel):
    investigacion_id: int
    nombre_sesion: str
    observaciones: Optional[str] = None
    usuario_ldap: str
    plancha_id: Optional[int] = None
    plancha_nombre: Optional[str] = None
    tablet_id: str
    estado: Optional[str] = "procesando"
    user_nombre: Optional[str] = None
    camara1_mac_address: Optional[str] = None
    camara2_mac_address: Optional[str] = None
    app_version: Optional[str] = None


class SesionResponse(BaseModel):
    id: int
    investigacion_id: int
    nombre_sesion: str
    usuario_ldap: str
    plancha_id: Optional[int] = None
    tablet_id: str
    estado: str
    user_nombre: Optional[str] = None
    camara1_mac_address: Optional[str] = None
    camara2_mac_address: Optional[str] = None
    app_version: Optional[str] = None
    fecha: datetime
    duracion_real: Optional[float] = None

    model_config = {"from_attributes": True}


# ======================================================
# Jobs
# ======================================================
class JobCreate(BaseModel):
    numero_expediente: str
    id_sesion: int
    tipo: str = Field(...,
                      pattern="^(audio|audio2|video|video2|transcripcion|manifest)$")
    archivo: str
    estado: str = Field(default="pendiente")
    resultado: Optional[str] = None
    error: Optional[str] = None


class JobUpdate(BaseModel):
    estado: Optional[str] = None
    resultado: Optional[str] = None
    error: Optional[str] = None


# ======================================================
# Pausas
# ======================================================
class PausaBase(BaseModel):
    inicio: datetime
    fin: datetime
    duracion: float
    fuente: str  # "app" | "auto"


class PausaCreate(PausaBase):
    sesion_id: int


class PausaResponse(PausaBase):
    id: int
    sesion_id: int
    model_config = {"from_attributes": True}


# ======================================================
# Infra Estado
# ======================================================
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


class PlanchaCreate(PlanchaBase):
    pass


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


class PlanchaResponse(PlanchaBase):
    id: int
    fecha_registro: datetime
    model_config = {"from_attributes": True}


# ======================================================
# AUTH (App LDAP / Tokens / Service)
# ======================================================
class AuthLoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ServiceTokenRequest(BaseModel):
    client_id: str
    client_secret: str


# ======================================================
# DASHBOARD AUTH + CRUD usuarios
# ======================================================
class DashboardLoginRequest(BaseModel):
    username: str
    password: str


class DashboardUserCreate(BaseModel):
    username: str
    password: str
    roles: List[str] = ["dashboard_read"]
    activo: bool = True


class DashboardUserUpdate(BaseModel):
    password: Optional[str] = None
    roles: Optional[List[str]] = None
    activo: Optional[bool] = None


class DashboardUserResponse(BaseModel):
    id: int
    username: str
    roles: List[str]
    activo: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkerHeartbeat(BaseModel):
    worker: str            # transcripcion, audio, video, etc.
    host: str              # server-master | server-whisper
    queue: Optional[str] = None
    pid: Optional[int] = None
    status: str            # listening | processing
