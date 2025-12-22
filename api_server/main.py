from fastapi import FastAPI

from api_server.database import engine
from api_server from api_server import models

from api_server.routers import (
    health,
    investigaciones,
    sesiones,
    archivos,
    jobs,
    ldap,
    whisper,
    infra,
    dashboard
)

# Crear tablas (solo en arranque)
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
app.include_router(ldap.router, prefix="/auth")
app.include_router(whisper.router, prefix="/whisper")
app.include_router(infra.router, prefix="/infra")
app.include_router(dashboard.router, prefix="/dashboard")
