import os
import math
from fastapi import Response, APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, distinct, text
import socket
import shutil

from api_server.database import get_db
from api_server.utils.jobs import detectar_pipeline_bloqueado
from api_server.utils.jwt import require_dashboard_admin, require_roles, pwd_context, create_access_token, create_refresh_token, _now_utc
from api_server.database import get_db
from api_server import models
from api_server.schemas import (
    DashboardLoginRequest,
    PlanchaUpdate,
    PlanchaCreate,
    PlanchaResponse,
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
    roles = user.roles.split(",")

    access = create_access_token(
        sub=sub,
        roles=roles,
        ttl_minutes=DASHBOARD_ACCESS_TOKEN_MINUTES,
        token_type="dashboard"
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
    _principal=Depends(require_dashboard_admin),  # 🔒 solo dashboard_admin
):
    desde = _now_utc() - timedelta(days=30)

    # ----------------------------
    # KPI: conteos en 30 días
    # ----------------------------
    kpi_sql = text("""
        SELECT
            COUNT(*) AS total_30_dias,
            SUM(CASE WHEN s.estado = 'finalizada' THEN 1 ELSE 0 END) AS finalizadas,
            SUM(CASE WHEN s.estado IN ('en_progreso','pausada') THEN 1 ELSE 0 END) AS pendientes,
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
            p.nombre AS plancha_nombre,
            s.estado,
            s.fecha
        FROM sesiones s
        LEFT JOIN investigaciones i ON i.id = s.investigacion_id
        LEFT JOIN planchas p ON p.id = s.plancha_id
        WHERE s.estado IN ('en_progreso','pausada')
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
    principal=Depends(require_roles("dashboard_admin"))
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
    principal=Depends(require_roles("dashboard_read", "dashboard_admin"))
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
            "usuario_ldap": s.usuario_ldap,
            "fecha": s.fecha,
            "estado": s.estado,
            "duracion_real": s.duracion_real,
            "jobs": {
                "pendiente": resumen.get("pendiente", 0),
                "en_progreso": resumen.get("en_progreso", 0),
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
    principal=Depends(require_roles("dashboard_admin"))
):
    if estado not in {"pendiente", "en_progreso", "completado", "error"}:
        raise HTTPException(status_code=400, detail="Estado inválido")

    base_q = (
        db.query(
            models.Job,
            models.Sesion.nombre_sesion.label("nombre_sesion")
        )
        .join(models.Sesion, models.Job.sesion_id == models.Sesion.id)
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
    for job, nombre_sesion in rows:
        data.append({
            "job_id": job.id,
            "sesion_id": job.sesion_id,
            "nombre_sesion": nombre_sesion,
            "numero_expediente": job.investigacion.numero_expediente,
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
def estatus_completo_sesion(sesion_id: int, db: Session = Depends(get_db), principal=Depends(require_roles("dashboard_admin"))):
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


# ============================================================
#  📊 DASHBOARD / CONSULTAS (LECTURA) — Estado Infra
# ============================================================


@router.get("/infraestructura")
def infra_estado_dashboard(db: Session = Depends(get_db), principal=Depends(require_roles("dashboard_admin"))):
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
# 📊 DASHBOARD / CONSULTAS (ESCRITURA) — Planchas
# ============================================================

@router.post("/planchas", response_model=PlanchaResponse, status_code=201)
def crear_plancha(data: PlanchaCreate, db: Session = Depends(get_db), principal=Depends(require_roles("dashboard_admin"))):
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


@router.get("/planchas", response_model=list[PlanchaResponse])
def listar_planchas(
    incluir_inactivas: bool = True,
    db: Session = Depends(get_db),
    principal=Depends(require_roles("dashboard_read", "dashboard_admin"))
):
    q = db.query(models.Plancha)

    if not incluir_inactivas:
        q = q.filter(models.Plancha.activo == True)

    return q.order_by(models.Plancha.nombre.asc()).all()


@router.get("/planchas/{plancha_id}", response_model=PlanchaResponse)
def obtener_plancha(plancha_id: int, db: Session = Depends(get_db), principal=Depends(require_roles("dashboard_read", "dashboard_admin"))):
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
    principal=Depends(require_roles("dashboard_admin"))
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


@router.delete("/planchas/{plancha_id}", status_code=204)
def desactivar_plancha(plancha_id: int, db: Session = Depends(get_db), principal=Depends(require_roles("dashboard_admin"))):
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
