from datetime import timedelta, datetime
from ldap3 import Server, Connection, NTLM, ALL
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, text
import logging
import os
from celery import chain
import requests
import socket
import shutil
import json
from pathlib import Path
from api_server.database import get_db, engine
from datetime import datetime, timezone
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
    PlanchaUpdate,
    PlanchaCreate
)

from models import LDAPLoginRequest

from worker.celery_app import celery_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

rabbit_user = os.getenv("RABBITMQ_USER")
rabbit_pass = os.getenv("RABBITMQ_PASS")
rabbit_host = os.getenv("RABBITMQ_HOST", "rabbitmq")

EXPEDIENTES_PATH = os.getenv(
    "EXPEDIENTES_PATH",
    "/mnt/wave/archivos_sistema_semefo"
).rstrip("/")

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
API_SERVER_URL = os.getenv("API_SERVER_URL", "localhost:8000")

if not GRABADOR_UUID:
    print("⚠ ADVERTENCIA: GRABADOR_UUID no definido en .env")


# ============================================================
#  RUTAS BÁSICAS
# ============================================================

def parse_hhmmss_to_seconds(hhmmss: str) -> float:
    partes = hhmmss.split(":")
    h, m, s = partes
    return int(h)*3600 + int(m)*60 + float(s)


@app.get("/")
async def root():
    return {"message": "SEMEFO API Server", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


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

    # Actualizar datos del archivo
    archivo.estado = data.estado

    if data.mensaje:
        archivo.mensaje = data.mensaje
    if data.fecha_finalizacion:
        archivo.fecha_finalizacion = datetime.now(timezone.utc)
    if data.ruta_convertida:
        archivo.ruta_convertida = data.ruta_convertida
    if data.conversion_completa is not None:
        archivo.conversion_completa = data.conversion_completa

    db.commit()

    # Disparar whisper cuando video principal termina
    if tipo == "video" and data.estado == "completado":
        try:
            sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
            expediente = sesion.investigacion.numero_expediente

            payload = {
                "sesion_id": sesion_id,
                "expediente": expediente
            }

            requests.post(
                f"{API_SERVER_URL}/whisper/enviar",
                json=payload,
                timeout=5
            )
        except:
            pass

    # Verificar si ya se completaron todos los archivos
    archivos = db.query(models.SesionArchivo).filter_by(
        sesion_id=sesion_id).all()

    completados = {
        a.tipo_archivo for a in archivos if a.estado == "completado"}

    requeridos = {"video", "video2", "audio", "transcripcion"}

    if requeridos.issubset(completados):
        sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()

        if sesion and sesion.estado != "finalizada":
            sesion.estado = "finalizada"
            sesion.duracion_real = (
                datetime.now(timezone.utc) - sesion.fecha).total_seconds()
            db.commit()
            print(f"[SESION] Sesión {sesion_id} FINALIZADA automáticamente")

    return {"message": f"Archivo {tipo} actualizado"}


# ============================================================
#  PROCESAR SESIÓN — MANIFEST + AUDIO + VIDEO
# ============================================================

@app.post("/procesar_sesion")
def procesar_sesion(payload: dict, db: Session = Depends(get_db)):

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

    if not sesion_obj:
        # Crear nueva sesión
        sesion_obj = models.Sesion(
            id=id_sesion,
            investigacion_id=1,
            nombre_sesion=ses.get("nombre", f"Sesion_{id_sesion}"),
            usuario_ldap=ses["forense"]["id_usuario"],
            user_nombre=ses["forense"]["nombre"],
            plancha_id=plancha_id,
            plancha_nombre=plancha_nombre,
            tablet_id=ses.get("tablet", "desconocida"),
            camara1_mac_address=cam1,
            camara2_mac_address=cam2,
            app_version=ses.get("version_app", "1.0.0"),

            # ESTADO FINALIZADA (tablet ya terminó)
            estado="finalizada",

            # Guardamos inicio y fin exactos
            inicio=inicio_dt,
            fin=fin_dt,

            # Duración real (no duración bruta)
            duracion_sesion_seg=duracion_real_seg
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
        sesion_obj.estado = "finalizada"

        # Guardamos inicio/fin reales SIEMPRE
        sesion_obj.inicio = inicio_dt
        sesion_obj.fin = fin_dt

        # Duración corregida
        sesion_obj.duracion_sesion_seg = duracion_real_seg

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
    chain(
        celery_app.signature("tasks.generar_manifest", args=[
                             cam1, fecha_solo], immutable=True),
        celery_app.signature("worker.tasks.unir_video", args=[
                             expediente, id_sesion, path_manifest1, inicio_iso, fin_iso], immutable=True)
    ).apply_async()

    chain(
        celery_app.signature("tasks.generar_manifest", args=[
                             cam2, fecha_solo], immutable=True),
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
#  JOBS (Usado por Workers)
# ============================================================

@app.post("/jobs/crear")
def crear_job(data: JobCreate, db: Session = Depends(get_db)):

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

        return {
            "job_id": job_existente.id,
            "reutilizado": True
        }

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
def actualizar_job_api(job_id: int, data: JobUpdate, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if data.estado is not None:
        job.estado = data.estado
    if data.resultado is not None:
        job.resultado = data.resultado
    if data.error is not None:
        job.error = data.error

    db.commit()
    db.refresh(job)

    return {"message": "Job actualizado", "job_id": job.id}


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
            archivo_real.ruta_convertida,
            tipo=j.tipo,
            expediente=expediente,
            sesion_id=sesion_id
        )

        salida.append({
            "id": None,  # No hay job asociado
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
        "jobs": sorted(
            salida,
            key=lambda x: x["fecha_creacion"] or datetime.min,
            reverse=True
        )
    }

# ============================================================
#  MONITOREO DE PROCESAMIENTO (DASHBOARD)
# ============================================================


@app.get("/jobs/en_progreso")
def jobs_en_progreso(db: Session = Depends(get_db)):
    jobs = (
        db.query(models.Job)
        .filter(models.Job.estado.in_(["pendiente", "procesando"]))
        .order_by(models.Job.fecha_creacion.desc())
        .all()
    )
    return jobs


@app.get("/jobs/errores")
def jobs_con_error(db: Session = Depends(get_db)):
    jobs = (
        db.query(models.Job)
        .filter(models.Job.estado == "error")
        .order_by(models.Job.fecha_creacion.desc())
        .all()
    )
    return jobs


@app.get("/jobs/ultimos/{limite}")
def ultimos_jobs(limite: int, db: Session = Depends(get_db)):
    jobs = (
        db.query(models.Job)
        .order_by(models.Job.fecha_creacion.desc())
        .limit(limite)
        .all()
    )
    return jobs


@app.get("/jobs/tipo/{tipo}")
def jobs_por_tipo(tipo: str, db: Session = Depends(get_db)):
    if tipo not in ["video", "video2", "audio", "audio2", "transcripcion"]:
        raise HTTPException(status_code=400, detail="Tipo inválido")

    jobs = (
        db.query(models.Job)
        .filter_by(tipo=tipo)
        .order_by(models.Job.fecha_creacion.desc())
        .all()
    )
    return jobs


@app.get("/sesiones/{sesion_id}/estatus_completo")
def estatus_completo_sesion(sesion_id: int, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    archivos = db.query(models.SesionArchivo).filter_by(
        sesion_id=sesion_id).all()
    jobs = db.query(models.Job).filter_by(sesion_id=sesion_id).all()

    return {
        "sesion": sesion,
        "archivos": archivos,
        "jobs": jobs
    }


@app.get("/procesos/activos")
def procesos_activos(db: Session = Depends(get_db)):
    sesiones = (
        db.query(models.Sesion)
        .filter(models.Sesion.estado.in_(["en_progreso", "grabando"]))
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
def enviar_a_whisper(data: dict):

    sesion_id = data.get("sesion_id")
    expediente = data.get("expediente")

    if not sesion_id or not expediente:
        raise HTTPException(status_code=400, detail="Datos incompletos")

    print(f"[WHISPER] Tarea recibida para sesión {sesion_id}")

    import pika
    import json
    credentials = pika.PlainCredentials(rabbit_user, rabbit_pass)

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
        body=json.dumps(data)
    )

    connection.close()

    return {"status": "whisper_job_enviado"}

# ============================================================
#  PROGRESO POR ARCHIVO (usado por workers)
# ============================================================


@app.put("/sesiones/{sesion_id}/progreso/{tipo_archivo}")
def actualizar_progreso(sesion_id: int, tipo_archivo: str, data: dict, db: Session = Depends(get_db)):

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
#  VERIFICAR SI LA SESIÓN YA PUEDE FINALIZARSE
# ============================================================


@app.get("/sesiones/{sesion_id}/verificar_finalizacion")
def verificar_finalizacion(sesion_id: int, db: Session = Depends(get_db)):

    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    archivos = db.query(models.SesionArchivo).filter_by(
        sesion_id=sesion_id).all()
    completados = {
        a.tipo_archivo for a in archivos if a.estado == "completado"}

    requeridos = {"video", "video2", "audio", "transcripcion"}

    if requeridos.issubset(completados):

        if sesion.estado != "finalizada":
            sesion.estado = "finalizada"
            sesion.duracion_real = (
                datetime.now(timezone.utc) - sesion.fecha).total_seconds()
            db.commit()

            print(
                f"[SESION] Sesión {sesion_id} FINALIZADA automáticamente por verificación externa")

        return {"status": "finalizada"}

    return {
        "status": "incompleta",
        "faltan": list(requeridos - completados)
    }


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


@app.post("/auth/ldap")
def auth_ldap(data: LDAPLoginRequest):
    result = ldap_authenticate(data.username, data.password)

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])

    return result


@app.get("/auth/ldap/userinfo/{username}")
def ldap_user_info(username: str):
    LDAP_HOST = os.getenv("LDAP_SERVER_IP", "192.168.115.8")
    LDAP_PORT = 389

    try:
        server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)
        conn = Connection(server, auto_bind=True)

        search_base = "DC=fiscalianl,DC=gob"
        conn.search(
            search_base,
            f"(sAMAccountName={username})",
            attributes=["userPrincipalName", "sAMAccountName", "displayName"]
        )

        if not conn.entries:
            return {"error": "Usuario no encontrado en LDAP"}

        entry = conn.entries[0]

        return {
            "username": username,
            "userPrincipalName": str(entry.userPrincipalName) if "userPrincipalName" in entry else None,
            "displayName": str(entry.displayName) if "displayName" in entry else None,
            "samAccountName": str(entry.sAMAccountName) if "sAMAccountName" in entry else None
        }

    except Exception as e:
        return {"error": str(e)}

    # ============================================================
#  LISTAR TODAS LAS PAUSAS (APP + AUTO) PARA PROCESAMIENTO
# ============================================================


@app.get("/sesiones/{sesion_id}/pausas_todas")
def obtener_pausas_todas(sesion_id: int, db: Session = Depends(get_db)):
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
# Consultas para semefo
# ============================================================


@app.get("/consultas/expedientes/{numero_expediente}")
def consulta_expediente(numero_expediente: str, db: Session = Depends(get_db)):

    inv = (
        db.query(models.Investigacion)
        .filter_by(numero_expediente=numero_expediente)
        .first()
    )

    if not inv:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")

    sesiones_out = []

    for s in inv.sesiones:
        archivos = []
        for a in s.archivos:
            size_kb = 0
            if a.ruta_convertida and os.path.exists(a.ruta_convertida):
                size_kb = round(os.path.getsize(
                    a.ruta_convertida) / 1024, 2)

            archivos.append({
                "tipo": a.tipo_archivo,
                "estado": a.estado,
                "tamano_kb": size_kb,
                "mensaje": a.mensaje
            })

        sesiones_out.append({
            "sesion_id": s.id,
            "fecha": s.fecha,
            "usuario_ldap": s.usuario_ldap,
            "estado": s.estado,
            "duracion_sesion_seg": s.duracion_sesion_seg,
            "archivos": archivos
        })

    return {
        "numero_expediente": inv.numero_expediente,
        "fecha_creacion": inv.fecha_creacion,
        "sesiones": sesiones_out
    }

# ==========================================================
# Dashboard Endpoints
# ============================================================


@app.get("/dashboard/expedientes")
def dashboard_expedientes(
    desde: datetime,
    hasta: datetime,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db)
):
    q = (
        db.query(
            models.Investigacion.numero_expediente,
            models.Investigacion.fecha_creacion,
            func.count(distinct(models.Sesion.id)).label("total_sesiones"),
            func.count(models.SesionArchivo.id).label("total_archivos"),
        )
        .outerjoin(models.Sesion, models.Sesion.investigacion_id == models.Investigacion.id)
        .outerjoin(models.SesionArchivo, models.SesionArchivo.sesion_id == models.Sesion.id)
        .filter(models.Investigacion.fecha_creacion.between(desde, hasta))
        .group_by(models.Investigacion.id)
        .order_by(models.Investigacion.fecha_creacion.desc())
    )

    total = q.count()
    data = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total
        },
        "data": [
            {
                "numero_expediente": r.numero_expediente,
                "fecha_creacion": r.fecha_creacion,
                "total_sesiones": r.total_sesiones,
                "total_archivos": r.total_archivos
            }
            for r in data
        ]
    }


