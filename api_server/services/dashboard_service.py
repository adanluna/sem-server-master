from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
import models


def dashboard_expedientes(desde, hasta, page, per_page, db: Session):
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


def dashboard_sesiones(desde, hasta, page, per_page, db: Session):
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


def dashboard_jobs(estado, page, per_page, db: Session):
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
