from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
import models
from schemas import InvestigacionCreate, InvestigacionUpdate

router = APIRouter()


@router.post("/")
def crear_o_devolver_investigacion(
    data: InvestigacionCreate,
    db: Session = Depends(get_db)
):
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


@router.get("/")
def list_investigaciones(db: Session = Depends(get_db)):
    return db.query(models.Investigacion).all()


@router.get("/{numero_expediente}")
def get_investigacion(
    numero_expediente: str,
    db: Session = Depends(get_db)
):
    inv = (
        db.query(models.Investigacion)
        .filter_by(numero_expediente=numero_expediente)
        .first()
    )

    if not inv:
        raise HTTPException(
            status_code=404,
            detail="Investigación no encontrada"
        )

    return inv


@router.put("/{numero_expediente}")
def update_investigacion(
    numero_expediente: str,
    datos: InvestigacionUpdate,
    db: Session = Depends(get_db)
):
    inv = (
        db.query(models.Investigacion)
        .filter_by(numero_expediente=numero_expediente)
        .first()
    )

    if not inv:
        raise HTTPException(
            status_code=404,
            detail="Investigación no encontrada"
        )

    if datos.nombre_carpeta is not None:
        inv.nombre_carpeta = datos.nombre_carpeta

    if datos.observaciones is not None:
        inv.observaciones = datos.observaciones

    db.commit()
    db.refresh(inv)

    return inv