@app.get("/dashboard/sesiones")
def dashboard_sesiones(
    desde: datetime,
    hasta: datetime,
    page: int = 1,
    per_page: int = 25,
    db: Session = Depends(get_db)
):
    q = (
        db.query(models.Sesion)
        .filter(models.Sesion.fecha.between(desde, hasta))
        .order_by(models.Sesion.fecha.desc())
    )

    total = q.count()
    sesiones = q.offset((page - 1) * per_page).limit(per_page).all()

    data = []
    for s in sesiones:
        jobs = (
            db.query(
                models.Job.estado,
                func.count(models.Job.id).label("total")
            )
            .filter(models.Job.sesion_id == s.id)
            .group_by(models.Job.estado)
            .all()
        )

        resumen_jobs = {j.estado: j.total for j in jobs}

        data.append({
            "sesion_id": s.id,
            "numero_expediente": s.investigacion.numero_expediente,
            "usuario_ldap": s.usuario_ldap,
            "fecha": s.fecha,
            "estado": s.estado,
            "duracion_sesion_seg": s.duracion_sesion_seg,
            "jobs": {
                "pendiente": resumen_jobs.get("pendiente", 0),
                "procesando": resumen_jobs.get("procesando", 0),
                "completado": resumen_jobs.get("completado", 0),
                "error": resumen_jobs.get("error", 0),
            }
        })

    return {
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total
        },
        "data": data
    }


