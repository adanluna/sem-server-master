from fastapi import FastAPI
from database import engine
import models

from routers import (
    health,
    investigaciones,
    sesiones,
    archivos,
    jobs,
    planchas,
    ldap,
    whisper,
    infra,
    dashboard
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema Forense SEMEFO",
    version="1.0.0"
)

app.include_router(health.router)
app.include_router(investigaciones.router, prefix="/investigaciones")
app.include_router(sesiones.router, prefix="/sesiones")
app.include_router(archivos.router, prefix="/archivos")
app.include_router(jobs.router, prefix="/jobs")
app.include_router(planchas.router, prefix="/planchas")
app.include_router(ldap.router, prefix="/auth")
app.include_router(whisper.router, prefix="/whisper")
app.include_router(infra.router, prefix="/infra")
app.include_router(dashboard.router, prefix="/dashboard")
