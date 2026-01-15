from fastapi import Depends, HTTPException, Query
from ldap3 import Server, Connection, ALL, SIMPLE, NTLM
from datetime import datetime, timezone
from ldap3 import Server, Connection, NTLM, ALL
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import logging
import os
from celery import chain
import json
import socket
import traceback

# Imports internos
from api_server.database import get_db
from api_server import models
from api_server.schemas import (
    InvestigacionCreate,
    InvestigacionUpdate,
    SesionCreate,
    SesionResponse,
    JobCreate,
    JobUpdate,
    SesionArchivoCreate,
    SesionArchivoResponse,
    SesionArchivoEstadoUpdate,
    PausaCreate,
    PausaResponse,
    InfraEstadoCreate,
    PlanchaResponse,
)
from api_server.models import AuthLoginRequest, RefreshRequest, ServiceTokenRequest
from worker.celery_app import celery_app
from api_server.utils.ping import _ping_probe, _clamp_int
from api_server.utils.rutas import parse_hhmmss_to_seconds, normalizar_ruta, ruta_red, size_kb
from api_server.utils.jobs import crear_job_interno
from api_server.utils.jwt import create_access_token, create_refresh_token, _sha256, _now_utc, require_roles, pwd_context, ACCESS_TOKEN_MINUTES, REFRESH_TOKEN_HOURS, SERVICE_TOKEN_HOURS
from api_server.routers.dashboard import router as dashboard_router
from api_server.routers.apk import router as apk_router
from api_server.api_app import api_app

# Declaración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
#  VARIABLES GLOBALES
# ============================================================


TERMINALES = {"completado", "error"}
ARCHIVOS_JOB_TIPOS = {"audio", "audio2", "video",
                      "video2", "manifesto", "transcripcion"}

EXPEDIENTES_PATH = os.getenv(
    "EXPEDIENTES_PATH",
    "/mnt/wave/archivos_sistema_semefo"
).rstrip("/")

