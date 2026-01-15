# api_server/api_app.py
from fastapi import FastAPI
from api_server.routers import api as api_router

api_app = FastAPI(
    title="SEMEFO – API Pública",
    description="Endpoints informativos para integración SEMEFO",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 👇 solo rutas /api
api_app.include_router(api_router.router)
