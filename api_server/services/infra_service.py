import os
import socket
import shutil
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from api_server import models


def registrar_estado(data, db):
    nuevo = models.InfraEstado(**data.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {"status": "ok", "id": nuevo.id}


def registrar_estado(data, db):
    nuevo = models.InfraEstado(**data.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {"status": "ok", "id": nuevo.id}


def obtener_estado_actual(db):
    rows = (
        db.query(models.InfraEstado)
        .order_by(models.InfraEstado.fecha.desc())
        .all()
    )

    salida = {}
    for r in rows:
        if r.servidor not in salida:
            salida[r.servidor] = {
                "disco_total_gb": r.disco_total_gb,
                "disco_usado_gb": r.disco_usado_gb,
                "disco_libre_gb": r.disco_libre_gb,
                "fecha": r.fecha
            }

    return salida


def dashboard_estado(db):
    estado = {
        "api": "ok",
        "db": "error",
        "rabbitmq": "error",
        "workers": {},
        "disco": {}
    }

    try:
        db.execute(text("SELECT 1"))
        estado["db"] = "ok"
    except:
        pass

    try:
        host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        sock = socket.create_connection((host, 5672), timeout=2)
        sock.close()
        estado["rabbitmq"] = "ok"
    except:
        pass

    total, used, free = shutil.disk_usage("/")
    estado["disco"]["master"] = {
        "total_gb": round(total / 1e9, 2),
        "usado_gb": round(used / 1e9, 2),
        "libre_gb": round(free / 1e9, 2)
    }

    return estado
