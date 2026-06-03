import os
import math
from fastapi import Response, APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, distinct, text
import socket
import shutil
import secrets
import ipaddress
from sqlalchemy.exc import IntegrityError, DataError
from typing import Optional

from api_server.database import get_db
from api_server.utils.jobs import detectar_pipeline_bloqueado, sesion_tiene_errores_pipeline
from api_server.utils.sesion_procesamiento import reprocesar_sesion_desde_bd
from api_server.utils.app_sessions import (
    close_app_session,
    close_stale_sessions,
    app_session_to_dict,
    APP_SESSION_STATE_RECORDING,
    REVOKE_ADMIN,
)
from api_server.utils.grabador_health import build_infraestructura_extra
from api_server.utils.jwt import (
    require_dashboard_permission,
    pwd_context,
    create_access_token,
    create_refresh_token,
    _now_utc,
    get_current_principal,
)
from api_server.utils.dashboard_permissions import (
    effective_permissions,
    full_permissions,
    is_super_admin,
    PROTECTED_USERNAME,
)
from api_server.database import get_db
from api_server import models
from api_server.schemas import (
    DashboardLoginRequest,
    DashboardPermissions,
    DashboardUserCreate,
    DashboardUserUpdate,
    DashboardUserResponse,
    DashboardMeResponse,
    PlanchaUpdate,
    PlanchaCreate,
    PlanchaResponse,
    ServiceClientCreate,
    ServiceClientUpdate,
    ServiceClientResponse,
    ServiceClientCreatedResponse,
)

# Router para endpoints de dashboard
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DASHBOARD_ACCESS_TOKEN_MINUTES = int(
    os.getenv("DASHBOARD_ACCESS_TOKEN_MINUTES", "30"))
DASHBOARD_REFRESH_TOKEN_DAYS = int(
    os.getenv("DASHBOARD_REFRESH_TOKEN_DAYS", "14"))


@router.post("/login")
def dashboard_login(
    data: DashboardLoginRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(models.DashboardUser)
        .filter_by(username=data.username)
        .first()
    )

    if not user or not user.activo:
        raise HTTPException(401, "Credenciales inválidas")

    # 🔒 Lock por intentos
    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(403, "Usuario bloqueado temporalmente")

    if not pwd_context.verify(data.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
        db.commit()
        raise HTTPException(401, "Credenciales inválidas")

    # ✅ Login correcto
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()

    sub = f"dash:{user.username}"
    roles = [r.strip() for r in user.roles.split(",") if r.strip()]
    perms = effective_permissions(
        username=user.username,
        permissions=user.permissions,
        roles=roles,
    )

    access = create_access_token(
        sub=sub,
        roles=roles,
        ttl_minutes=DASHBOARD_ACCESS_TOKEN_MINUTES,
        token_type="dashboard",
        permissions=perms,
    )

    refresh, jti, token_hash, exp = create_refresh_token(
        sub=sub,
        roles=roles,
        ttl_hours=DASHBOARD_REFRESH_TOKEN_DAYS * 24,
    )

    db.add(models.RefreshToken(
        subject=sub,
        jti=jti,
        token_hash=token_hash,
        expires_at=exp
    ))
    db.commit()

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer"
    }