app = FastAPI(
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # dashboard
        "http://127.0.0.1:3000",
        "http://172.21.82.2:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Agregar routers
app.include_router(dashboard_router)
app.include_router(apk_router)
app.mount("/api", api_app)

rabbit_user = os.getenv("RABBITMQ_USER")
rabbit_pass = os.getenv("RABBITMQ_PASS")
rabbit_host = os.getenv("RABBITMQ_HOST", "rabbitmq")

SMB_ROOT = os.getenv("WINDOWS_WAVE_SHARE_MOUNT", "/mnt/wave").rstrip("/")
GRABADOR_UUID = os.getenv("WINDOWS_WAVE_UUID", "").strip()
API_SERVER_URL = os.getenv("API_SERVER_URL", "http://localhost:8000").strip()

if not API_SERVER_URL.startswith("http"):
    API_SERVER_URL = f"http://{API_SERVER_URL}"

DASHBOARD_ACCESS_TOKEN_MINUTES = int(
    os.getenv("DASHBOARD_ACCESS_TOKEN_MINUTES", "30"))
DASHBOARD_REFRESH_TOKEN_DAYS = int(
    os.getenv("DASHBOARD_REFRESH_TOKEN_DAYS", "14"))

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
#  🔥 ENDPOINTS CRÍTICOS DE PROCESO (NO MOVER)
#  (Se mantiene exactamente igual el contenido, solo se reubica)
# ============================================================

# ============================================================
#  PROCESAR SESIÓN — MANIFEST + AUDIO + VIDEO
# ============================================================

def _now_utc():
    return datetime.now(timezone.utc)


@app.post("/procesar_sesion")
def procesar_sesion(payload: dict, db: Session = Depends(get_db), principal=Depends(require_roles("operador", "supervisor"))):

    if not isinstance(payload, dict):
        raise HTTPException(400, "Payload inválido")

    ses = payload.get("sesion_activa")
    if not ses:
        raise HTTPException(status_code=400, detail="Falta 'sesion_activa'")

    # ---------------------------------------------------------
    # CAMPOS DEL JSON
    # ---------------------------------------------------------
    expediente = ses.get("expediente")
    id_sesion = ses.get("id_sesion")
    cam1 = ses.get("camara1_mac_address")
    cam2 = ses.get("camara2_mac_address")
    duracion_total_str = ses.get("duracion_total")
    plancha_id = ses.get("plancha_id")
    plancha_nombre = ses.get("plancha_nombre")

    if not plancha_id or not plancha_nombre:
        raise HTTPException(
            status_code=400,
            detail="Falta plancha_id o plancha_nombre en sesion_activa"
        )

    if not expediente or not id_sesion:
        raise HTTPException(
            status_code=400, detail="Faltan expediente o id_sesion")

    if not cam1 or not cam2:
        raise HTTPException(status_code=400, detail="Faltan MAC addresses")

    # ---------------------------------------------------------
    # INICIO / FIN
    # ---------------------------------------------------------
    try:
        inicio_iso = ses["inicio"]
        fin_iso = ses["fin"]
        inicio_dt = datetime.fromisoformat(inicio_iso)
        fin_dt = datetime.fromisoformat(fin_iso)
    except:
        raise HTTPException(
            status_code=400, detail="Formato inválido de inicio/fin")

    # DURACIÓN REAL enviada por la app (HH:MM:SS → seg)
    duracion_real_seg = None
    if duracion_total_str:
        try:
            duracion_real_seg = parse_hhmmss_to_seconds(duracion_total_str)
        except:
            print("[ERROR] No se pudo parsear duracion_total")
            duracion_real_seg = 0

    # ---------------------------------------------------------
    # OBTENER O CREAR SESIÓN
    # ---------------------------------------------------------
    sesion_obj = db.query(models.Sesion).filter_by(id=id_sesion).first()

    if sesion_obj:
        investigacion = sesion_obj.investigacion
    else:
        investigacion = (
            db.query(models.Investigacion)
            .filter_by(numero_expediente=expediente)
            .first()
        )
        if not investigacion:
            raise HTTPException(404, "Investigación no encontrada")

    if not sesion_obj:
        # Crear nueva sesión
        sesion_obj = models.Sesion(
            id=id_sesion,
            investigacion_id=investigacion.id,
            nombre_sesion=ses.get("nombre", f"Sesion_{id_sesion}"),
            usuario_ldap=ses["forense"]["id_usuario"],
            user_nombre=ses["forense"]["nombre"],
            plancha_id=plancha_id,
            plancha_nombre=plancha_nombre,
            tablet_id=ses.get("tablet", "desconocida"),
            camara1_mac_address=cam1,
            camara2_mac_address=cam2,
            app_version=ses.get("version_app", "1.0.0"),
            estado="procesando",
            fecha=inicio_dt,
            inicio=inicio_dt,
            fin=fin_dt,
            duracion_real=float(
                duracion_real_seg) if duracion_real_seg is not None else None
        )

        db.add(sesion_obj)
        db.commit()
        db.refresh(sesion_obj)
        print(f"[SESION] Creada sesión {id_sesion}")

    else:
        # Si ya existe, actualizamos datos
        print(f"[SESION] Sesión {id_sesion} existente → actualizando")

        sesion_obj.plancha_id = plancha_id
        sesion_obj.plancha_nombre = plancha_nombre
        sesion_obj.camara1_mac_address = cam1
        sesion_obj.camara2_mac_address = cam2
        sesion_obj.app_version = ses.get("version_app", "1.0.0")
        sesion_obj.estado = "procesando"

        # Guardamos inicio/fin reales SIEMPRE
        sesion_obj.inicio = inicio_dt
        sesion_obj.fin = fin_dt

        # Duración corregida
        sesion_obj.duracion_real = float(
            duracion_real_seg) if duracion_real_seg is not None else None

        db.commit()

    # ---------------------------------------------------------
    # GUARDAR PAUSAS DE LA APP
    # ---------------------------------------------------------
    pausas = ses.get("pausas", [])
    for p in pausas:
        try:
            inicio_p = datetime.fromisoformat(p["inicio"])
            fin_p = datetime.fromisoformat(p["fin"])
            dur = (fin_p - inicio_p).total_seconds()

            nueva = models.LogPausa(
                sesion_id=sesion_obj.id,
                inicio=inicio_p,
                fin=fin_p,
                duracion=dur,
                fuente="app"
            )
            db.add(nueva)
        except Exception as e:
            print(f"[PAUSAS] Error registrando pausa: {e}")

    db.commit()

    # ---------------------------------------------------------
    # PREPARAR MANIFESTS
    # ---------------------------------------------------------
    fecha_solo = inicio_iso.split("T")[0]
    yyyy, mm, dd = fecha_solo.split("-")

    path_manifest1 = f"/mnt/wave/manifests/{GRABADOR_UUID}/{cam1}/{yyyy}/{mm}/{dd}/manifest.json"
    path_manifest2 = f"/mnt/wave/manifests/{GRABADOR_UUID}/{cam2}/{yyyy}/{mm}/{dd}/manifest.json"

    # ---------------------------------------------------------
    # LANZAR WORKERS
    # ---------------------------------------------------------
    job_manifest1 = crear_job_interno(
        db=db,
        numero_expediente=expediente,
        sesion_id=id_sesion,
        tipo="manifest",
        archivo=f"manifests/{GRABADOR_UUID}/{cam1}/{yyyy}/{mm}/{dd}/manifest.json"
    )
    if not job_manifest1:
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar job de manifest para cámara 1"
        )
    job_manifest2 = crear_job_interno(
        db=db,
        numero_expediente=expediente,
        sesion_id=id_sesion,
        tipo="manifest",
        archivo=f"manifests/{GRABADOR_UUID}/{cam2}/{yyyy}/{mm}/{dd}/manifest.json"
    )
    if not job_manifest2:
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar job de manifest para cámara 2"
        )

    chain(
        celery_app.signature("tasks.generar_manifest", args=[
                             cam1, fecha_solo, job_manifest1], immutable=True),
        celery_app.signature("worker.tasks.unir_video", args=[
                             expediente, id_sesion, path_manifest1, inicio_iso, fin_iso], immutable=True)
    ).apply_async()

    chain(
        celery_app.signature("tasks.generar_manifest", args=[
                             cam2, fecha_solo, job_manifest2], immutable=True),
        celery_app.signature("worker.tasks.unir_video2", args=[
                             expediente, id_sesion, path_manifest2, inicio_iso, fin_iso], immutable=True)
    ).apply_async()

    # ---------------------------------------------------------
    # RESPUESTA
    # ---------------------------------------------------------
    return {
        "status": "procesando",
        "expediente": expediente,
        "id_sesion": id_sesion,
        "inicio_sesion": inicio_iso,
        "fin_sesion": fin_iso,
        "duracion_total_seg": duracion_real_seg,
        "pausas_app_registradas": len(pausas),
        "manifest1": path_manifest1,
        "manifest2": path_manifest2
    }


