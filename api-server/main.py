from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, engine
import models

# Crear tablas automáticamente en la DB si no existen
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema Forense SEMEFO",
    description="API del Sistema Integral de Grabación y Gestión de Autopsias del Gobierno del Estado de Nuevo León.",
    version="1.0.0",
    contact={
        "name": "Gobierno del Estado de Nuevo León",
        "url": "https://www.nl.gob.mx",
        "email": "soporte@nl.gob.mx",
    },
    license_info={
        "name": "Privativo Gobierno NL",
        "url": "https://www.nl.gob.mx",
    },
)


@app.get("/")
def read_root():
    return {"message": "API forense SEMEFO activa"}

# Modelo Pydantic para insertar


class InvestigacionCreate(BaseModel):
    numero_expediente: str
    nombre_carpeta: str | None = None
    observaciones: str | None = None

# Endpoint POST para crear investigación


@app.post("/investigaciones/")
def create_investigacion(invest: InvestigacionCreate, db: Session = Depends(get_db)):
    nueva = models.Investigacion(
        numero_expediente=invest.numero_expediente,
        nombre_carpeta=invest.nombre_carpeta,
        observaciones=invest.observaciones
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

# Endpoint GET para listar investigaciones


@app.get("/investigaciones/")
def list_investigaciones(db: Session = Depends(get_db)):
    return db.query(models.Investigacion).all()