@router.get("/resumen")
def dashboard_resumen(
    db: Session = Depends(get_db),
    _principal=Depends(require_dashboard_permission("dashboard")),
):
    desde = _now_utc() - timedelta(days=30)

    # ----------------------------
    # KPI: conteos en 30 días
    # ----------------------------
    kpi_sql = text("""
        SELECT
            COUNT(*) AS total_30_dias,
            SUM(CASE WHEN s.estado = 'finalizada' THEN 1 ELSE 0 END) AS finalizadas,
            SUM(CASE WHEN s.estado IN ('procesando','pausada') THEN 1 ELSE 0 END) AS pendientes,
            -- "errores": sesiones con algún job o archivo en estado error (en 30 días)
            SUM(CASE WHEN EXISTS (
                SELECT 1 FROM jobs j
                WHERE j.sesion_id = s.id AND j.estado = 'error'
            ) OR EXISTS (
                SELECT 1 FROM sesion_archivos sa
                WHERE sa.sesion_id = s.id AND sa.estado = 'error'
            )
            THEN 1 ELSE 0 END) AS errores
        FROM sesiones s
        WHERE s.fecha >= :desde
    """)

    kpis_row = db.execute(
        kpi_sql, {"desde": desde}).mappings().first() or {}
    kpis = {
        "total_30_dias": int(kpis_row.get("total_30_dias") or 0),
        "finalizadas": int(kpis_row.get("finalizadas") or 0),
        "pendientes": int(kpis_row.get("pendientes") or 0),
        "errores": int(kpis_row.get("errores") or 0),
    }

    # ----------------------------
    # Top 10 pendientes (más viejas primero)
    # ----------------------------
    pendientes_sql = text("""
        SELECT
            s.id,
            i.numero_expediente,
            s.nombre_sesion,
            p.nombre AS plancha_nombre,
            s.estado,
            s.fecha
        FROM sesiones s
        LEFT JOIN investigaciones i ON i.id = s.investigacion_id
        LEFT JOIN planchas p ON p.id = s.plancha_id
        WHERE s.estado IN ('procesando','pausada')
        ORDER BY s.fecha ASC
        LIMIT 10
    """)
    pendientes = list(db.execute(pendientes_sql).mappings().all())

    # ----------------------------
    # Top 10 últimas creadas
    # ----------------------------
    ultimas_sql = text("""
        SELECT
            s.id,
            i.numero_expediente,
            p.nombre AS plancha_nombre,
            s.nombre_sesion,
            s.estado,
            s.fecha
        FROM sesiones s
        LEFT JOIN investigaciones i ON i.id = s.investigacion_id
        LEFT JOIN planchas p ON p.id = s.plancha_id
        ORDER BY s.fecha DESC
        LIMIT 10
    """)
    ultimas = list(db.execute(ultimas_sql).mappings().all())

    # ----------------------------
    # Top 10 con error (prioriza lo más reciente)
    # Nota: trae "origen" y mensaje para poder depurar
    # ----------------------------
    errores_sql = text("""
        SELECT
            s.id,
            i.numero_expediente,
            p.nombre AS plancha_nombre,
            s.estado,
            s.nombre_sesion,
            COALESCE(j.tipo::text, sa.tipo_archivo::text) AS origen,
            COALESCE(j.error, sa.mensaje) AS mensaje,
            GREATEST(
                COALESCE(j.fecha_creacion::timestamp, '1970-01-01'::timestamp),
                COALESCE(sa.fecha_finalizacion::timestamp, '1970-01-01'::timestamp),
                COALESCE(s.fecha::timestamp, '1970-01-01'::timestamp)
            ) AS ultima_actualizacion
        FROM sesiones s
        LEFT JOIN investigaciones i ON i.id = s.investigacion_id
        LEFT JOIN planchas p ON p.id = s.plancha_id
        LEFT JOIN LATERAL (
            SELECT j.tipo, j.error, j.fecha_creacion
            FROM jobs j
            WHERE j.sesion_id = s.id AND j.estado = 'error'
            ORDER BY j.fecha_creacion DESC
            LIMIT 1
        ) j ON TRUE
        LEFT JOIN LATERAL (
            SELECT sa.tipo_archivo, sa.mensaje, sa.fecha_finalizacion
            FROM sesion_archivos sa
            WHERE sa.sesion_id = s.id AND sa.estado = 'error'
            ORDER BY sa.fecha_finalizacion DESC
            LIMIT 1
        ) sa ON TRUE
        WHERE (j.tipo IS NOT NULL OR sa.tipo_archivo IS NOT NULL)
        ORDER BY ultima_actualizacion DESC
        LIMIT 10;
    """)
    errores = list(db.execute(errores_sql).mappings().all())

    return {
        "kpis": kpis,
        "pendientes": pendientes,
        "ultimas": ultimas,
        "errores": errores,
    }


@router.get("/expedientes")
def dashboard_expedientes(
    desde: datetime,
    hasta: datetime,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("sesiones")),
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


@router.get("/sesiones")
def dashboard_sesiones(
    desde: datetime,
    hasta: datetime,
    page: int = 1,
    per_page: int = 25,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("sesiones")),
):
    base_q = (
        db.query(models.Sesion)
        .filter(models.Sesion.fecha.between(desde, hasta))
    )

    total = base_q.count()

    sesiones = (
        base_q
        .order_by(models.Sesion.fecha.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    sesion_ids = [s.id for s in sesiones]

    jobs_resumen = (
        db.query(
            models.Job.sesion_id,
            models.Job.estado,
            func.count(models.Job.id).label("total")
        )
        .filter(models.Job.sesion_id.in_(sesion_ids))
        .group_by(models.Job.sesion_id, models.Job.estado)
        .all()
    )

    jobs_map = {}
    for r in jobs_resumen:
        jobs_map.setdefault(r.sesion_id, {})[r.estado] = r.total

    data = []
    for s in sesiones:
        resumen = jobs_map.get(s.id, {})

        data.append({
            "sesion_id": s.id,
            "numero_expediente": s.investigacion.numero_expediente,
            "nombre_sesion": s.nombre_sesion,
            "usuario_ldap": s.usuario_ldap,
            "fecha": s.fecha,
            "estado": s.estado,
            "duracion_real": s.duracion_real,
            "jobs": {
                "pendiente": resumen.get("pendiente", 0),
                "procesando": resumen.get("procesando", 0),
                "completado": resumen.get("completado", 0),
                "error": resumen.get("error", 0),
            }
        })

    return {
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page)
        },
        "data": data
    }


