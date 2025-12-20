from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import InfraEstadoCreate
from services.infra_service import (
    registrar_estado,
    obtener_estado_actual,
    dashboard_estado
)

router = APIRouter()


@router.post("/estado")
def registrar(data: InfraEstadoCreate, db: Session = Depends(get_db)):
    return registrar_estado(data, db)


@router.get("/estado/ultimo")
def ultimo(db: Session = Depends(get_db)):
    return obtener_estado_actual(db)


@router.get("/estado")
def dashboard(db: Session = Depends(get_db)):
    return dashboard_estado(db)