# ============================================================
#  ⚙️ APIS PARA WORKERS / PROCESAMIENTOS
# ============================================================

# ============================================================
#  ARCHIVOS (registro y cambios de estado)
# ============================================================

@app.post("/archivos/", response_model=SesionArchivoResponse)
def registrar_archivo(
    data: SesionArchivoCreate,
    db: Session = Depends(get_db),

):

    existente = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=data.sesion_id, tipo_archivo=data.tipo_archivo)
        .first()
    )

    # ✅ Si ya existe: actualizar (idempotente)
    if existente:
        if data.ruta_original is not None:
            existente.ruta_original = data.ruta_original
        if data.ruta_convertida is not None:
            existente.ruta_convertida = data.ruta_convertida
        if data.estado is not None:
            existente.estado = data.estado
        if data.mensaje is not None:
            existente.mensaje = data.mensaje
        if data.fecha_finalizacion is not None:
            existente.fecha_finalizacion = data.fecha_finalizacion
        if data.conversion_completa is not None:
            existente.conversion_completa = data.conversion_completa

        db.commit()
        db.refresh(existente)
        return existente

    archivo = models.SesionArchivo(**data.dict())
    db.add(archivo)
    db.commit()
    db.refresh(archivo)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # otro request lo creó primero → lo regresamos
        existente = (
            db.query(models.SesionArchivo)
            .filter_by(sesion_id=data.sesion_id, tipo_archivo=data.tipo_archivo)
            .first()
        )
        return existente

    db.refresh(archivo)
    return archivo

# Consultar archivos de una sesión usado por Whisper


@app.get("/sesiones/{sesion_id}/archivos")
def listar_archivos_sesion(sesion_id: int, db: Session = Depends(get_db)):
    ses = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not ses:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    archivos = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion_id)
        .order_by(models.SesionArchivo.id.asc())
        .all()
    )
    return archivos


@app.put("/archivos/{sesion_id}/{tipo}/actualizar_estado")
def actualizar_estado(
    sesion_id: int,
    tipo: str,
    data: SesionArchivoEstadoUpdate,
    db: Session = Depends(get_db),
):
    # -------------------------------------------------
    # 0. Upsert del archivo
    # -------------------------------------------------
    archivo = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion_id, tipo_archivo=tipo)
        .first()
    )

    if not archivo:
        archivo = models.SesionArchivo(
            sesion_id=sesion_id,
            tipo_archivo=tipo,
            ruta_original=data.ruta_original or data.ruta_convertida,
            ruta_convertida=data.ruta_convertida,
            estado=data.estado,
            mensaje=data.mensaje,
            fecha_finalizacion=(
                datetime.now(timezone.utc)
                if data.estado == "completado"
                else None
            ),
            conversion_completa=bool(data.conversion_completa),
        )
        db.add(archivo)
    else:
        archivo.estado = data.estado

        if data.mensaje is not None:
            archivo.mensaje = data.mensaje

        if data.ruta_convertida is not None:
            archivo.ruta_convertida = data.ruta_convertida

        if data.conversion_completa is not None:
            archivo.conversion_completa = data.conversion_completa

        if data.estado == "completado":
            archivo.fecha_finalizacion = datetime.now(timezone.utc)

    db.commit()

    # -------------------------------------------------
    # 1. Verificar ARCHIVOS requeridos
    # -------------------------------------------------
    ARCHIVOS_REQUERIDOS = {"video", "video2", "audio", "transcripcion"}

    archivos = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion_id)
        .all()
    )

    mapa = {a.tipo_archivo: a for a in archivos}

    # faltantes
    faltantes = [t for t in ARCHIVOS_REQUERIDOS if t not in mapa]
    if faltantes:
        return {
            "message": f"Archivo {tipo} actualizado (faltan: {faltantes})",
            "estado_sesion": "procesando",
        }

    # no completados
    no_completados = [
        t for t in ARCHIVOS_REQUERIDOS if mapa[t].estado != "completado"
    ]
    if no_completados:
        return {
            "message": f"Archivo {tipo} actualizado (incompletos: {no_completados})",
            "estado_sesion": "procesando",
        }

    # no convertidos
    no_convertidos = [
        t for t in ARCHIVOS_REQUERIDOS if not bool(mapa[t].conversion_completa)
    ]
    if no_convertidos:
        return {
            "message": f"Archivo {tipo} actualizado (sin convertir: {no_convertidos})",
            "estado_sesion": "procesando",
        }

    # -------------------------------------------------
    # 2. CIERRE FINAL DE SESIÓN (ÚNICO LUGAR)
    # -------------------------------------------------
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()

    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if sesion.estado != "finalizada":
        sesion.estado = "finalizada"
        db.commit()
        db.refresh(sesion)

    if sesion.duracion_real is None and sesion.inicio and sesion.fin:
        sesion.duracion_real = (sesion.fin - sesion.inicio).total_seconds()
        db.commit()

    return {
        "message": f"Archivo {tipo} actualizado",
        "estado_sesion": "finalizada",
    }