@router.get("/jobs")
def dashboard_jobs(
    estado: str,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("jobs")),
):
    if estado not in {"pendiente", "procesando", "completado", "error"}:
        raise HTTPException(status_code=400, detail="Estado inválido")

    base_q = (
        db.query(
            models.Job,
            models.Sesion.nombre_sesion.label("nombre_sesion"),
            models.Investigacion.numero_expediente.label("numero_expediente"),
        )
        .join(models.Sesion, models.Job.sesion_id == models.Sesion.id)
        .outerjoin(models.Investigacion, models.Sesion.investigacion_id == models.Investigacion.id)
        .filter(models.Job.estado == estado)
    )

    total = base_q.count()

    rows = (
        base_q
        .order_by(models.Job.fecha_creacion.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    data = []
    for job, nombre_sesion, numero_expediente in rows:
        data.append({
            "job_id": job.id,
            "sesion_id": job.sesion_id,
            "nombre_sesion": nombre_sesion,
            "numero_expediente": numero_expediente,
            "tipo": job.tipo,
            "archivo": job.archivo,
            "estado": job.estado,
            "fecha": job.fecha_creacion,
            "error": job.error
        })

    return {
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page)
        },
        "data": data
    }


@router.get("/jobs/sesion/{sesion_id}")
def estatus_completo_sesion(sesion_id: int, db: Session = Depends(get_db), principal=Depends(require_dashboard_permission("jobs"))):
    s = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    archivos = db.query(models.SesionArchivo).filter_by(
        sesion_id=sesion_id).all()
    jobs = db.query(models.Job).filter_by(sesion_id=sesion_id).all()

    return {
        "sesion": {
            "id": s.id,
            "nombre_sesion": s.nombre_sesion,
            "estado": s.estado,
            "fecha": s.fecha,
            "duracion_real": s.duracion_real,
            "investigacion_id": s.investigacion_id,
            "plancha_id": s.plancha_id,
        },
        "archivos": [
            {
                "id": a.id,
                "tipo_archivo": a.tipo_archivo,
                "estado": a.estado,
                "ruta_original": a.ruta_original,
                "ruta_convertida": a.ruta_convertida,
                "mensaje": a.mensaje,
                "fecha_creacion": a.fecha,
                "fecha_finalizacion": a.fecha_finalizacion,
                "conversion_completa": a.conversion_completa,
            }
            for a in archivos
        ],
        "jobs": [
            {
                "id": j.id,
                "tipo": j.tipo,
                "estado": j.estado,
                "archivo": j.archivo,
                "error": j.error,
                "fecha_creacion": j.fecha_creacion,
                "fecha_actualizacion": j.fecha_actualizacion,
            }
            for j in jobs
        ],
    }


# ============================================================
#  📊 DASHBOARD / CONSULTAS (LECTURA) — Estado Infra
# ============================================================


