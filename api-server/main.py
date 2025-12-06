from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import os
from celery import chain

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
    SesionArchivoEstadoUpdate,
    PausaCreate,
    PausaResponse
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
    ses = payload.get("sesion_activa")
    if not ses:
        raise HTTPException(status_code=400, detail="Falta 'sesion_activa'")

    expediente = ses.get("expediente")
    id_sesion = ses.get("id_sesion")
    cam1 = ses.get("camara1_mac_address")
    cam2 = ses.get("camara2_mac_address")

    if not expediente or not id_sesion:
        raise HTTPException(
            status_code=400, detail="Faltan expediente o id_sesion")

    if not cam1 or not cam2:
        raise HTTPException(status_code=400, detail="Faltan MAC addresses")

    # ============================================
    #  Convertir inicio/fin en datetime
    # ============================================
    try:
        inicio_iso = ses["inicio"]
        fin_iso = ses["fin"]
        inicio_dt = datetime.fromisoformat(inicio_iso)
        fin_dt = datetime.fromisoformat(fin_iso)
    except:
        raise HTTPException(
            status_code=400, detail="Formato inválido de inicio/fin")

    # ============================================
    #  Buscar si la sesión ya existe
    # ============================================
    sesion_obj = db.query(models.Sesion).filter_by(id=id_sesion).first()

    if not sesion_obj:
        # Crear la sesión — usando SOLO campos existentes en el modelo
        sesion_obj = models.Sesion(
            id=id_sesion,
            investigacion_id=1,   # ⚠️ DE MOMENTO HARDCODEADO — luego lo amarramos al expediente real
            nombre_sesion=ses.get("nombre", f"Sesion_{id_sesion}"),
            usuario_ldap=ses["forense"]["id_usuario"],
            plancha_id=ses.get("plancha", "desconocida"),
            tablet_id=ses.get("tablet", "desconocida"),
            estado="en_progreso",
            user_nombre=ses["forense"]["nombre"],
            camara1_mac_address=cam1,
            camara2_mac_address=cam2,
            app_version=ses.get("version_app", "1.0.0")
        )
        db.add(sesion_obj)
        db.commit()
        db.refresh(sesion_obj)

        print(f"[SESION] Creada sesión {id_sesion}")

    else:
        print(f"[SESION] Sesión {id_sesion} ya existía")

    # ============================================
    #  Registrar pausas de la APP (ahora sí existe la sesión)
    # ============================================
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
            print(f"[PAUSAS] Error guardando pausa APP: {e}")

    db.commit()

    # ============================================
    #   Construcción de rutas manifest
    # ============================================
    fecha_solo = inicio_iso.split("T")[0]
    yyyy, mm, dd = fecha_solo.split("-")

    path_manifest1 = f"/mnt/wave/manifests/{GRABADOR_UUID}/{cam1}/{yyyy}/{mm}/{dd}/manifest.json"
    path_manifest2 = f"/mnt/wave/manifests/{GRABADOR_UUID}/{cam2}/{yyyy}/{mm}/{dd}/manifest.json"

    # ============================================
    #   PROCESO COMPLETO: GENERAR MANIFEST → UNIR VIDEO
    # ============================================

    chain(
        celery_app.signature(
            "tasks.generar_manifest",
            args=[cam1, fecha_solo],
            immutable=True
        ),
        celery_app.signature(
            "worker.tasks.unir_video",
            args=[expediente, id_sesion, path_manifest1, inicio_iso, fin_iso],
            immutable=True
        )
    ).apply_async()

    chain(
        celery_app.signature(
            "tasks.generar_manifest",
            args=[cam2, fecha_solo],
            immutable=True
        ),
        celery_app.signature(
            "worker.tasks.unir_video2",
            args=[expediente, id_sesion, path_manifest2, inicio_iso, fin_iso],
            immutable=True
        )
    ).apply_async()

    return {
        "status": "procesando",
        "expediente": expediente,
        "id_sesion": id_sesion,
        "inicio_sesion": inicio_iso,
        "fin_sesion": fin_iso,
        "pausas_app_registradas": len(pausas),
        "manifest1": path_manifest1,
        "manifest2": path_manifest2
    }