@app.get("/dashboard/jobs")
def dashboard_jobs(
    estado: str,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db)
):
    q = (
        db.query(models.Job)
        .filter(models.Job.estado == estado)
        .order_by(models.Job.fecha_creacion.desc())
    )

    total = q.count()
    jobs = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total
        },
        "data": [
            {
                "job_id": j.id,
                "numero_expediente": j.investigacion.numero_expediente,
                "sesion_id": j.sesion_id,
                "tipo": j.tipo,
                "archivo": j.archivo,
                "estado": j.estado,
                "fecha_creacion": j.fecha_creacion,
                "error": j.error
            }
            for j in jobs
        ]
    }

# Obtener estado de la infraestructura


@app.post("/infra/estado")
def registrar_infra_estado(
    data: InfraEstadoCreate,
    db: Session = Depends(get_db)
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


@app.get("/dashboard/infra/estado")
def infra_estado_dashboard(db: Session = Depends(get_db)):
    estado = {
        "api": "ok",
        "db": "error",
        "rabbitmq": "error",
        "workers": {
            "video": "desconocido",
            "audio": "desconocido",
            "transcripcion": "desconocido"
        },
        "disco": {
            "master": None,
            "whisper": {
                "status": "sin_reporte"
            }
        }
    }

    # -------------------------------------------------
    # DB
    # -------------------------------------------------
    try:
        db.execute(text("SELECT 1"))
        estado["db"] = "ok"
    except Exception:
        estado["db"] = "error"

    # -------------------------------------------------
    # RabbitMQ (socket check)
    # -------------------------------------------------
    try:
        rabbit_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        rabbit_port = 5672
        sock = socket.create_connection((rabbit_host, rabbit_port), timeout=2)
        sock.close()
        estado["rabbitmq"] = "ok"
    except Exception:
        estado["rabbitmq"] = "error"

    # -------------------------------------------------
    # Workers (heurística por jobs recientes)
    # -------------------------------------------------
    try:
        limite = datetime.now(timezone.utc) - timedelta(minutes=10)

        jobs = (
            db.query(models.Job.tipo)
            .filter(models.Job.fecha_actualizacion >= limite)
            .all()
        )

        tipos_activos = {j.tipo for j in jobs}

        estado["workers"]["video"] = "activo" if "video" in tipos_activos else "inactivo"
        estado["workers"]["audio"] = "activo" if "audio" in tipos_activos else "inactivo"
        estado["workers"]["transcripcion"] = (
            "activo" if "transcripcion" in tipos_activos else "inactivo"
        )
    except Exception:
        pass

    # -------------------------------------------------
    # Disco MASTER (en vivo)
    # -------------------------------------------------
    try:
        total, used, free = shutil.disk_usage("/")
        estado["disco"]["master"] = {
            "total_gb": round(total / (1024 ** 3), 2),
            "usado_gb": round(used / (1024 ** 3), 2),
            "libre_gb": round(free / (1024 ** 3), 2)
        }
    except Exception:
        estado["disco"]["master"] = None

    # -------------------------------------------------
    # Disco WHISPER (desde BD)
    # -------------------------------------------------
    whisper = (
        db.query(models.InfraEstado)
        .filter(models.InfraEstado.servidor == "whisper")
        .order_by(models.InfraEstado.fecha.desc())
        .first()
    )

    if whisper:
        retraso = datetime.now(timezone.utc) - whisper.fecha

        estado["disco"]["whisper"] = {
            "total_gb": whisper.disco_total_gb,
            "usado_gb": whisper.disco_usado_gb,
            "libre_gb": whisper.disco_libre_gb,
            "fecha": whisper.fecha,
            "status": "stale" if retraso > timedelta(minutes=10) else "ok"
        }

    return estado
# ============================================================
#  PLANCHAS
# ============================================================


@app.post("/planchas/", response_model=PlanchaResponse, status_code=201)
def crear_plancha(data: PlanchaCreate, db: Session = Depends(get_db)):
    plancha = models.Plancha(**data.dict())

    db.add(plancha)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ya existe una plancha con ese nombre o datos inválidos"
        )

    db.refresh(plancha)
    return plancha


