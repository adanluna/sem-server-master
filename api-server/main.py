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

# SOLO debe importarse celery_app (no las funciones del worker)
from worker.celery_app import celery_app


# =============================
#  LOGGING Y CONFIG INICIAL
# =============================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema Forense SEMEFO",
    description="API del Sistema Integral de Grabación y Gestión de Autopsias del Gobierno del Estado de Nuevo León.",
    version="1.0.0",
    contact={"name": "Gobierno del Estado de Nuevo León",
             "url": "https://www.nl.gob.mx"},
    license_info={"name": "Privativo Fiscalía NL",
                  "url": "https://www.fiscalianl.gob.mx/"},
)


# =============================
#  RUTAS BÁSICAS
# =============================
@app.get("/")
async def root():
    return {"message": "SEMEFO API Server", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "API funcionando correctamente"}


# =============================
#   INVESTIGACIONES
# =============================
@app.post("/investigaciones/", response_model=InvestigacionCreate)
def create_investigacion(invest: InvestigacionCreate, db: Session = Depends(get_db)):
    nueva = models.Investigacion(
        numero_expediente=invest.numero_expediente,
        nombre_carpeta=invest.nombre_carpeta,
        observaciones=invest.observaciones
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/investigaciones/")
def list_investigaciones(db: Session = Depends(get_db)):
    return db.query(models.Investigacion).all()


@app.get("/investigaciones/{numero_expediente}", response_model=InvestigacionCreate)
def get_investigacion_by_expediente(numero_expediente: str, db: Session = Depends(get_db)):
    investigacion = db.query(models.Investigacion).filter_by(
        numero_expediente=numero_expediente).first()
    if not investigacion:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")
    return investigacion


@app.put("/investigaciones/{numero_expediente}", response_model=InvestigacionCreate)
def update_investigacion(numero_expediente: str, datos: InvestigacionUpdate, db: Session = Depends(get_db)):
    investigacion = db.query(models.Investigacion).filter_by(
        numero_expediente=numero_expediente).first()
    if not investigacion:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")

    if datos.nombre_carpeta is not None:
        investigacion.nombre_carpeta = datos.nombre_carpeta
    if datos.observaciones is not None:
        investigacion.observaciones = datos.observaciones

    db.commit()
    db.refresh(investigacion)
    return investigacion


# =============================
#   SESIONES
# =============================
@app.post("/sesiones/")
def crear_sesion(sesion_data: SesionCreate, db: Session = Depends(get_db)):
    try:
        # Validar referencia
        investigacion = db.query(models.Investigacion).filter(
            models.Investigacion.id == sesion_data.investigacion_id
        ).first()

        if not investigacion:
            raise HTTPException(
                status_code=404, detail=f"Investigación {sesion_data.investigacion_id} no encontrada")

        nueva_sesion = models.Sesion(
            investigacion_id=sesion_data.investigacion_id,
            nombre_sesion=sesion_data.nombre_sesion,
            observaciones=sesion_data.observaciones,
            usuario_ldap=sesion_data.usuario_ldap,
            plancha_id=sesion_data.plancha_id,
            tablet_id=sesion_data.tablet_id,
            estado=getattr(sesion_data, 'estado', 'en_progreso'),
            user_nombre=getattr(sesion_data, 'user_nombre',
                                sesion_data.usuario_ldap),
            camara1_mac_address=sesion_data.camara1_mac_address,
            camara2_mac_address=sesion_data.camara2_mac_address,
            app_version=sesion_data.app_version
        )

        db.add(nueva_sesion)
        db.commit()
        db.refresh(nueva_sesion)

        # Log de auditoría
        log = models.LogEvento(
            tipo_evento="crear_sesion",
            descripcion=f"Sesión creada en plancha {nueva_sesion.plancha_id}, tablet {nueva_sesion.tablet_id}",
            usuario_ldap=nueva_sesion.usuario_ldap
        )
        db.add(log)
        db.commit()

        return {
            "id": nueva_sesion.id,
            "investigacion_id": nueva_sesion.investigacion_id,
            "nombre_sesion": nueva_sesion.nombre_sesion,
            "observaciones": nueva_sesion.observaciones,
            "usuario_ldap": nueva_sesion.usuario_ldap,
            "plancha_id": nueva_sesion.plancha_id,
            "tablet_id": nueva_sesion.tablet_id,
            "estado": nueva_sesion.estado,
            "user_nombre": nueva_sesion.user_nombre,
            "camara1_mac_address": nueva_sesion.camara1_mac_address,
            "camara2_mac_address": nueva_sesion.camara2_mac_address,
            "app_version": nueva_sesion.app_version
        }

    except Exception as e:
        db.rollback()
        raise


@app.get("/sesiones/pendientes/{usuario_ldap}")
def get_sesion_pendiente(usuario_ldap: str, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(
        usuario_ldap=usuario_ldap, estado="en_progreso"
    ).first()

    if not sesion:
        return {"message": f"No hay sesiones pendientes para el usuario {usuario_ldap}"}

    return {
        "sesion_id": sesion.id,
        "investigacion_id": sesion.investigacion_id,
        "plancha_id": sesion.plancha_id,
        "tablet_id": sesion.tablet_id,
        "estado": sesion.estado
    }


@app.put("/sesiones/finalizar/{sesion_id}")
def finalizar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()

    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if sesion.estado != "en_progreso":
        return {"message": "La sesión ya está finalizada o cerrada."}

    sesion.estado = "finalizada"
    db.commit()
    db.refresh(sesion)

    log = models.LogEvento(
        tipo_evento="finalizar_sesion",
        descripcion=f"Sesión {sesion_id} finalizada",
        usuario_ldap=sesion.usuario_ldap
    )
    db.add(log)
    db.commit()

    return {"message": "Sesión finalizada exitosamente"}


# =============================
#   USUARIOS / PENDIENTES
# =============================
@app.get("/usuarios/{username}/sesion_pendiente")
def get_usuario_sesion_pendiente(username: str, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter(
        models.Sesion.usuario_ldap == username,
        models.Sesion.estado == "en_progreso"
    ).first()

    if not sesion:
        return {"pendiente": False}

    investigacion = db.query(models.Investigacion).filter(
        models.Investigacion.id == sesion.investigacion_id
    ).first()

    return {
        "pendiente": True,
        "tablet_id": sesion.tablet_id,
        "plancha_id": sesion.plancha_id,
        "numero_expediente": investigacion.numero_expediente if investigacion else None,
        "nombre_sesion": sesion.nombre_sesion,
        "id_sesion": sesion.id
    }


# =============================
#   ARCHIVOS
# =============================
@app.post("/archivos/", response_model=SesionArchivoResponse)
def registrar_archivo(data: SesionArchivoCreate, db: Session = Depends(get_db)):
    archivo = models.SesionArchivo(**data.dict())
    db.add(archivo)
    db.commit()
    db.refresh(archivo)
    return archivo


@app.get("/sesiones/{sesion_id}/archivos", response_model=list[SesionArchivoResponse])
def listar_archivos_por_sesion(sesion_id: int, db: Session = Depends(get_db)):
    return db.query(models.SesionArchivo).filter_by(sesion_id=sesion_id).all() or []


@app.put("/archivos/{sesion_id}/{tipo}/actualizar_estado")
def actualizar_estado_archivo(sesion_id: int, tipo: str, data: SesionArchivoEstadoUpdate, db: Session = Depends(get_db)):
    archivo = db.query(models.SesionArchivo).filter_by(
        sesion_id=sesion_id, tipo_archivo=tipo
    ).first()

    if not archivo:
        raise HTTPException(
            status_code=404, detail=f"No se encontró archivo {tipo}")

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
    db.refresh(archivo)

    return {"message": f"Archivo {tipo} actualizado a '{data.estado}'"}


# =============================
#   PROCESAR SESIÓN (MANIFEST + WORKERS)
# =============================
@app.post("/procesar_sesion")
def procesar_sesion(payload: dict, db: Session = Depends(get_db)):
    numero_expediente = payload.get("numero_expediente")
    id_sesion = payload.get("id_sesion")

    camera2_mac = payload.get("camera2_mac")
    wave_root = payload.get("wave_root")

    if not numero_expediente or not id_sesion:
        raise HTTPException(
            status_code=400, detail="Faltan parámetros obligatorios")

    if not camera2_mac or not wave_root:
        raise HTTPException(
            status_code=400, detail="Faltan parámetros de cámara 2")

    # Construcción de ruta del día
    now = datetime.now()
    ruta_dia = os.path.join(
        wave_root,
        f"({camera2_mac})",
        str(now.year),
        str(now.month).zfill(2),
        str(now.day).zfill(2)
    )

    # Log auditoría
    log = models.LogEvento(
        tipo_evento="generar_manifest",
        descripcion=f"Manifest solicitado para cámara2 {camera2_mac} en {ruta_dia}",
        usuario_ldap="sistema"
    )
    db.add(log)
    db.commit()

    # Disparar MANIFEST
    celery_app.send_task(
        "tasks.generar_manifest",
        args=[ruta_dia, camera2_mac],
        queue="manifest"
    )

    # Disparar workers de edición
    celery_app.send_task(
        "worker.tasks.unir_audio",
        args=[numero_expediente, id_sesion],
        queue="uniones_audio"
    )

    celery_app.send_task(
        "worker.tasks.unir_video",
        args=[numero_expediente, id_sesion],
        queue="uniones_video"
    )

    celery_app.send_task(
        "worker.tasks.unir_video2",
        args=[numero_expediente, id_sesion],
        queue="videos2"
    )

    return {
        "status": "procesando",
        "message": f"Procesamiento iniciado para expediente {numero_expediente}, sesión {id_sesion}. Consultar estatus posteriormente."
    }


@app.post("/logs")
def registrar_log(payload: dict, db: Session = Depends(get_db)):
    tipo = payload.get("tipo_evento")
    descripcion = payload.get("descripcion")
    usuario = payload.get("usuario_ldap", "system")

    if not tipo or not descripcion:
        raise HTTPException(status_code=400, detail="Faltan datos del log")

    log = models.LogEvento(
        tipo_evento=tipo,
        descripcion=descripcion,
        usuario_ldap=usuario
    )
    db.add(log)
    db.commit()

    return {"status": "ok", "message": "Log registrado"}
