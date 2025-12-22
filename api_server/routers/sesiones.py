from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from api_server.database import get_db
from api_server import models
from api_server.schemas import (
    SesionCreate,
    SesionResponse,
    PausaCreate,
    PausaResponse
)

router = APIRouter()


@router.post("/", response_model=SesionResponse)
def crear_sesion(
    sesion_data: SesionCreate,
    db: Session = Depends(get_db)
):
    investigacion = (
        db.query(models.Investigacion)
        .filter_by(id=sesion_data.investigacion_id)
        .first()
    )

    if not investigacion:
        raise HTTPException(404, "Investigación no encontrada")

    nueva = models.Sesion(**sesion_data.dict(exclude_unset=True))
    db.add(nueva)
    db.commit()
    db.refresh(nueva)

    db.add(models.LogEvento(
        tipo_evento="crear_sesion",
        descripcion=f"Sesión creada en plancha {nueva.plancha_id}",
        usuario_ldap=nueva.usuario_ldap
    ))
    db.commit()

    return nueva


@router.put("/finalizar/{sesion_id}")
def finalizar_sesion(
    sesion_id: int,
    db: Session = Depends(get_db)
):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()

    if not sesion:
        raise HTTPException(404, "Sesión no encontrada")

    if sesion.estado != "en_progreso":
        return {"message": "Sesión ya cerrada"}

    sesion.estado = "finalizada"
    sesion.fin = datetime.now(timezone.utc)
    db.commit()

    db.add(models.LogEvento(
        tipo_evento="finalizar_sesion",
        descripcion=f"Sesión {sesion_id} finalizada",
        usuario_ldap=sesion.usuario_ldap
    ))
    db.commit()

    return {"message": "Sesión finalizada"}


@router.post("/{sesion_id}/pausas", response_model=PausaResponse)
def registrar_pausa(
    sesion_id: int,
    data: PausaCreate,
    db: Session = Depends(get_db)
):
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion:
        raise HTTPException(404, "Sesión no encontrada")

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