@app.get("/planchas/", response_model=list[PlanchaResponse])
def listar_planchas(
    incluir_inactivas: bool = True,
    db: Session = Depends(get_db)
):
    q = db.query(models.Plancha)

    if not incluir_inactivas:
        q = q.filter(models.Plancha.activo == True)

    return q.order_by(models.Plancha.nombre.asc()).all()


@app.get("/planchas/{plancha_id}", response_model=PlanchaResponse)
def obtener_plancha(plancha_id: int, db: Session = Depends(get_db)):
    plancha = (
        db.query(models.Plancha)
        .filter(models.Plancha.id == plancha_id)
        .first()
    )

    if not plancha:
        raise HTTPException(status_code=404, detail="Plancha no encontrada")

    return plancha


@app.put("/planchas/{plancha_id}", response_model=PlanchaResponse)
def actualizar_plancha(
    plancha_id: int,
    data: PlanchaUpdate,
    db: Session = Depends(get_db)
):
    plancha = (
        db.query(models.Plancha)
        .filter(models.Plancha.id == plancha_id)
        .first()
    )

    if not plancha:
        raise HTTPException(status_code=404, detail="Plancha no encontrada")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(plancha, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Error al actualizar la plancha"
        )

    db.refresh(plancha)
    return plancha


@app.delete("/planchas/{plancha_id}", status_code=204)
def desactivar_plancha(plancha_id: int, db: Session = Depends(get_db)):
    plancha = (
        db.query(models.Plancha)
        .filter(models.Plancha.id == plancha_id)
        .first()
    )

    if not plancha:
        raise HTTPException(status_code=404, detail="Plancha no encontrada")

    # 🔒 Borrado lógico (CRÍTICO PARA GOBIERNO)
    plancha.activo = False
    db.commit()


