from fastapi import APIRouter, HTTPException, Depends
import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from api_server.database import get_db
from api_server import models
from api_server.utils.rutas import normalizar_ruta, size_kb, ruta_red
from api_server.utils.service_auth import require_service_bearer


router = APIRouter(
    prefix="/api",
    tags=["api"],
    # el rol que quieras exigir
    dependencies=[Depends(require_service_bearer("semefo_read"))]
)
logger = logging.getLogger("api")

TERMINALES = {"completado", "error"}

# ============================================================
#  LISTAR JOBS DE UNA SESIÓN (vista unificada para UI)
# ============================================================


@router.get("/sesiones/{sesion_id}/jobs")
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

# ============================================================
#  🔍 CONSULTAS SESIONES
# ============================================================


@router.get("/sesiones/{sesion_id}")
def obtener_sesion(sesion_id: int, db: Session = Depends(get_db)):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # 1) Archivos
    archivos = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion_id)
        .order_by(models.SesionArchivo.id.asc())
        .all()
    )

    # 2) Jobs (para consolidar estado)
    jobs = (
        db.query(models.Job)
        .filter_by(sesion_id=sesion_id)
        .order_by(models.Job.fecha_creacion.desc())
        .all()
    )

    # último job por tipo (audio/video/transcripcion/etc.)
    ultimo_job_por_tipo = {}
    for j in jobs:
        # Solo tipos que correspondan a sesion_archivos
        if j.tipo not in {"audio", "audio2", "video", "video2", "transcripcion"}:
            continue
        if j.tipo not in ultimo_job_por_tipo:
            # como vienen desc, el primero es el más reciente
            ultimo_job_por_tipo[j.tipo] = j

    sesion_out = {
        "id": sesion.id,
        "user_nombre": sesion.user_nombre,
        "plancha_id": sesion.plancha_id,
        "plancha_nombre": sesion.plancha_nombre,
        "investigacion_id": sesion.investigacion_id,
        "app_version": sesion.app_version,
        "progreso_porcentaje": sesion.progreso_porcentaje,
        "tablet_id": sesion.tablet_id,
        "estado": sesion.estado,
        "fecha": sesion.fecha,
        "fin": sesion.fin,
        "nombre_sesion": sesion.nombre_sesion,
    }

    archivos_out = []
    for a in archivos:
        ruta_base = a.ruta_convertida or a.ruta_original

        ruta_abs = normalizar_ruta(
            ruta_base,
            tipo=a.tipo_archivo,
            expediente=None,
            sesion_id=None
        )

        ruta_publica = ruta_red(ruta_abs)

        fecha_archivo = getattr(a, "fecha_creacion",
                                None) or getattr(a, "fecha", None)

        ruta_original_abs = normalizar_ruta(
            a.ruta_original,
            tipo=a.tipo_archivo,
            expediente=None,
            sesion_id=None
        )

        # === Consolidación: si job más reciente está terminal, prevalece ===
        estado_final = a.estado
        mensaje_final = getattr(a, "mensaje", None)
        fecha_finalizacion_final = a.fecha_finalizacion
        tamano_kb_final = size_kb(ruta_abs)

        j = ultimo_job_por_tipo.get(a.tipo_archivo)
        if j and (j.estado in TERMINALES):
            estado_final = j.estado
            # Si el job trae error, úsalo
            if j.error:
                mensaje_final = j.error
            # Fecha final: usa fecha_actualizacion del job si existe
            if getattr(j, "fecha_actualizacion", None):
                fecha_finalizacion_final = j.fecha_actualizacion
            # Tamaño: si el job reporta tamaño y es > 0, úsalo (evita 0 por race condition)
            if getattr(j, "tamano_actual_KB", None) and j.tamano_actual_KB > 0:
                tamano_kb_final = j.tamano_actual_KB

        archivos_out.append({
            "tipo_archivo": a.tipo_archivo,
            "sesion_id": a.sesion_id,
            "ruta_convertida": ruta_publica,
            "estado": estado_final,
            "mensaje": mensaje_final,
            "fecha": fecha_archivo,
            "ruta_original": ruta_original_abs,
            "id": a.id,
            "conversion_completa": bool(a.conversion_completa),
            "tamano_kb": tamano_kb_final,
            "fecha_finalizacion": fecha_finalizacion_final,
        })

    return {"sesion": sesion_out, "archivos": archivos_out}

# ============================================================
#  🔍 CONSULTAS PARA SEMEFO (expedientes)
# ============================================================


@router.get("/expedientes/{numero_expediente}")
def consulta_expediente(numero_expediente: str, db: Session = Depends(get_db)):
    inv = (
        db.query(models.Investigacion)
        .filter_by(numero_expediente=numero_expediente)
        .first()
    )

    if not inv:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")

    sesiones_out = []

    # Si tienes relación inv.sesiones, úsala; si no, query por investigacion_id
    for s in inv.sesiones:
        # ---------- sesion_out (mismo shape que /sesiones/{id}) ----------
        sesion_out = {
            "id": s.id,
            "user_nombre": s.user_nombre,
            "plancha_id": s.plancha_id,
            "plancha_nombre": s.plancha_nombre,
            "investigacion_id": s.investigacion_id,
            "app_version": s.app_version,
            "progreso_porcentaje": s.progreso_porcentaje,
            "tablet_id": s.tablet_id,
            "estado": s.estado,
            "fecha": s.fecha,
            "fin": s.fin,
            "nombre_sesion": s.nombre_sesion,
        }

        # ---------- archivos_out (mismo shape que /sesiones/{id}) ----------
        archivos_out = []
        for a in s.archivos:
            ruta_base = a.ruta_convertida or a.ruta_original

            # Normalizar a absoluta (para que size_kb y ruta_red funcionen)
            ruta_abs = normalizar_ruta(
                ruta_base,
                tipo=a.tipo_archivo,
                expediente=inv.numero_expediente,
                sesion_id=s.id
            )

            ruta_publica = ruta_red(ruta_abs)

            fecha_archivo = getattr(
                a, "fecha_creacion", None) or getattr(a, "fecha", None)

            ruta_original_abs = normalizar_ruta(
                a.ruta_original,
                tipo=a.tipo_archivo,
                expediente=inv.numero_expediente,
                sesion_id=s.id
            )

            archivos_out.append({
                "tipo_archivo": a.tipo_archivo,
                "sesion_id": a.sesion_id,
                "ruta_convertida": ruta_publica,
                "estado": a.estado,
                "fecha": fecha_archivo,
                "ruta_original": ruta_original_abs,
                "id": a.id,
                "fecha_finalizacion": a.fecha_finalizacion,
                "tamano_kb": size_kb(ruta_abs),
            })

        sesiones_out.append({
            "sesion": sesion_out,
            "archivos": archivos_out
        })

    return {
        "numero_expediente": inv.numero_expediente,
        "fecha_creacion": inv.fecha_creacion,
        "sesiones": sesiones_out
    }