@router.get("/infraestructura")
def infra_estado_dashboard(db: Session = Depends(get_db), principal=Depends(require_dashboard_permission("infraestructura"))):
    estado = {
        "infra_status": "ok",  # ok | warning | error
        "api": "ok",
        "db": "error",
        "rabbitmq": "error",
        "workers": {
            "manifest": "desconocido",
            "video": "desconocido",
            "video2": "desconocido",
            "audio": "desconocido",
            "transcripcion": "desconocido"
        },
        "disco": {
            "master": None,
            "whisper": {
                "status": "sin_reporte"
            }
        },
        "pipeline_bloqueado": {
            "total": 0,
            "sesiones": []
        },
        "grabador": None,
        "wave_mount": None,
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

        estado["workers"]["manifest"] = (
            "activo"
            if any(t.startswith("manifest") for t in tipos_activos)
            else "inactivo"
        )

        estado["workers"]["video"] = (
            "activo" if "video" in tipos_activos else "inactivo"
        )

        estado["workers"]["video2"] = (
            "activo" if "video2" in tipos_activos else "inactivo"
        )

        estado["workers"]["audio"] = (
            "activo" if "audio" in tipos_activos else "inactivo"
        )

        estado["workers"]["transcripcion"] = (
            "activo" if "transcripcion" in tipos_activos else "inactivo"
        )

    except Exception:
        pass

    bloqueadas = detectar_pipeline_bloqueado(db)

    if len(bloqueadas) >= 3:
        estado["infra_status"] = "error"

    if bloqueadas:
        estado["infra_status"] = "warning"
        estado["pipeline_bloqueado"] = {
            "total": len(bloqueadas),
            "sesiones": bloqueadas
        }

    # -------------------------------------------------
    # WARNING: errores recientes en manifest
    # -------------------------------------------------
    limite = datetime.now(timezone.utc) - timedelta(minutes=30)
    errores_manifest = (
        db.query(models.Job)
        .filter(
            models.Job.tipo == "manifest",
            models.Job.estado == "error",
            models.Job.fecha_actualizacion >= limite
        )
        .count()
    )

    if errores_manifest > 0:
        estado["infra_status"] = "warning"

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
        wf = whisper.fecha

        # Si no hay fecha, lo marcamos como reporte inválido / incompleto
        if wf is None:
            estado["disco"]["whisper"] = {
                "total_gb": whisper.disco_total_gb,
                "usado_gb": whisper.disco_usado_gb,
                "libre_gb": whisper.disco_libre_gb,
                "fecha": None,
                "status": "sin_fecha"
            }
        else:
            # Si viene naive, asumimos UTC
            if wf.tzinfo is None:
                wf = wf.replace(tzinfo=timezone.utc)

            retraso = datetime.now(timezone.utc) - wf

            estado["disco"]["whisper"] = {
                "total_gb": whisper.disco_total_gb,
                "usado_gb": whisper.disco_usado_gb,
                "libre_gb": whisper.disco_libre_gb,
                "fecha": wf,
                "status": "stale" if retraso > timedelta(minutes=10) else "ok"
            }

    try:
        extra = build_infraestructura_extra()
    except Exception as exc:
        from api_server.utils.grabador_health import grabador_ip

        ip = grabador_ip()
        extra = {
            "grabador": {
                "ip": ip,
                "online": False,
                "smb_port_open": None,
                "metodo": None,
                "message": f"Error comprobando grabador: {exc}",
                "ok": False,
            },
            "wave_mount": {
                "master": {
                    "mount_point": os.getenv("WAVE_MOUNT", "/mnt/wave"),
                    "mounted": False,
                    "readable": False,
                    "message": "No se pudo comprobar montaje",
                    "ok": False,
                },
                "whisper": {
                    "status": "error",
                    "message": "No se pudo comprobar reporte whisper",
                    "ok": False,
                },
            },
        }

    estado["grabador"] = extra["grabador"]
    estado["wave_mount"] = extra["wave_mount"]

    def _svc(ok: bool) -> str:
        return "ok" if ok else "error"

    estado["grabador_status"] = _svc(extra["grabador"].get("ok"))
    estado["wave_master_status"] = _svc(
        (extra["wave_mount"].get("master") or {}).get("ok")
    )
    whisper = extra["wave_mount"].get("whisper") or {}
    estado["wave_whisper_status"] = (
        "ok" if whisper.get("ok") else whisper.get("status", "error")
    )

    if not extra["grabador"].get("ok") or not (
        extra["wave_mount"].get("master") or {}
    ).get("ok"):
        estado["infra_status"] = "error"
    elif not whisper.get("ok"):
        estado["infra_status"] = "error"

    return estado


# ============================================================
# 📊 DASHBOARD / CONSULTAS (ESCRITURA) — Planchas
# ============================================================

@router.post("/planchas", response_model=PlanchaResponse, status_code=201)
def crear_plancha(data: PlanchaCreate, db: Session = Depends(get_db), principal=Depends(require_dashboard_permission("planchas"))):
    payload = data.dict()

    payload["camara1_ip"] = (payload.get("camara1_ip"))
    payload["camara2_ip"] = (payload.get("camara2_ip"))
    payload["camara1_id"] = (payload.get("camara1_id"))
    payload["camara2_id"] = (payload.get("camara2_id"))

    plancha = models.Plancha(**payload)
    db.add(plancha)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Ya existe una plancha con ese nombre")
    except DataError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="IP inválida (debe ser una IP o vacío)")
    except Exception as e:
        db.rollback()
        print("[PLANCHAS] Error create:", repr(e))
        raise HTTPException(status_code=400, detail="Datos inválidos")

    db.refresh(plancha)
    return plancha