@app.get("/planchas/disponibles", response_model=list[PlanchaResponse])
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


@app.get("/infra/whisper/estado")
def estado_whisper():
    with open("/mnt/wave/infra/whisper_status.json") as f:
        return json.load(f)


def normalizar_ruta(
    path: str | None,
    *,
    tipo: str | None = None,
    expediente: str | None = None,
    sesion_id: int | None = None
) -> str | None:
    """
    Normaliza rutas según tipo de archivo SEMEFO
    """

    if not path:
        return None

    # -------------------------
    # AUDIO / TRANSCRIPCIÓN
    # -------------------------
    if tipo in ("audio", "transcripcion"):
        if expediente and sesion_id:
            archivo = os.path.basename(path)
            return f"{EXPEDIENTES_PATH}/{expediente}/{sesion_id}/{archivo}"

    # -------------------------
    # YA ES ABSOLUTA
    # -------------------------
    if path.startswith("/"):
        return path

    # -------------------------
    # RELATIVA → EXPEDIENTES
    # -------------------------
    return f"{EXPEDIENTES_PATH}/{path.lstrip('/')}"


def size_kb(path: str | None) -> float:
    """
    Calcula tamaño en KB de forma segura
    """
    if not path:
        return 0.0

    try:
        p = Path(path)
        if p.exists() and p.is_file():
            return round(p.stat().st_size / 1024, 2)
    except Exception:
        pass

    return 0.0


def ruta_red(path_abs: str | None) -> str | None:
    """
    Convierte ruta /mnt/wave/... → Wisenet_WAVE_Media/...
    """
    if not path_abs:
        return None

    if path_abs.startswith("/mnt/wave/"):
        return path_abs.replace("/mnt/wave/", "Wisenet_WAVE_Media/")

    return path_abs