@app.post("/sesiones/{sesion_id}/pausas_detectadas")
def registrar_pausas_detectadas(sesion_id: int, data: dict, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    nuevas = data.get("pausas", [])

    # Si ya existen pausas detectadas, las unimos
    previas = sesion.pausas_detectadas or []

    sesion.pausas_detectadas = previas + nuevas
    db.commit()

    return {"message": "Pausas registradas", "total": len(sesion.pausas_detectadas)}


@app.post("/sesiones/{sesion_id}/pausas", response_model=PausaResponse)
def registrar_pausa(sesion_id: int, data: PausaCreate, db: Session = Depends(get_db)):
    # Validar sesión
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


@app.post("/sesiones/{sesion_id}/pausas_auto")
def registrar_pausas_auto(sesion_id: int, data: dict, db: Session = Depends(get_db)):
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
            print(f"[PAUSA AUTO] Error procesando pausa: {e}")

    db.commit()

    return {"registradas": count}

# ============================================================
#  JOBS (Usado por Workers)
# ============================================================


@app.post("/jobs/crear")
def crear_job(data: JobCreate, db: Session = Depends(get_db)):
    # Buscar investigación mediante el número de expediente
    investigacion = db.query(models.Investigacion).filter_by(
        numero_expediente=data.numero_expediente
    ).first()

    if not investigacion:
        raise HTTPException(
            status_code=404,
            detail=f"Investigación '{data.numero_expediente}' no encontrada"
        )

    # Crear nuevo Job con valores por defecto
    nuevo = models.Job(
        investigacion_id=investigacion.id,
        sesion_id=data.id_sesion,
        tipo=data.tipo,
        archivo=data.archivo,
        estado=data.estado or "pendiente",
        resultado=data.resultado,
        error=data.error
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return {"job_id": nuevo.id}


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

# ============================================================
#  JOBS
# ============================================================


@app.get("/sesiones/{sesion_id}/jobs")
def listar_jobs_sesion(sesion_id: int, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    jobs = (
        db.query(models.Job)
        .filter_by(sesion_id=sesion_id)
        .order_by(models.Job.fecha_creacion.desc())
        .all()
    )

    return jobs

# ============================================================
#  MONITOREO DE PROCESAMIENTO (ENDPOINTS PARA DASHBOARD)
# ============================================================

# -------------------------------
# 1) Jobs en progreso
# -------------------------------


@app.get("/jobs/en_progreso")
def jobs_en_progreso(db: Session = Depends(get_db)):
    jobs = (
        db.query(models.Job)
        .filter(models.Job.estado.in_(["pendiente", "procesando"]))
        .order_by(models.Job.fecha_creacion.desc())
        .all()
    )
    return jobs


# -------------------------------
# 2) Jobs fallados
# -------------------------------
@app.get("/jobs/errores")
def jobs_con_error(db: Session = Depends(get_db)):
    jobs = (
        db.query(models.Job)
        .filter(models.Job.estado == "error")
        .order_by(models.Job.fecha_creacion.desc())
        .all()
    )
    return jobs


# -------------------------------
# 3) Últimos N jobs
# -------------------------------
@app.get("/jobs/ultimos/{limite}")
def ultimos_jobs(limite: int, db: Session = Depends(get_db)):
    jobs = (
        db.query(models.Job)
        .order_by(models.Job.fecha_creacion.desc())
        .limit(limite)
        .all()
    )
    return jobs


# -------------------------------
# 4) Jobs por tipo (video, video2, audio, audio2, transcripcion)
# -------------------------------
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


# -------------------------------
# 5) Ver estado actual de una sesión (archivos + jobs)
# -------------------------------
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


# -------------------------------
# 6) Sesiones actualmente procesándose
# -------------------------------
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

# ------------------------------------------------------------
# 1) PROGRESO ESTIMADO DE LA UNIÓN DE VIDEOS
# ------------------------------------------------------------


@app.get("/procesos/progreso/{sesion_id}")
def progreso_sesion(sesion_id: int, db: Session = Depends(get_db)):

    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    jobs = (
        db.query(models.Job)
        .filter_by(sesion_id=sesion_id)
        .order_by(models.Job.fecha_creacion.desc())
        .all()
    )

    archivos = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion_id)
        .all()
    )

    # Buscar archivos finales para estimar progreso
    progreso = {}

    for tipo in ["video", "video2"]:
        salida = None
        for a in archivos:
            if a.tipo_archivo == tipo and a.ruta_convertida:
                salida = a.ruta_convertida

        if salida and os.path.exists(salida):
            size_mb = round(os.path.getsize(salida) / (1024 * 1024), 2)
        else:
            size_mb = 0

        job_tipo = next((j for j in jobs if j.tipo == tipo), None)

        progreso[tipo] = {
            "estado_job": job_tipo.estado if job_tipo else "no_inicio",
            "resultado": job_tipo.resultado if job_tipo else None,
            "error": job_tipo.error if job_tipo else None,
            "tamano_actual_MB": size_mb
        }

    return {
        "sesion_id": sesion_id,
        "expediente": sesion.investigacion.numero_expediente,
        "estado_sesion": sesion.estado,
        "progreso": progreso
    }


# ------------------------------------------------------------
# 2) TIMELINE COMPLETO DE UNA SESIÓN
# ------------------------------------------------------------
@app.get("/procesos/timeline/{sesion_id}")
def timeline_sesion(sesion_id: int, db: Session = Depends(get_db)):

    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    archivos = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion_id)
        .order_by(models.SesionArchivo.fecha.asc())
        .all()
    )

    jobs = (
        db.query(models.Job)
        .filter_by(sesion_id=sesion_id)
        .order_by(models.Job.fecha_creacion.asc())
        .all()
    )

    pausas = (
        db.query(models.LogPausa)
        .filter_by(sesion_id=sesion_id)
        .order_by(models.LogPausa.inicio.asc())
        .all()
    )

    timeline = []

    for p in pausas:
        timeline.append({
            "tipo": "pausa",
            "inicio": p.inicio,
            "fin": p.fin,
            "duracion": p.duracion,
            "fuente": p.fuente
        })

    for j in jobs:
        timeline.append({
            "tipo": "job",
            "id": j.id,
            "task": j.tipo,
            "archivo": j.archivo,
            "estado": j.estado,
            "resultado": j.resultado,
            "error": j.error,
            "fecha": j.fecha_creacion
        })

    for a in archivos:
        timeline.append({
            "tipo": "archivo",
            "id": a.id,
            "archivo": a.tipo_archivo,
            "fecha": a.fecha,
            "estado": a.estado,
            "ruta": a.ruta_convertida
        })

    # Ordenar todo cronológicamente
    timeline.sort(key=lambda x: x.get("fecha") or x.get("inicio"))

    return {
        "sesion_id": sesion_id,
        "expediente": sesion.investigacion.numero_expediente,
        "estado": sesion.estado,
        "timeline": timeline
    }