@router.get("/planchas", response_model=list[PlanchaResponse])
def listar_planchas(
    incluir_inactivas: bool = True,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("planchas"))
):
    q = db.query(models.Plancha)

    if not incluir_inactivas:
        q = q.filter(models.Plancha.activo == True)

    return q.order_by(models.Plancha.nombre.asc()).all()


@router.get("/planchas/{plancha_id}", response_model=PlanchaResponse)
def obtener_plancha(plancha_id: int, db: Session = Depends(get_db), principal=Depends(require_dashboard_permission("planchas"))):
    plancha = (
        db.query(models.Plancha)
        .filter(models.Plancha.id == plancha_id)
        .first()
    )

    if not plancha:
        raise HTTPException(status_code=404, detail="Plancha no encontrada")

    return plancha


@router.put("/planchas/{plancha_id}", response_model=PlanchaResponse)
def actualizar_plancha(
    plancha_id: int,
    data: PlanchaUpdate,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("planchas"))
):
    plancha = (
        db.query(models.Plancha)
        .filter(models.Plancha.id == plancha_id)
        .first()
    )

    if not plancha:
        raise HTTPException(status_code=404, detail="Plancha no encontrada")

    patch = data.dict(exclude_unset=True)

    # ✅ Normalización INET (y opcionalmente IDs si los borran)
    if "camara1_ip" in patch:
        patch["camara1_ip"] = (patch["camara1_ip"])
    if "camara2_ip" in patch:
        patch["camara2_ip"] = (patch["camara2_ip"])

    if "camara1_id" in patch:
        patch["camara1_id"] = (patch["camara1_id"])
    if "camara2_id" in patch:
        patch["camara2_id"] = (patch["camara2_id"])

    for field, value in patch.items():
        setattr(plancha, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Ya existe una plancha con ese nombre")
    except DataError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="IP inválida (debe ser una IP o vacío)")
    except Exception as e:
        db.rollback()
        # 👇 opcional, para que lo veas en logs y no adivinar
        print("[PLANCHAS] Error update:", repr(e))
        raise HTTPException(
            status_code=400, detail="Error al actualizar la plancha")

    db.refresh(plancha)
    return plancha


@router.delete("/planchas/{plancha_id}", status_code=204)
def desactivar_plancha(plancha_id: int, db: Session = Depends(get_db), principal=Depends(require_dashboard_permission("planchas"))):
    plancha = (
        db.query(models.Plancha)
        .filter(models.Plancha.id == plancha_id)
        .first()
    )

    if not plancha:
        raise HTTPException(status_code=404, detail="Plancha no encontrada")

    # 🔒 Borrado lógico
    plancha.activo = False
    db.commit()
    return Response(status_code=204)


# ============================================================
#  DASHBOARD — CRUD Service Clients (API Keys)
# ============================================================


def _validate_allowed_ips(allowed_ips: Optional[str]) -> None:
    if allowed_ips is None:
        return
    s = allowed_ips.strip()
    if s == "":
        return

    parts = allowed_ips.replace(" ", ",").split(",")
    for p in parts:
        p = p.strip()
        if not p:
            continue
        try:
            if "/" in p:
                ipaddress.ip_network(p, strict=False)
            else:
                ipaddress.ip_address(p)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"allowed_ips inválido: '{p}'")


def _generate_token() -> str:
    return secrets.token_urlsafe(48)


def _get_sc_or_404(db: Session, sc_id: int):
    sc = db.query(models.ServiceClient).filter_by(id=sc_id).first()
    if not sc:
        raise HTTPException(
            status_code=404, detail="Service client no encontrado")
    return sc


@router.get("/service-clients", response_model=list[ServiceClientResponse])
def listar_service_clients(
    q: Optional[str] = Query(default=None),
    solo_activos: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("tokens")),
):
    query = db.query(models.ServiceClient)

    if q:
        query = query.filter(models.ServiceClient.client_id.ilike(f"%{q}%"))

    if solo_activos:
        query = query.filter(models.ServiceClient.activo.is_(True))

    return query.order_by(models.ServiceClient.created_at.desc()).limit(limit).all()


@router.get("/service-clients/{sc_id}", response_model=ServiceClientResponse)
def obtener_service_client(
    sc_id: int,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("tokens")),
):
    return _get_sc_or_404(db, sc_id)


