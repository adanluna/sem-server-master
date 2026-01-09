from api_server import models
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from api_server import models


def verificar_estado_sesion(sesion_id: int, db: Session):
    jobs = db.query(models.Job).filter_by(sesion_id=sesion_id).all()
    if not jobs:
        return

    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        return

    errores = [j for j in jobs if j.estado == "error"]
    pendientes = [j for j in jobs if j.estado in ("pendiente", "en_progreso")]

    # ❌ Error operativo
    if errores:
        if sesion.estado != "error":
            sesion.estado = "error"
            db.commit()
        return

    # ⏳ Aún en proceso
    if pendientes:
        return

    # ✅ Jobs completos (pero NO evidencia)
    if sesion.estado not in ("finalizada", "error"):
        sesion.estado = "procesado"
        db.commit()


def crear_o_resetear_job(
    *,
    db,
    numero_expediente: str,
    sesion_id: int,
    tipo: str,
    archivo: str
) -> int:
    job = (
        db.query(models.Job)
        .filter_by(sesion_id=sesion_id, tipo=tipo)
        .first()
    )

    if job:
        job.estado = "pendiente"
        job.error = None
        job.resultado = None
        job.fecha_actualizacion = datetime.now(timezone.utc)
        db.commit()
        return job.id

    investigacion = (
        db.query(models.Investigacion)
        .filter_by(numero_expediente=numero_expediente)
        .first()
    )

    if not investigacion:
        raise RuntimeError("Investigación no encontrada")

    nuevo = models.Job(
        investigacion_id=investigacion.id,
        sesion_id=sesion_id,
        tipo=tipo,
        archivo=archivo,
        estado="pendiente"
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return nuevo.id


def detectar_pipeline_bloqueado(db, minutos=15):
    limite = datetime.now(timezone.utc) - timedelta(minutes=minutos)

    sesiones_bloqueadas = []

    sesiones = db.query(models.Sesion).all()

    for ses in sesiones:
        jobs = (
            db.query(models.Job)
            .filter(models.Job.sesion_id == ses.id)
            .all()
        )

        jobs_por_tipo = {j.tipo: j for j in jobs}

        manifest = jobs_por_tipo.get("manifest")
        video = jobs_por_tipo.get("video")
        video2 = jobs_por_tipo.get("video2")

        if not manifest or manifest.estado != "completado":
            continue

        # Si video existe pero no avanza
        if video and video.estado in ("pendiente", "en_progreso"):
            if video.fecha_actualizacion < limite:
                sesiones_bloqueadas.append({
                    "sesion_id": ses.id,
                    "expediente": ses.investigacion.numero_expediente,
                    "bloqueado_en": "video",
                    "desde": video.fecha_actualizacion
                })

        if video2 and video2.estado in ("pendiente", "en_progreso"):
            if video2.fecha_actualizacion < limite:
                sesiones_bloqueadas.append({
                    "sesion_id": ses.id,
                    "expediente": ses.investigacion.numero_expediente,
                    "bloqueado_en": "video2",
                    "desde": video2.fecha_actualizacion
                })

    return sesiones_bloqueadas


def crear_job_interno(
    *,
    db: Session,
    numero_expediente: str,
    sesion_id: int,
    tipo: str,
    archivo: str
) -> dict:
    """
    Crea o reutiliza un Job de manera interna (sin FastAPI).

    Reglas:
    - Un job es único por (sesion_id + tipo)
    - Si existe, se resetea para reintento
    """

    # 🔒 Buscar SIEMPRE por sesión + tipo
    job_existente = (
        db.query(models.Job)
        .filter_by(sesion_id=sesion_id, tipo=tipo)
        .first()
    )

    if job_existente:
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

    # -----------------------------------------
    # Crear job nuevo
    # -----------------------------------------
    investigacion = (
        db.query(models.Investigacion)
        .filter_by(numero_expediente=numero_expediente)
        .first()
    )

    if not investigacion:
        raise ValueError("Investigación no encontrada")

    nuevo = models.Job(
        investigacion_id=investigacion.id,
        sesion_id=sesion_id,
        tipo=tipo,
        archivo=archivo,
        estado="pendiente",
        fecha_creacion=datetime.now(timezone.utc),
        fecha_actualizacion=datetime.now(timezone.utc),
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return {
        "job_id": nuevo.id,
        "creado": True
    }
