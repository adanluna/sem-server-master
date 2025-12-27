import os
from pathlib import Path

EXPEDIENTES_PATH = os.getenv(
    "EXPEDIENTES_PATH",
    "/mnt/wave/archivos_sistema_semefo"
).rstrip("/")


def parse_hhmmss_to_seconds(hhmmss: str) -> float:
    partes = hhmmss.split(":")
    h, m, s = partes
    return int(h)*3600 + int(m)*60 + float(s)


def normalizar_ruta(
    path: str | None,
    *,
    tipo: str | None = None,
    expediente: str | None = None,
    sesion_id: int | None = None
) -> str | None:
    """
    Normaliza rutas según tipo de archivo SEMEFO
    """

    if not path:
        return None

    # -------------------------
    # AUDIO / TRANSCRIPCIÓN
    # -------------------------
    if tipo in ("audio", "transcripcion"):
        if expediente and sesion_id:
            archivo = os.path.basename(path)
            return f"{EXPEDIENTES_PATH}/{expediente}/{sesion_id}/{archivo}"

    # -------------------------
    # YA ES ABSOLUTA
    # -------------------------
    if path.startswith("/"):
        return path

    # -------------------------
    # RELATIVA → EXPEDIENTES
    # -------------------------
    return f"{EXPEDIENTES_PATH}/{path.lstrip('/')}"


def size_kb(path: str | None) -> float:
    """
    Calcula tamaño en KB de forma segura
    """
    if not path:
        return 0.0

    try:
        p = Path(path)
        if p.exists() and p.is_file():
            return round(p.stat().st_size / 1024, 2)
    except Exception:
        pass

    return 0.0


def ruta_red(path_abs: str | None) -> str | None:
    """
    Convierte ruta /mnt/wave/... → Wisenet_WAVE_Media/...
    """
    if not path_abs:
        return None

    if path_abs.startswith("/mnt/wave/"):
        return path_abs.replace("/mnt/wave/", "Wisenet_WAVE_Media/")

    return path_abs
