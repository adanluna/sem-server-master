from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import os

from database import get_db, engine
import models
from schemas import (
    InvestigacionCreate,
    InvestigacionUpdate,
    SesionCreate,
    JobCreate,
    JobUpdate,
    SesionArchivoCreate,
    SesionArchivoResponse,
    SesionArchivoEstadoUpdate
)

from worker.celery_app import celery_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema Forense SEMEFO",
    description="API del Sistema Integral de Grabación y Gestión de Autopsias del Gobierno del Estado de Nuevo León.",
    version="1.0.0"
)

# ============================================================
#  VARIABLES GLOBALES
# ============================================================

SMB_ROOT = os.getenv("WINDOWS_WAVE_SHARE_MOUNT", "/mnt/wave").rstrip("/")
GRABADOR_UUID = os.getenv("WINDOWS_WAVE_UUID", "").strip()

if not GRABADOR_UUID:
    print("⚠ ADVERTENCIA: GRABADOR_UUID no definido en .env")


# ============================================================
#  RUTAS BÁSICAS
# ============================================================

@app.get("/")
async def root():
    return {"message": "SEMEFO API Server", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# ============================================================
#  INVESTIGACIONES
# ============================================================

@app.post("/investigaciones/", response_model=InvestigacionCreate)
def create_investigacion(invest: InvestigacionCreate, db: Session = Depends(get_db)):
    nueva = models.Investigacion(**invest.dict())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/investigaciones/")
def list_investigaciones(db: Session = Depends(get_db)):
    return db.query(models.Investigacion).all()


@app.get("/investigaciones/{numero_expediente}", response_model=InvestigacionCreate)
def get_investigacion(numero_expediente: str, db: Session = Depends(get_db)):
    inv = db.query(models.Investigacion).filter_by(
        numero_expediente=numero_expediente).first()
    if not inv:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")
    return inv


@app.put("/investigaciones/{numero_expediente}", response_model=InvestigacionCreate)
def update_investigacion(numero_expediente: str, datos: InvestigacionUpdate, db: Session = Depends(get_db)):
    inv = db.query(models.Investigacion).filter_by(
        numero_expediente=numero_expediente).first()
    if not inv:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")

    if datos.nombre_carpeta is not None:
        inv.nombre_carpeta = datos.nombre_carpeta
    if datos.observaciones is not None:
        inv.observaciones = datos.observaciones

    db.commit()
    db.refresh(inv)
    return inv


# ============================================================
#  SESIONES
# ============================================================

@app.post("/sesiones/")
def crear_sesion(sesion_data: SesionCreate, db: Session = Depends(get_db)):
    investigacion = db.query(models.Investigacion).filter_by(
        id=sesion_data.investigacion_id).first()

    if not investigacion:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")

    nueva = models.Sesion(
        **sesion_data.dict(exclude_unset=True)
    )

    db.add(nueva)
    db.commit()
    db.refresh(nueva)

    log = models.LogEvento(
        tipo_evento="crear_sesion",
        descripcion=f"Sesión creada en plancha {nueva.plancha_id}, tablet {nueva.tablet_id}",
        usuario_ldap=nueva.usuario_ldap
    )
    db.add(log)
    db.commit()

    return nueva


@app.put("/sesiones/finalizar/{sesion_id}")
def finalizar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()

    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if sesion.estado != "en_progreso":
        return {"message": "Sesión ya está finalizada o cerrada"}

    sesion.estado = "finalizada"
    db.commit()

    log = models.LogEvento(
        tipo_evento="finalizar_sesion",
        descripcion=f"Sesión {sesion_id} finalizada",
        usuario_ldap=sesion.usuario_ldap
    )
    db.add(log)
    db.commit()

    return {"message": "Sesión finalizada exitosamente"}


# ============================================================
#  ARCHIVOS
# ============================================================

@app.post("/archivos/", response_model=SesionArchivoResponse)
def registrar_archivo(data: SesionArchivoCreate, db: Session = Depends(get_db)):
    archivo = models.SesionArchivo(**data.dict())
    db.add(archivo)
    db.commit()
    db.refresh(archivo)
    return archivo


@app.get("/sesiones/{sesion_id}/archivos", response_model=list[SesionArchivoResponse])
def listar_archivos(sesion_id: int, db: Session = Depends(get_db)):
    return db.query(models.SesionArchivo).filter_by(sesion_id=sesion_id).all() or []


@app.put("/archivos/{sesion_id}/{tipo}/actualizar_estado")
def actualizar_estado(sesion_id: int, tipo: str, data: SesionArchivoEstadoUpdate, db: Session = Depends(get_db)):
    archivo = db.query(models.SesionArchivo).filter_by(
        sesion_id=sesion_id, tipo_archivo=tipo).first()

    if not archivo:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    archivo.estado = data.estado

    if data.mensaje:
        archivo.mensaje = data.mensaje
    if data.fecha_finalizacion:
        archivo.fecha_finalizacion = datetime.utcnow()
    if data.ruta_convertida:
        archivo.ruta_convertida = data.ruta_convertida
    if data.conversion_completa is not None:
        archivo.conversion_completa = data.conversion_completa

    db.commit()
    return {"message": f"Archivo {tipo} actualizado"}


# ============================================================
#  PROCESAR SESIÓN — MANIFEST + AUDIO + VIDEO
# ============================================================

@app.post("/procesar_sesion")
def procesar_sesion(payload: dict, db: Session = Depends(get_db)):

    numero_expediente = payload.get("numero_expediente")
    id_sesion = payload.get("id_sesion")
    cam1 = payload.get("camara1_mac_address")
    cam2 = payload.get("camara2_mac_address")

    if not numero_expediente or not id_sesion:
        raise HTTPException(
            status_code=400, detail="Faltan parámetros obligatorios")

    if not cam1 or not cam2:
        raise HTTPException(status_code=400, detail="Faltan MAC addresses")

    hoy = datetime.now().strftime("%Y-%m-%d")

    # ====== MANIFEST PARA CAM1 ======
    celery_app.send_task(
        "tasks.generar_manifest",
        args=[cam1, hoy],
        queue="manifest"
    )

    # ====== MANIFEST PARA CAM2 ======
    celery_app.send_task(
        "tasks.generar_manifest",
        args=[cam2, hoy],
        queue="manifest"
    )

    # Rutas del manifest que tasks.py va a necesitar
    manifest1 = f"/mnt/wave/manifests/{GRABADOR_UUID}/{cam1}/{hoy[0:4]}/{hoy[5:7]}/{hoy[8:10]}/manifest.json"
    manifest2 = f"/mnt/wave/manifests/{GRABADOR_UUID}/{cam2}/{hoy[0:4]}/{hoy[5:7]}/{hoy[8:10]}/manifest.json"

    # ====== LANZAR WORKERS ======
    celery_app.send_task(
        "worker.tasks.unir_video",
        args=[numero_expediente, id_sesion, manifest1,
              hoy+"T00:00:00", hoy+"T23:59:59"],
        queue="uniones_video"
    )

    celery_app.send_task(
        "worker.tasks.unir_video2",
        args=[numero_expediente, id_sesion, manifest2,
              hoy+"T00:00:00", hoy+"T23:59:59"],
        queue="videos2"
    )

    return {
        "status": "procesando",
        "message": f"Procesando expediente {numero_expediente} sesión {id_sesion}",
        "manifest1": manifest1,
        "manifest2": manifest2
    }