@router.post("/service-clients", response_model=ServiceClientCreatedResponse, status_code=201)
def crear_service_client(
    data: ServiceClientCreate,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("tokens")),
):
    _validate_allowed_ips(data.allowed_ips)

    exists = db.query(models.ServiceClient).filter_by(
        client_id=data.client_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="client_id ya existe")

    token = (data.token or "").strip() or _generate_token()

    sc = models.ServiceClient(
        client_id=data.client_id.strip(),
        client_secret_hash=token,  # 👈 tu regla: el token ES client_secret_hash
        roles=(data.roles or "worker").strip(),
        activo=bool(data.activo),
        allowed_ips=(data.allowed_ips.strip() if data.allowed_ips else None),
        last_used_at=None,
    )

    db.add(sc)
    db.commit()
    db.refresh(sc)

    return {"service_client": sc, "token": token}


@router.put("/service-clients/{sc_id}", response_model=ServiceClientResponse)
def actualizar_service_client(
    sc_id: int,
    data: ServiceClientUpdate,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("tokens")),
):
    sc = _get_sc_or_404(db, sc_id)

    _validate_allowed_ips(data.allowed_ips)

    if data.roles is not None:
        sc.roles = data.roles.strip()
    if data.activo is not None:
        sc.activo = bool(data.activo)
    if data.allowed_ips is not None:
        sc.allowed_ips = (data.allowed_ips.strip() or None)

    db.commit()
    db.refresh(sc)
    return sc


@router.post("/service-clients/{sc_id}/rotar-token", response_model=ServiceClientCreatedResponse)
def rotar_token_service_client(
    sc_id: int,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("tokens")),
):
    sc = _get_sc_or_404(db, sc_id)
    token = _generate_token()

    sc.client_secret_hash = token
    sc.last_used_at = None

    db.commit()
    db.refresh(sc)
    return {"service_client": sc, "token": token}


@router.post("/service-clients/{sc_id}/activar", response_model=ServiceClientResponse)
def activar_service_client(
    sc_id: int,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("tokens")),
):
    sc = _get_sc_or_404(db, sc_id)
    sc.activo = True
    db.commit()
    db.refresh(sc)
    return sc


@router.post("/service-clients/{sc_id}/desactivar", response_model=ServiceClientResponse)
def desactivar_service_client(
    sc_id: int,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("tokens")),
):
    sc = _get_sc_or_404(db, sc_id)
    sc.activo = False
    db.commit()
    db.refresh(sc)
    return sc


@router.delete("/service-clients/{sc_id}")
def eliminar_service_client(
    sc_id: int,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("tokens")),
):
    sc = db.query(models.ServiceClient).filter_by(id=sc_id).first()
    if not sc:
        raise HTTPException(
            status_code=404, detail="Service client no encontrado")

    db.delete(sc)
    db.commit()

    return {"message": "Service client eliminado", "id": sc_id}


# ============================================================
#  SESIONES FALLIDAS / REPROCESO
# ============================================================

def _contar_jobs_archivos_error(db: Session, sesion_id: int) -> tuple[int, int]:
    jobs_error = (
        db.query(models.Job)
        .filter_by(sesion_id=sesion_id, estado="error")
        .count()
    )
    archivos_error = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion_id, estado="error")
        .count()
    )
    return jobs_error, archivos_error


def _sesion_es_fallida(s: models.Sesion, db: Session) -> bool:
    if not s.payload_procesamiento:
        return False
    if s.estado == "finalizada":
        return False
    if s.error_procesamiento or s.estado == "error":
        return True
    return sesion_tiene_errores_pipeline(db, s.id)


@router.get("/sesiones-fallidas")
def listar_sesiones_fallidas(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _principal=Depends(require_dashboard_permission("sesiones_fallidas")),
):
    candidatas = (
        db.query(models.Sesion)
        .filter(models.Sesion.payload_procesamiento.isnot(None))
        .filter(models.Sesion.estado != "finalizada")
        .order_by(
            models.Sesion.fecha_error_procesamiento.desc().nullslast(),
            models.Sesion.fecha.desc(),
        )
        .all()
    )

    fallidas = [s for s in candidatas if _sesion_es_fallida(s, db)]
    total = len(fallidas)
    offset = (page - 1) * per_page
    pagina = fallidas[offset: offset + per_page]

    data = []
    for s in pagina:
        jobs_error, archivos_error = _contar_jobs_archivos_error(db, s.id)
        inv = s.investigacion
        data.append({
            "id": s.id,
            "numero_expediente": inv.numero_expediente if inv else None,
            "nombre_sesion": s.nombre_sesion,
            "plancha_nombre": s.plancha_nombre,
            "usuario_ldap": s.usuario_ldap,
            "user_nombre": s.user_nombre,
            "estado": s.estado,
            "fecha": s.fecha,
            "fecha_error_procesamiento": s.fecha_error_procesamiento,
            "error_procesamiento": s.error_procesamiento,
            "error_origen": s.error_origen,
            "reintentos_procesamiento": s.reintentos_procesamiento or 0,
            "tiene_payload": bool(s.payload_procesamiento),
            "jobs_error": jobs_error,
            "archivos_error": archivos_error,
        })

    return {
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page) if total else 0,
        },
        "data": data,
    }