# ============================================================
#  PROGRESO POR ARCHIVO (usado por workers)
# ============================================================


@app.put("/sesiones/{sesion_id}/progreso/{tipo_archivo}")
def actualizar_progreso(sesion_id: int, tipo_archivo: str, data: dict, db: Session = Depends(get_db), ):

    progreso = data.get("progreso")
    if progreso is None:
        raise HTTPException(status_code=400, detail="Falta 'progreso'")

    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Guardar progreso general de la sesión
    sesion.progreso_porcentaje = progreso
    db.commit()

    print(f"[PROGRESO] Sesión {sesion_id} – {tipo_archivo}: {progreso}%")

    return {"message": "Progreso actualizado"}

# ============================================================
#  REGISTRAR PAUSAS DETECTADAS (Workers)
# ============================================================


@app.post("/sesiones/{sesion_id}/pausas_detectadas")
def registrar_pausas_detectadas(sesion_id: int, data: dict, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    pausas = data.get("pausas", [])
    count = 0

    for p in pausas:
        try:
            inicio = datetime.fromisoformat(p["inicio"])
            fin = datetime.fromisoformat(p["fin"])
            dur = float(p["duracion"])

            nueva = models.LogPausa(
                sesion_id=sesion_id,
                inicio=inicio,
                fin=fin,
                duracion=dur,
                fuente="auto"
            )
            db.add(nueva)
            count += 1
        except Exception as e:
            print(f"[PAUSA AUTO] Error: {e}")

    db.commit()

    return {"registradas": count}


# ============================================================
#  JOBS (Usado por Workers)
# ============================================================

@app.post("/jobs/crear")
def crear_job(data: JobCreate, db: Session = Depends(get_db), ):

    # 🔒 Buscar SIEMPRE el job por sesión + tipo
    job_existente = (
        db.query(models.Job)
        .filter_by(
            sesion_id=data.id_sesion,
            tipo=data.tipo
        )
        .first()
    )

    if job_existente:
        # 🔁 Resetear estado para reintento
        job_existente.estado = "pendiente"
        job_existente.error = None
        job_existente.resultado = None
        job_existente.fecha_actualizacion = datetime.now(timezone.utc)

        db.commit()
        db.refresh(job_existente)

        return {"job_id": job_existente.id, "reutilizado": True}

    # -------------------------------------------------
    # Crear SOLO si no existe
    # -------------------------------------------------
    investigacion = (
        db.query(models.Investigacion)
        .filter_by(numero_expediente=data.numero_expediente)
        .first()
    )

    if not investigacion:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")

    nuevo = models.Job(
        investigacion_id=investigacion.id,
        sesion_id=data.id_sesion,
        tipo=data.tipo,
        archivo=data.archivo,
        estado="pendiente"
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return {
        "job_id": nuevo.id,
        "creado": True
    }


@app.put("/jobs/{job_id}/actualizar")
def actualizar_job_api(
    job_id: int,
    data: JobUpdate,
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    try:
        # =========================
        # 1) Actualiza JOB
        # =========================
        if data.estado is not None:
            job.estado = data.estado
        if data.resultado is not None:
            job.resultado = data.resultado
        if data.error is not None:
            job.error = data.error

        # Si tu modelo Job tiene fecha_actualizacion, setéala
        if hasattr(job, "fecha_actualizacion"):
            job.fecha_actualizacion = _now_utc()

        # =========================
        # 2) Sincroniza SESION_ARCHIVOS
        #    Solo si es un tipo de archivo y estado terminal
        # =========================
        if (job.tipo in ARCHIVOS_JOB_TIPOS) and (job.estado in TERMINALES):
            sa = (
                db.query(models.SesionArchivo)
                .filter_by(sesion_id=job.sesion_id, tipo_archivo=job.tipo)
                .first()
            )

            if sa:
                sa.estado = job.estado

                # mensaje en error, limpio en completado
                if hasattr(sa, "mensaje"):
                    sa.mensaje = job.error if job.estado == "error" else None

                # fecha_finalizacion
                if hasattr(sa, "fecha_finalizacion"):
                    sa.fecha_finalizacion = _now_utc()

                # conversion_completa: true solo si completado
                if hasattr(sa, "conversion_completa"):
                    sa.conversion_completa = (job.estado == "completado")

                # ruta_convertida (si job.resultado trae path final y el campo existe)
                if job.resultado and hasattr(sa, "ruta_convertida"):
                    sa.ruta_convertida = job.resultado

            # Si NO existe SesionArchivo, NO lo creo aquí por defecto
            # para evitar “inventar evidencia”. Mejor que exista desde el registro inicial.
            # Si tú sí quieres autocrearlo, lo hacemos pero con reglas estrictas.

        db.commit()
        db.refresh(job)

        return {
            "message": "Job actualizado",
            "job_id": job.id,
            "sesion_id": job.sesion_id,
            "tipo": job.tipo,
            "estado": job.estado,
            "error": job.error,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al actualizar job: {str(e)}")

# ============================================================
#  🗂️ SEMEFO CORE (Investigaciones / Sesiones)
# ============================================================

# ============================================================
#  INVESTIGACIONES
# ============================================================


@app.post("/investigaciones/")
def crear_o_devolver_investigacion(data: InvestigacionCreate, db: Session = Depends(get_db)):
    existente = (
        db.query(models.Investigacion)
        .filter_by(numero_expediente=data.numero_expediente)
        .first()
    )

    if existente:
        return existente

    nueva = models.Investigacion(
        numero_expediente=data.numero_expediente,
        nombre_carpeta=None,
        observaciones=None,
        fecha_creacion=datetime.now()
    )

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


@app.post("/sesiones/", response_model=SesionResponse)
def crear_sesion(sesion_data: SesionCreate, db: Session = Depends(get_db)):

    investigacion = db.query(models.Investigacion).filter_by(
        id=sesion_data.investigacion_id
    ).first()

    if not investigacion:
        raise HTTPException(
            status_code=404, detail="Investigación no encontrada")

    nueva = models.Sesion(**sesion_data.dict(exclude_unset=True))
    db.add(nueva)
    db.commit()
    db.refresh(nueva)

    db.add(models.LogEvento(
        tipo_evento="crear_sesion",
        descripcion=f"Sesión creada en plancha {nueva.plancha_id}, tablet {nueva.tablet_id}",
        usuario_ldap=nueva.usuario_ldap
    ))
    db.commit()

    return nueva


# ============================================================
#  ⏸️ PAUSAS (manuales y lectura)
# ============================================================

# ============================================================
#  PAUSAS MANUALES
# ============================================================

@app.post("/sesiones/{sesion_id}/pausas", response_model=PausaResponse)
def registrar_pausa(sesion_id: int, data: PausaCreate, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    pausa = models.LogPausa(
        sesion_id=sesion_id,
        inicio=data.inicio,
        fin=data.fin,
        duracion=data.duracion,
        fuente=data.fuente
    )

    db.add(pausa)
    db.commit()
    db.refresh(pausa)
    return pausa


# ============================================================
#  LISTAR TODAS LAS PAUSAS (APP + AUTO) PARA PROCESAMIENTO
# ============================================================

@app.get("/sesiones/{sesion_id}/pausas_todas")
def obtener_pausas_todas(sesion_id: int, db: Session = Depends(get_db), ):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # ===========================
    # 🔥 AGREGAMOS INICIO Y FIN 🔥
    # ===========================
    inicio_sesion = None
    fin_sesion = None

    if sesion.inicio:
        inicio_sesion = sesion.inicio.isoformat()

    if sesion.fin:
        fin_sesion = sesion.fin.isoformat()

    # ===========================
    # PAUSAS
    # ===========================
    pausas_db = (
        db.query(models.LogPausa)
        .filter_by(sesion_id=sesion_id)
        .order_by(models.LogPausa.inicio.asc())
        .all()
    )

    pausas = []
    for p in pausas_db:
        pausas.append({
            "inicio": p.inicio.isoformat(),
            "fin": p.fin.isoformat(),
            "duracion": p.duracion,
            "fuente": p.fuente
        })

    return {
        "sesion_id": sesion_id,
        "inicio_sesion": inicio_sesion,
        "fin_sesion": fin_sesion,
        "total": len(pausas),
        "pausas": pausas
    }


# ============================================================
#  🔍 APIS PARA CONSULTA SEMEFO (lectura operacional)
# ============================================================

@app.get("/jobs/procesando")
def jobs_procesando(db: Session = Depends(get_db)):
    jobs = (
        db.query(models.Job)
        .filter(models.Job.estado.in_(["pendiente"]))
        .order_by(models.Job.fecha_creacion.desc())
        .all()
    )
    return jobs


@app.get("/sesiones/{sesion_id}/jobs")
def listar_jobs_sesion(sesion_id: int, db: Session = Depends(get_db)):

    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    expediente = sesion.investigacion.numero_expediente

    # ============================
    # JOBS (procesos)
    # ============================
    jobs = (
        db.query(models.Job)
        .filter_by(sesion_id=sesion_id)
        .order_by(models.Job.fecha_creacion.desc())
        .all()
    )

    # ============================
    # ARCHIVOS (evidencia real)
    # ============================
    archivos = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion_id)
        .all()
    )

    archivos_por_tipo = {a.tipo_archivo: a for a in archivos}

    salida = []

    # ============================
    # JOBS CON ARCHIVO
    # ============================
    for j in jobs:
        archivo_real = archivos_por_tipo.get(j.tipo)

        if archivo_real and archivo_real.ruta_convertida:
            ruta = normalizar_ruta(archivo_real.ruta_convertida)
        elif j.resultado:
            ruta = normalizar_ruta(j.resultado)
        else:
            ruta = normalizar_ruta(
                f"{expediente}/{sesion_id}/{j.archivo}"
            )

        salida.append({
            "id": j.id,
            "tipo": j.tipo,
            "archivo": j.archivo,
            "estado": j.estado,
            "error": j.error,
            "fecha_creacion": j.fecha_creacion,
            "fecha_actualizacion": j.fecha_actualizacion,
            "ruta": ruta,
            "ruta_red": ruta_red(ruta),
            "tamano_actual_KB": size_kb(ruta)
        })

    # ============================
    # ARCHIVOS SIN JOB (audio, etc.)
    # ============================
    tipos_con_job = {j["tipo"] for j in salida}

    for tipo, a in archivos_por_tipo.items():
        if tipo in tipos_con_job:
            continue

        ruta = normalizar_ruta(
            a.ruta_convertida,
            tipo=tipo,
            expediente=expediente,
            sesion_id=sesion_id
        )

        salida.append({
            "id": None,
            "tipo": tipo,
            "archivo": os.path.basename(a.ruta_convertida or ""),
            "estado": a.estado,
            "error": a.mensaje,
            "fecha_creacion": a.fecha,
            "fecha_actualizacion": a.fecha_finalizacion,
            "ruta": ruta,
            "tamano_actual_KB": size_kb(ruta)
        })

    return {
        "sesion_id": sesion_id,
        "expediente": expediente,
        "estado_sesion": sesion.estado,
        "nombre_sesion": sesion.nombre_sesion,
        "jobs": sorted(
            salida,
            key=lambda x: x["fecha_creacion"] or datetime.min,
            reverse=True
        )
    }


@app.get("/procesos/activos")
def procesos_activos(db: Session = Depends(get_db)):
    sesiones = (
        db.query(models.Sesion)
        .filter(models.Sesion.estado.in_(["procesando"]))
        .all()
    )

    output = []
    for ses in sesiones:
        jobs = (
            db.query(models.Job)
            .filter_by(sesion_id=ses.id)
            .order_by(models.Job.fecha_creacion.desc())
            .all()
        )
        archivos = (
            db.query(models.SesionArchivo)
            .filter_by(sesion_id=ses.id)
            .all()
        )

        output.append({
            "sesion_id": ses.id,
            "expediente": ses.investigacion.numero_expediente,
            "estado_sesion": ses.estado,
            "jobs": jobs,
            "archivos": archivos
        })

    return output

# ============================================================
#  LOGS FFMPEG
# ============================================================


@app.get("/procesos/ffmpeg_log/{sesion_id}")
def obtener_ffmpeg_log(sesion_id: int):

    logs_path = "/opt/semefo/logs"
    posibles = [
        f"{logs_path}/ffmpeg_video_{sesion_id}.log",
        f"{logs_path}/ffmpeg_video2_{sesion_id}.log"
    ]

    contenido = {}

    for path in posibles:
        if os.path.exists(path):
            with open(path, "r") as f:
                contenido[os.path.basename(path)] = f.read()

    if not contenido:
        raise HTTPException(
            status_code=404, detail="No hay logs para esta sesión")

    return contenido


# ============================================================
#  WHISPER — CORREGIDO: ruta_video ya no es obligatoria
# ============================================================

@app.post("/whisper/enviar")
def enviar_a_whisper(data: dict, ):

    sesion_id = data.get("sesion_id")
    expediente = data.get("expediente")

    if not sesion_id or not expediente:
        raise HTTPException(status_code=400, detail="Datos incompletos")

    if not rabbit_user or not rabbit_pass:
        raise HTTPException(500, "RabbitMQ credentials no configuradas")

    print(f"[WHISPER] Tarea recibida para sesión {sesion_id}")

    import pika
    import json
    credentials = pika.PlainCredentials(rabbit_user, rabbit_pass)

    if not rabbit_user or not rabbit_pass:
        raise HTTPException(500, "RabbitMQ credentials no configuradas")

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=rabbit_host,
            port=5672,
            virtual_host="/",
            credentials=credentials
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue="transcripciones", durable=True)

    channel.basic_publish(
        exchange="",
        routing_key="transcripciones",
        body=json.dumps(data),
        properties=pika.BasicProperties(delivery_mode=2)
    )

    connection.close()

    return {"status": "whisper_job_enviado"}


# ============================================================
#  AUTH / LDAP
# ============================================================


def ldap_authenticate(username: str, password: str):
    LDAP_HOST = os.getenv("LDAP_SERVER_IP", "192.168.115.8")
    LDAP_PORT = int(os.getenv("LDAP_PORT", 389))

    # ESTE ES EL UPN REAL DEL DOMINIO
    user_principal = f"{username}@fiscalianl.gob"

    try:
        server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)

        conn = Connection(
            server,
            user=user_principal,
            password=password,
            authentication="SIMPLE",
            auto_bind=False
        )

        # Intento de TLS (si el servidor lo soporta)
        try:
            conn.start_tls()
        except:
            pass

        if not conn.bind():
            return {"success": False, "message": "Credenciales inválidas"}

        # DefaultNamingContext detectado del servidor
        search_base = "DC=fiscalianl,DC=gob"

        conn.search(
            search_base,
            f"(sAMAccountName={username})",
            attributes=["displayName", "mail"]
        )

        info = {}
        if conn.entries:
            entry = conn.entries[0]
            info = {
                "displayName": str(entry.displayName) if "displayName" in entry else None,
                "mail": str(entry.mail) if "mail" in entry else None
            }

        conn.unbind()

        return {
            "success": True,
            "message": "Autenticación correcta",
            "user": {
                "username": username,
                **info
            }
        }

    except Exception as e:
        return {"success": False, "message": f"Error LDAP: {str(e)}"}


@app.post("/auth/login")
def auth_login(data: AuthLoginRequest, db: Session = Depends(get_db)):
    """Alias de /auth/ldap para compatibilidad"""
    result = ldap_authenticate(data.username, data.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])

    sub = f"ldap:{data.username}"
    roles = ["operador"]

    access = create_access_token(
        sub=sub, roles=roles, ttl_minutes=ACCESS_TOKEN_MINUTES)
    refresh, jti, token_hash, expires_at = create_refresh_token(
        sub=sub, roles=roles, ttl_hours=REFRESH_TOKEN_HOURS)

    rt = models.RefreshToken(
        subject=sub,
        jti=jti,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(rt)
    db.commit()

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user": result.get("user", {})
    }


