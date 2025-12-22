from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api_server.database import get_db
from api_server.services.dashboard_service import (
    dashboard_expedientes,
    dashboard_sesiones,
    dashboard_jobs
)

router = APIRouter()


@router.get("/expedientes")
def expedientes(desde, hasta, page=1, per_page=20, db: Session = Depends(get_db)):
    return dashboard_expedientes(desde, hasta, page, per_page, db)


@router.get("/sesiones")
def sesiones(desde, hasta, page=1, per_page=25, db: Session = Depends(get_db)):
    return dashboard_sesiones(desde, hasta, page, per_page, db)


@router.get("/jobs")
def jobs(estado, page=1, per_page=50, db: Session = Depends(get_db)):
    return dashboard_jobs(estado, page, per_page, db)
