# ============================================================
#   Procesamiento y reproceso de sesiones
# ============================================================

import os
from datetime import datetime, timezone

from celery import chain
from fastapi import HTTPException
from sqlalchemy.orm import Session

from api_server import models
from api_server.utils.jobs import crear_job_interno, limpiar_error_procesamiento
from api_server.utils.rutas import parse_hhmmss_to_seconds
from api_server.utils.sesion_estado import asignar_estado_sesion, validar_estado_sesion
from worker.celery_app import celery_app

GRABADOR_UUID = os.getenv("WINDOWS_WAVE_UUID", "").strip()


def _now_utc():
    return datetime.now(timezone.utc)


def _normalizar_job_id(result):
    if isinstance(result, dict):
        return result.get("job_id")
    return result


def sincronizar_pausas_app(db: Session, sesion_id: int, pausas: list) -> int:
    """
    Aplica pausas del JSON de forma idempotente (fuente=app).
    Reemplaza las existentes; no recalcula nada.
    """
    db.query(models.LogPausa).filter_by(
        sesion_id=sesion_id,
        fuente="app",
    ).delete(synchronize_session=False)

    count = 0
    for p in pausas or []:
        try:
            inicio_p = datetime.fromisoformat(p["inicio"])
            fin_p = datetime.fromisoformat(p["fin"])
            dur = (fin_p - inicio_p).total_seconds()

            db.add(models.LogPausa(
                sesion_id=sesion_id,
                inicio=inicio_p,
                fin=fin_p,
                duracion=dur,
                fuente="app",
            ))
            count += 1
        except Exception as e:
            print(f"[PAUSAS] Error registrando pausa sesión {sesion_id}: {e}")

    db.commit()
    return count


def preparar_reprocesamiento(db: Session, sesion: models.Sesion) -> None:
    """Limpia errores y resetea archivos en error antes de relanzar pipeline."""
    limpiar_error_procesamiento(db, sesion.id)
    sesion.reintentos_procesamiento = (sesion.reintentos_procesamiento or 0) + 1
    asignar_estado_sesion(sesion, "procesando")

    archivos_error = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion.id)
        .filter(models.SesionArchivo.estado == "error")
        .all()
    )
    for a in archivos_error:
        a.estado = "pendiente"
        a.mensaje = None
        a.conversion_completa = False
        a.fecha_finalizacion = None
        a.tamano_kb = None

    db.commit()


