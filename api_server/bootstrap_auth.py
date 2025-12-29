import os
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from api_server.database import SessionLocal
from api_server import models
from dotenv import load_dotenv
load_dotenv(".env")

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

DASH_USER = os.getenv("BOOTSTRAP_DASH_USER", "admin")
DASH_PASS = os.getenv("BOOTSTRAP_DASH_PASS", "")
WORKER_CLIENT_ID = os.getenv("BOOTSTRAP_WORKER_CLIENT_ID", "worker_master")
WORKER_CLIENT_SECRET = os.getenv(
    "BOOTSTRAP_WORKER_CLIENT_SECRET", "")
WHISPER_CLIENT_ID = os.getenv("BOOTSTRAP_WHISPER_CLIENT_ID", "worker_whisper")
WHISPER_CLIENT_SECRET = os.getenv(
    "BOOTSTRAP_WHISPER_CLIENT_SECRET", "")


def main():
    db: Session = SessionLocal()

    # Dashboard admin
    u = db.query(models.DashboardUser).filter_by(username=DASH_USER).first()
    if not u:
        u = models.DashboardUser(
            username=DASH_USER,
            password_hash=pwd.hash(DASH_PASS),
            roles="dashboard_admin,dashboard_read",
            activo=True
        )
        db.add(u)
        print(f"[OK] dashboard user creado: {DASH_USER}")
    else:
        print(f"[SKIP] dashboard user ya existe: {DASH_USER}")

    # Worker master client
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