@app.post("/auth/refresh")
def auth_refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    token = data.refresh_token.strip()
    token_hash = _sha256(token)

    row = (
        db.query(models.RefreshToken)
        .filter_by(token_hash=token_hash)
        .first()
    )
    if not row or row.revoked_at is not None:
        raise HTTPException(401, "Refresh inválido")

    if row.expires_at < _now_utc():
        raise HTTPException(401, "Refresh expirado")

    # ✅ permitir refresh para ldap y dash
    if not (row.subject.startswith("ldap:") or row.subject.startswith("dash:")):
        raise HTTPException(
            403, "Refresh no permitido para este tipo de usuario")

    # Rotación: revocar el actual y emitir uno nuevo
    sub = row.subject

    if sub.startswith("ldap:"):
        roles = ["operador"]
    else:
        roles = ["dashboard_read"]

    new_access = create_access_token(
        sub=sub, roles=roles, ttl_minutes=ACCESS_TOKEN_MINUTES
    )

    new_refresh, jti, th, exp = create_refresh_token(
        sub=sub, roles=roles, ttl_hours=REFRESH_TOKEN_HOURS
    )

    row.revoked_at = _now_utc()
    new_row = models.RefreshToken(
        subject=sub,
        jti=jti,
        token_hash=th,
        expires_at=exp
    )

    db.add(new_row)
    db.commit()

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }


