import os

EXPEDIENTES_PATH = os.getenv(
    "EXPEDIENTES_PATH",
    "/mnt/wave/archivos_sistema_semefo"
).rstrip("/")


def normalizar_ruta(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("/"):
        return path
    return f"{EXPEDIENTES_PATH}/{path.lstrip('/')}"
