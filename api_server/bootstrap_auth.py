import os
from api_server.database import SessionLocal
from api_server import models
from api_server.utils.jwt import pwd_context


def clean(v: str) -> str:
    if not v:
        return ""
    v = v.strip()
    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
        v = v[1:-1]
    return v.strip()


WORKER_CLIENT_ID = clean(os.getenv("WORKER_CLIENT_ID", "worker_master"))
WORKER_CLIENT_SECRET = clean(os.getenv("WORKER_CLIENT_SECRET", ""))

WHISPER_CLIENT_ID = clean(os.getenv("WHISPER_CLIENT_ID", "worker_whisper"))
WHISPER_CLIENT_SECRET = clean(os.getenv("WHISPER_CLIENT_SECRET", ""))

if not WORKER_CLIENT_SECRET:
    raise SystemExit(
        "[FATAL] WORKER_CLIENT_SECRET vacío en el contenedor fastapi")
if not WHISPER_CLIENT_SECRET:
    raise SystemExit(
        "[FATAL] WHISPER_CLIENT_SECRET vacío en el contenedor fastapi")

db = SessionLocal()


def upsert(client_id, secret, roles="worker"):
    c = db.query(models.ServiceClient).filter_by(client_id=client_id).first()
    if not c:
        c = models.ServiceClient(client_id=client_id, activo=True, roles=roles)
        db.add(c)
        db.flush()
        print("[OK] creado:", client_id)
    else:
        print("[OK] existe:", client_id)

    c.client_secret_hash = pwd_context.hash(secret)
    c.activo = True
    c.roles = roles
    print("[OK] secret rehasheado:", client_id)


upsert(WORKER_CLIENT_ID, WORKER_CLIENT_SECRET, "worker")
upsert(WHISPER_CLIENT_ID, WHISPER_CLIENT_SECRET, "worker")

db.commit()
db.close()
print("[DONE] Rehash completado.")