@app.post("/auth/service-token")
def auth_service_token(data: ServiceTokenRequest, db: Session = Depends(get_db)):
    client = db.query(models.ServiceClient).filter_by(
        client_id=data.client_id, activo=True).first()
    if not client:
        raise HTTPException(401, "Cliente inválido")

    if not pwd_context.verify(data.client_secret, client.client_secret_hash):
        raise HTTPException(401, "Cliente inválido")

    sub = f"svc:{client.client_id}"
    roles = client.roles.split(",") if client.roles else ["worker"]

    access = create_access_token(
        sub=sub, roles=roles, ttl_minutes=SERVICE_TOKEN_HOURS * 60)

    client.last_used_at = _now_utc()
    db.commit()

    return {"access_token": access, "token_type": "bearer"}

# ============================================================
#  APP / Planchas
# ============================================================


@app.get("/planchas/disponibles", response_model=list[PlanchaResponse],)
def listar_planchas_disponibles(db: Session = Depends(get_db)):
    return (
        db.query(models.Plancha)
        .filter(
            models.Plancha.activo == True,
            models.Plancha.asignada == False
        )
        .order_by(models.Plancha.nombre.asc())
        .all()
    )

# ============================================================
#  🏗️ INFRAESTRUCTURA (reportes, estado, salud)
# ============================================================