def ejecutar_procesamiento_sesion(
    payload: dict,
    db: Session,
    *,
    es_reintento: bool = False,
) -> dict:
    """
    Lógica central de /procesar_sesion.
    Guarda payload, sincroniza pausas del JSON y lanza workers Celery.
    """
    if not isinstance(payload, dict):
        raise HTTPException(400, "Payload inválido")

    ses = payload.get("sesion_activa")
    if not ses:
        raise HTTPException(status_code=400, detail="Falta 'sesion_activa'")

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
            detail="Falta plancha_id o plancha_nombre en sesion_activa",
        )

    if not expediente or not id_sesion:
        raise HTTPException(
            status_code=400, detail="Faltan expediente o id_sesion")

    if not cam1 or not cam2:
        raise HTTPException(status_code=400, detail="Faltan MAC addresses")

    try:
        inicio_iso = ses["inicio"]
        fin_iso = ses["fin"]
        inicio_dt = datetime.fromisoformat(inicio_iso)
        fin_dt = datetime.fromisoformat(fin_iso)
    except Exception:
        raise HTTPException(
            status_code=400, detail="Formato inválido de inicio/fin")

    duracion_real_seg = None
    if duracion_total_str:
        try:
            duracion_real_seg = parse_hhmmss_to_seconds(duracion_total_str)
        except Exception:
            print("[ERROR] No se pudo parsear duracion_total")
            duracion_real_seg = 0

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

    nombre_carpeta = (
        getattr(investigacion, "nombre_carpeta", None) or ""
    ).strip()
    if not nombre_carpeta:
        nombre_carpeta = expediente

    forense = ses.get("forense") or {}

    if not sesion_obj:
        sesion_obj = models.Sesion(
            id=id_sesion,
            investigacion_id=investigacion.id,
            nombre_sesion=ses.get("nombre", f"Sesion_{id_sesion}"),
            usuario_ldap=forense.get("id_usuario", "desconocido"),
            user_nombre=forense.get("nombre"),
            plancha_id=plancha_id,
            plancha_nombre=plancha_nombre,
            tablet_id=ses.get("tablet", "desconocida"),
            camara1_mac_address=cam1,
            camara2_mac_address=cam2,
            app_version=ses.get("version_app", "1.0.0"),
            estado=validar_estado_sesion("procesando"),
            fecha=inicio_dt,
            inicio=inicio_dt,
            fin=fin_dt,
            duracion_real=float(duracion_real_seg)
            if duracion_real_seg is not None
            else None,
        )
        db.add(sesion_obj)
        db.commit()
        db.refresh(sesion_obj)
        print(f"[SESION] Creada sesión {id_sesion}")
    else:
        print(f"[SESION] Sesión {id_sesion} existente → actualizando")
        sesion_obj.plancha_id = plancha_id
        sesion_obj.plancha_nombre = plancha_nombre
        sesion_obj.camara1_mac_address = cam1
        sesion_obj.camara2_mac_address = cam2
        sesion_obj.app_version = ses.get("version_app", "1.0.0")
        asignar_estado_sesion(sesion_obj, "procesando")
        sesion_obj.inicio = inicio_dt
        sesion_obj.fin = fin_dt
        sesion_obj.duracion_real = (
            float(duracion_real_seg) if duracion_real_seg is not None else None
        )
        db.commit()

    sesion_obj.payload_procesamiento = payload
    sesion_obj.fecha_ultimo_procesamiento = _now_utc()
    if not es_reintento:
        limpiar_error_procesamiento(db, sesion_obj.id, commit=False)
    db.commit()

    pausas = ses.get("pausas", [])
    pausas_registradas = sincronizar_pausas_app(db, sesion_obj.id, pausas)

    fecha_solo = inicio_iso.split("T")[0]
    yyyy, mm, dd = fecha_solo.split("-")

    path_manifest1 = (
        f"/mnt/wave/manifests/{GRABADOR_UUID}/{cam1}/{yyyy}/{mm}/{dd}/manifest.json"
    )
    path_manifest2 = (
        f"/mnt/wave/manifests/{GRABADOR_UUID}/{cam2}/{yyyy}/{mm}/{dd}/manifest.json"
    )

    job_manifest1 = _normalizar_job_id(crear_job_interno(
        db=db,
        numero_expediente=expediente,
        sesion_id=id_sesion,
        tipo="manifest",
        archivo=f"manifests/{GRABADOR_UUID}/{cam1}/{yyyy}/{mm}/{dd}/manifest.json",
    ))
    if not job_manifest1:
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar job de manifest para cámara 1",
        )

    job_manifest2 = _normalizar_job_id(crear_job_interno(
        db=db,
        numero_expediente=expediente,
        sesion_id=id_sesion,
        tipo="manifest",
        archivo=f"manifests/{GRABADOR_UUID}/{cam2}/{yyyy}/{mm}/{dd}/manifest.json",
    ))
    if not job_manifest2:
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar job de manifest para cámara 2",
        )

    chain(
        celery_app.signature(
            "tasks.generar_manifest",
            args=[cam1, fecha_solo, job_manifest1],
            immutable=True,
        ),
        celery_app.signature(
            "worker.tasks.unir_video",
            args=[
                expediente,
                nombre_carpeta,
                id_sesion,
                path_manifest1,
                inicio_iso,
                fin_iso,
            ],
            immutable=True,
        ),
    ).apply_async()

    chain(
        celery_app.signature(
            "tasks.generar_manifest",
            args=[cam2, fecha_solo, job_manifest2],
            immutable=True,
        ),
        celery_app.signature(
            "worker.tasks.unir_video2",
            args=[
                expediente,
                nombre_carpeta,
                id_sesion,
                path_manifest2,
                inicio_iso,
                fin_iso,
            ],
            immutable=True,
        ),
    ).apply_async()

    return {
        "status": "procesando",
        "expediente": expediente,
        "nombre_carpeta": nombre_carpeta,
        "id_sesion": id_sesion,
        "inicio_sesion": inicio_iso,
        "fin_sesion": fin_iso,
        "duracion_total_seg": duracion_real_seg,
        "pausas_app_registradas": pausas_registradas,
        "manifest1": path_manifest1,
        "manifest2": path_manifest2,
        "reintento": es_reintento,
    }


def reprocesar_sesion_desde_bd(db: Session, sesion_id: int) -> dict:
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if not sesion.payload_procesamiento:
        raise HTTPException(
            status_code=400,
            detail="Esta sesión no tiene JSON de procesamiento guardado",
        )

    if sesion.estado == "finalizada":
        raise HTTPException(
            status_code=400,
            detail="La sesión ya está finalizada",
        )

    preparar_reprocesamiento(db, sesion)
    db.refresh(sesion)

    result = ejecutar_procesamiento_sesion(
        sesion.payload_procesamiento,
        db,
        es_reintento=True,
    )
    result["reintentos_procesamiento"] = sesion.reintentos_procesamiento
    return result
