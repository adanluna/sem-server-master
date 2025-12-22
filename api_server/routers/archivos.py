from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from api_server.database import get_db
import models
from schemas import (
    SesionArchivoCreate,
    SesionArchivoResponse,
    SesionArchivoEstadoUpdate
)

router = APIRouter()


@router.post("/", response_model=SesionArchivoResponse)
def registrar_archivo(
    data: SesionArchivoCreate,
    db: Session = Depends(get_db)
):
    archivo = models.SesionArchivo(**data.dict())
    db.add(archivo)
    db.commit()
    db.refresh(archivo)
    return archivo


@router.get("/sesiones/{sesion_id}/archivos", response_model=list[SesionArchivoResponse])
def listar_archivos(
    sesion_id: int,
    db: Session = Depends(get_db)
):
    return (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion_id)
        .all()
    )


@router.put("/{sesion_id}/{tipo}/actualizar_estado")
def actualizar_estado_archivo(
    sesion_id: int,
    tipo: str,
    data: SesionArchivoEstadoUpdate,
    db: Session = Depends(get_db)
):
    archivo = (
        db.query(models.SesionArchivo)
        .filter_by(sesion_id=sesion_id, tipo_archivo=tipo)
        .first()
    )

    if not archivo:
        raise HTTPException(404, "Archivo no encontrado")

    archivo.estado = data.estado
    archivo.mensaje = data.mensaje
    archivo.fecha_finalizacion = datetime.now(timezone.utc)

    if data.ruta_convertida:
        archivo.ruta_convertida = data.ruta_convertida

    db.commit()
    return {"message": "Archivo actualizado"}