# Obtener estado de la infraestructura


@app.post("/infra/estado")
def registrar_infra_estado(
    data: InfraEstadoCreate,
    db: Session = Depends(get_db),
    principal=Depends(require_roles("dashboard_admin"))
):
    nuevo = models.InfraEstado(**data.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return {
        "status": "ok",
        "id": nuevo.id
    }


@app.get("/infra/estado/ultimo")
def infra_estado_actual(db: Session = Depends(get_db)):
    rows = (
        db.query(models.InfraEstado)
        .order_by(models.InfraEstado.fecha.desc())
        .all()
    )

    resultado = {}
    for r in rows:
        if r.servidor not in resultado:
            resultado[r.servidor] = {
                "disco_total_gb": r.disco_total_gb,
                "disco_usado_gb": r.disco_usado_gb,
                "disco_libre_gb": r.disco_libre_gb,
                "fecha": r.fecha
            }

    return resultado


# ============================================================
#  APP / Status Camaras
# ============================================================

@app.get("/infra/whisper/estado")
def estado_whisper():
    if not os.path.exists("/mnt/wave/infra/whisper_status.json"):
        return {"status": "desconocido"}

    with open("/mnt/wave/infra/whisper_status.json") as f:
        return json.load(f)


@app.get("/infra/camaras/ping")
def ping_camara(ip: str):
    """
    Verifica si una cámara (o cualquier dispositivo) responde en red.
    """
    try:
        online = ping_camara(ip)

        return {
            "ip": ip,
            "online": online,
            "timestamp": datetime.now(timezone.utc)
        }

    except Exception as e:
        logger.error(f"[PING_CAMARA] Error con IP {ip}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al verificar conectividad de la cámara"
        )


# ============================================================
#   ENDPOINT — Estado general infraestructura (cámaras)
# ============================================================

@app.post("/infra/estado_general")
def estado_general_infraestructura(
    payload: dict,
    debug: bool = Query(
        False, description="Si true, incluye debug detallado (solo uso interno)."),
    timeout: int = Query(
        1, ge=1, le=3, description="Timeout por ping en segundos (1..3)."),
    retries: int = Query(
        2, ge=1, le=3, description="Reintentos de ping (1..3)."),
):
    """
    Recibe:
    {
      "camaras":[{"id":"camera1","ip":"172.21.82.121"}, ...]
    }

    Devuelve:
    - api.status = ok
    - camaras.total/online/offline/detalle
    - detalle incluye online/metodo y opcional debug si ?debug=1
    """

    camaras = payload.get("camaras", [])
    if not camaras:
        raise HTTPException(
            status_code=400, detail="Debe enviar una lista de cámaras")

    # Doble seguridad: clamp por si llegan valores raros (aunque Query ya valida)
    timeout = _clamp_int(timeout, 1, 3)
    retries = _clamp_int(retries, 1, 3)

    estado_camaras = []

    for cam in camaras:
        cam_id = cam.get("id")
        ip = cam.get("ip")
        if not cam_id or not ip:
            continue

        try:
            r = _ping_probe(ip, timeout=timeout, retries=retries)
        except Exception as e:
            # En producción, no exponemos traceback si debug=False
            err_debug = {"error": repr(e)}
            if debug:
                err_debug["traceback"] = traceback.format_exc()[:2000]

            r = {"online": False, "metodo": "exc", "debug": err_debug}

        item = {
            "id": cam_id,
            "ip": ip,
            "online": bool(r.get("online", False)),
            "metodo": r.get("metodo"),
        }

        if debug:
            item["debug"] = r.get("debug")

        estado_camaras.append(item)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api": {"status": "ok"},
        "camaras": {
            "total": len(estado_camaras),
            "online": sum(1 for c in estado_camaras if c["online"] is True),
            "offline": sum(1 for c in estado_camaras if c["online"] is False),
            "detalle": estado_camaras,
        },
    }


@app.post("/infra/heartbeat")
def worker_heartbeat(data: dict, db: Session = Depends(get_db)):
    """
    data = {
        worker: video | video2 | audio | transcripcion | manifest
        status: listening | processing
        pid: int
        queue: str | None
    }
    """

    host = socket.gethostname()

    hb = (
        db.query(models.WorkerHeartbeatModel)
        .filter_by(worker=data["worker"], host=host)
        .first()
    )

    if hb:
        hb.status = data["status"]
        hb.pid = data.get("pid")
        hb.queue = data.get("queue")
        hb.last_seen = datetime.now(timezone.utc)
    else:
        hb = models.WorkerHeartbeatModel(
            worker=data["worker"],
            host=host,
            queue=data.get("queue"),
            pid=data.get("pid"),
            status=data["status"],
            last_seen=datetime.now(timezone.utc),
        )
        db.add(hb)

    db.commit()

    return {"ok": True}
