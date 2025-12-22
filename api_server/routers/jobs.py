from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from api_server.database import get_db
import models
from schemas import JobCreate, JobUpdate

router = APIRouter()


@router.post("/crear")
def crear_job(
    data: JobCreate,
    db: Session = Depends(get_db)
):
    job = (
        db.query(models.Job)
        .filter_by(sesion_id=data.id_sesion, tipo=data.tipo)
        .first()
    )

    if job:
        job.estado = "pendiente"
        job.error = None
        job.resultado = None
        job.fecha_actualizacion = datetime.now(timezone.utc)
        db.commit()
        return {"job_id": job.id, "reutilizado": True}

    investigacion = (
        db.query(models.Investigacion)
        .filter_by(numero_expediente=data.numero_expediente)
        .first()
    )

    if not investigacion:
        raise HTTPException(404, "Investigación no encontrada")

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

    return {"job_id": nuevo.id, "creado": True}


@router.put("/{job_id}/actualizar")
def actualizar_job(
    job_id: int,
    data: JobUpdate,
    db: Session = Depends(get_db)
):
    job = db.query(models.Job).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(404, "Job no encontrado")

    if data.estado:
        job.estado = data.estado
    if data.resultado:
        job.resultado = data.resultado
    if data.error:
        job.error = data.error

    job.fecha_actualizacion = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Job actualizado"}
