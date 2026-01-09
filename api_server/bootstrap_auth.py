import os
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from api_server.database import SessionLocal
from api_server import models
from dotenv import load_dotenv

load_dotenv(".env")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

DASH_USER = os.getenv("DASH_USER", "admin")
DASH_PASS = os.getenv("DASH_PASS", "").strip()

WORKER_CLIENT_ID = os.getenv("WORKER_CLIENT_ID", "worker_master")
WORKER_CLIENT_SECRET = os.getenv("WORKER_CLIENT_SECRET", "").strip()

WHISPER_CLIENT_ID = os.getenv("WHISPER_CLIENT_ID", "worker_whisper")
WHISPER_CLIENT_SECRET = os.getenv("WHISPER_CLIENT_SECRET", "").strip()


def must(value: str, name: str):
    if not value:
        raise SystemExit(f"[FATAL] Falta {name} en .env o está vacío.")
    return value


def looks_like_bcrypt(h: str) -> bool:
    return h.startswith("$2a$") or h.startswith("$2b$") or h.startswith("$2y$")


def main():
    must(DASH_USER, "DASH_USER")
    must(DASH_PASS, "DASH_PASS")
    must(WORKER_CLIENT_ID, "WORKER_CLIENT_ID")
    must(WORKER_CLIENT_SECRET, "WORKER_CLIENT_SECRET")
    must(WHISPER_CLIENT_ID, "WHISPER_CLIENT_ID")
    must(WHISPER_CLIENT_SECRET, "WHISPER_CLIENT_SECRET")

    db: Session = SessionLocal()

    # Dashboard admin
    u = db.query(models.DashboardUser).filter_by(username=DASH_USER).first()
    if not u:
        # DASH_PASS ya debe ser hash bcrypt
        if not looks_like_bcrypt(DASH_PASS):
            raise SystemExit(
                "[FATAL] DASH_PASS no parece bcrypt ($2b$...). Si quieres usar texto plano, cambia el modo del script.")
        u = models.DashboardUser(
            username=DASH_USER,
            password_hash=pwd.hash(DASH_PASS),  # 👈 NO re-hash
            roles="dashboard_admin,dashboard_read",
            activo=True
        )
        db.add(u)
        print(f"[OK] dashboard user creado: {DASH_USER}")
    else:
        print(f"[SKIP] dashboard user ya existe: {DASH_USER}")

    # Worker master client (sí hasheamos secret)
    c1 = db.query(models.ServiceClient).filter_by(
        client_id=WORKER_CLIENT_ID).first()
    if not c1:
        c1 = models.ServiceClient(
            client_id=WORKER_CLIENT_ID,
            client_secret_hash=pwd.hash(WORKER_CLIENT_SECRET),
            roles="worker",
            activo=True
        )
        db.add(c1)
        print(f"[OK] service client creado: {WORKER_CLIENT_ID}")
    else:
        print(f"[SKIP] service client ya existe: {WORKER_CLIENT_ID}")

    # Worker whisper client
    c2 = db.query(models.ServiceClient).filter_by(
        client_id=WHISPER_CLIENT_ID).first()
    if not c2:
        c2 = models.ServiceClient(
            client_id=WHISPER_CLIENT_ID,
            client_secret_hash=pwd.hash(WHISPER_CLIENT_SECRET),
            roles="worker",
            activo=True
        )
        db.add(c2)
        print(f"[OK] service client creado: {WHISPER_CLIENT_ID}")
    else:
        print(f"[SKIP] service client ya existe: {WHISPER_CLIENT_ID}")

    db.commit()
    db.close()


if __name__ == "__main__":
    main()