@router.get("/sesiones-fallidas/{sesion_id}")
def detalle_sesion_fallida(
    sesion_id: int,
    db: Session = Depends(get_db),
    _principal=Depends(require_dashboard_permission("sesiones_fallidas")),
):
    s = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if not _sesion_es_fallida(s, db) and s.estado != "finalizada":
        raise HTTPException(
            status_code=404,
            detail="La sesión no está en estado fallido",
        )

    archivos = db.query(models.SesionArchivo).filter_by(sesion_id=sesion_id).all()
    jobs = db.query(models.Job).filter_by(sesion_id=sesion_id).all()
    jobs_error, archivos_error = _contar_jobs_archivos_error(db, sesion_id)
    inv = s.investigacion

    return {
        "sesion": {
            "id": s.id,
            "numero_expediente": inv.numero_expediente if inv else None,
            "nombre_sesion": s.nombre_sesion,
            "plancha_nombre": s.plancha_nombre,
            "usuario_ldap": s.usuario_ldap,
            "user_nombre": s.user_nombre,
            "estado": s.estado,
            "fecha": s.fecha,
            "inicio": s.inicio,
            "fin": s.fin,
            "duracion_real": s.duracion_real,
            "fecha_error_procesamiento": s.fecha_error_procesamiento,
            "fecha_ultimo_procesamiento": s.fecha_ultimo_procesamiento,
            "error_procesamiento": s.error_procesamiento,
            "error_origen": s.error_origen,
            "reintentos_procesamiento": s.reintentos_procesamiento or 0,
            "tiene_payload": bool(s.payload_procesamiento),
            "jobs_error": jobs_error,
            "archivos_error": archivos_error,
        },
        "payload_procesamiento": s.payload_procesamiento,
        "jobs": [
            {
                "id": j.id,
                "tipo": j.tipo,
                "estado": j.estado,
                "archivo": j.archivo,
                "error": j.error,
                "fecha_creacion": j.fecha_creacion,
                "fecha_actualizacion": j.fecha_actualizacion,
            }
            for j in jobs
        ],
        "archivos": [
            {
                "id": a.id,
                "tipo_archivo": a.tipo_archivo,
                "estado": a.estado,
                "mensaje": a.mensaje,
                "ruta_convertida": a.ruta_convertida,
                "conversion_completa": a.conversion_completa,
                "fecha_finalizacion": a.fecha_finalizacion,
            }
            for a in archivos
        ],
    }


@router.post("/sesiones-fallidas/{sesion_id}/reprocesar")
def reprocesar_sesion_fallida(
    sesion_id: int,
    db: Session = Depends(get_db),
    _principal=Depends(require_dashboard_permission("sesiones_fallidas")),
):
    result = reprocesar_sesion_desde_bd(db, sesion_id)
    return {
        "status": result.get("status", "procesando"),
        "id_sesion": sesion_id,
        "reintentos_procesamiento": result.get("reintentos_procesamiento", 0),
        "message": "Sesión enviada a reprocesar correctamente",
    }


# ============================================================
#  Usuarios del dashboard (CRUD)
# ============================================================

def _dashboard_user_response(user: models.DashboardUser) -> DashboardUserResponse:
    roles = [r.strip() for r in (user.roles or "").split(",") if r.strip()]
    perms = effective_permissions(
        username=user.username,
        permissions=user.permissions,
        roles=roles,
    )
    return DashboardUserResponse(
        id=user.id,
        username=user.username,
        activo=user.activo,
        permissions=DashboardPermissions(**perms),
        is_protected=user.username == PROTECTED_USERNAME,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def _permissions_to_db(perms: DashboardPermissions) -> dict:
    return perms.model_dump()


def _roles_from_permissions(perms: dict) -> str:
    if perms.get("usuarios") or perms.get("tokens"):
        return "dashboard_admin"
    return "dashboard_read"


@router.get("/me", response_model=DashboardMeResponse)
def dashboard_me(principal=Depends(get_current_principal)):
    if principal.get("type") != "dashboard":
        raise HTTPException(status_code=401, detail="Token inválido para dashboard")

    username = principal.get("sub", "").split(":", 1)[-1]
    perms = effective_permissions(
        username=username,
        permissions=principal.get("permissions"),
        roles=principal.get("roles"),
    )
    return DashboardMeResponse(
        username=username,
        permissions=DashboardPermissions(**perms),
        is_protected=is_super_admin(username),
    )


@router.get("/usuarios", response_model=list[DashboardUserResponse])
def listar_dashboard_usuarios(
    db: Session = Depends(get_db),
    _principal=Depends(require_dashboard_permission("usuarios")),
):
    users = (
        db.query(models.DashboardUser)
        .order_by(models.DashboardUser.username.asc())
        .all()
    )
    return [_dashboard_user_response(u) for u in users]


@router.get("/usuarios/{user_id}", response_model=DashboardUserResponse)
def obtener_dashboard_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    _principal=Depends(require_dashboard_permission("usuarios")),
):
    user = db.query(models.DashboardUser).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _dashboard_user_response(user)


@router.post("/usuarios", response_model=DashboardUserResponse, status_code=201)
def crear_dashboard_usuario(
    data: DashboardUserCreate,
    db: Session = Depends(get_db),
    _principal=Depends(require_dashboard_permission("usuarios")),
):
    username = data.username.strip()
    if len(username) < 2:
        raise HTTPException(status_code=400, detail="Usuario demasiado corto")
    if username.lower() == PROTECTED_USERNAME:
        raise HTTPException(status_code=400, detail="Nombre de usuario reservado")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")

    perms = _permissions_to_db(data.permissions)
    user = models.DashboardUser(
        username=username,
        password_hash=pwd_context.hash(data.password),
        roles=_roles_from_permissions(perms),
        permissions=perms,
        activo=bool(data.activo),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    db.refresh(user)
    return _dashboard_user_response(user)


@router.put("/usuarios/{user_id}", response_model=DashboardUserResponse)
def actualizar_dashboard_usuario(
    user_id: int,
    data: DashboardUserUpdate,
    db: Session = Depends(get_db),
    _principal=Depends(require_dashboard_permission("usuarios")),
):
    user = db.query(models.DashboardUser).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if data.password is not None:
        if len(data.password) < 8:
            raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
        user.password_hash = pwd_context.hash(data.password)

    if user.username == PROTECTED_USERNAME:
        user.activo = True
        user.permissions = full_permissions()
    else:
        if data.activo is not None:
            user.activo = bool(data.activo)
        if data.permissions is not None:
            perms = _permissions_to_db(data.permissions)
            user.permissions = perms
            user.roles = _roles_from_permissions(perms)

    db.commit()
    db.refresh(user)
    return _dashboard_user_response(user)


@router.delete("/usuarios/{user_id}")
def eliminar_dashboard_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    _principal=Depends(require_dashboard_permission("usuarios")),
):
    user = db.query(models.DashboardUser).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.username == PROTECTED_USERNAME:
        raise HTTPException(
            status_code=403,
            detail="No se puede eliminar el usuario administrador por defecto",
        )

    db.delete(user)
    db.commit()
    return {"message": "Usuario eliminado", "id": user_id}


# ============================================================
#  Sesiones app (operadores LDAP / tablets)
# ============================================================

@router.get("/app-sessions")
def listar_app_sessions(
    db: Session = Depends(get_db),
    _principal=Depends(require_dashboard_permission("sesiones")),
):
    close_stale_sessions(db)
    rows = (
        db.query(models.AppUserSession)
        .filter(models.AppUserSession.revoked_at.is_(None))
        .order_by(models.AppUserSession.last_heartbeat_at.desc())
        .all()
    )
    return [app_session_to_dict(r) for r in rows]


@router.post("/app-sessions/{session_id}/revoke")
def revocar_app_session(
    session_id: int,
    db: Session = Depends(get_db),
    principal=Depends(require_dashboard_permission("sesiones")),
):
    row = db.query(models.AppUserSession).filter_by(id=session_id).first()
    if not row or row.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o ya cerrada")

    if row.estado == APP_SESSION_STATE_RECORDING:
        raise HTTPException(
            status_code=403,
            detail="No se puede cerrar la sesión mientras el operador está grabando",
        )

    admin_user = principal.get("sub", "").split(":")[-1]
    close_app_session(
        db,
        row,
        reason=REVOKE_ADMIN,
        revoked_by=admin_user,
        pause_sesion=True,
    )
    return {"status": "ok", "message": "Sesión de app cerrada", "id": session_id}

