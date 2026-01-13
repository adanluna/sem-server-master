import os
from pathlib import Path

EXPEDIENTES_PATH = os.getenv(
    "EXPEDIENTES_PATH",
    "/mnt/wave/archivos_sistema_semefo"
).rstrip("/")

# Para exponer ruta pública (lo que quieres en el JSON)
WAVE_MOUNT = os.getenv("WAVE_MOUNT", "/mnt/wave").rstrip("/")
WINDOWS_WAVE_SHARE = os.getenv(
    "WINDOWS_WAVE_SHARE", "//172.21.82.4/Wisenet_WAVE_Media").strip()
EXPEDIENTES_PATH = os.getenv(
    "EXPEDIENTES_PATH", "/mnt/wave/archivos_sistema_semefo").rstrip("/")

# Raíz del mount local (en master normalmente /mnt/wave)
SMB_MOUNT = os.getenv("SMB_MOUNT", "/mnt/wave").rstrip("/")


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
    Normaliza rutas según tipo de archivo SEMEFO.
    - Si ya es absoluta (/...), se respeta.
    - Si es relativa, se cuelga de EXPEDIENTES_PATH.
    - Para audio/transcripcion, si expediente+sesion_id vienen, fuerza /EXPEDIENTES/exp/sesion/archivo
    """
    if not path:
        return None

    path = str(path).strip()

    # -------------------------
    # YA ES ABSOLUTA
    # -------------------------
    if path.startswith("/"):
        return path

    # -------------------------
    # AUDIO / TRANSCRIPCIÓN
    # -------------------------
    if tipo in ("audio", "transcripcion"):
        if expediente and sesion_id:
            archivo = os.path.basename(path)
            return f"{EXPEDIENTES_PATH}/{expediente}/{sesion_id}/{archivo}"

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


def _share_base() -> str:
    """
    Convierte:
      //172.21.82.4/Wisenet_WAVE_Media  ->  172.21.82.4/Wisenet_WAVE_Media
      \\\\172.21.82.4\\Wisenet_WAVE_Media -> 172.21.82.4/Wisenet_WAVE_Media
    """
    s = WINDOWS_WAVE_SHARE.replace("\\", "/").strip()
    while s.startswith("/"):
        s = s[1:]
    # ahora debe ser: 172.21.82.4/Wisenet_WAVE_Media
    return s.rstrip("/")


def ruta_red(path_any: str | None) -> str | None:
    """
    Convierte rutas internas a la forma pública:

    - /mnt/wave/archivos_sistema_semefo/exp09/1/video.webm
      -> 172.21.82.4/Wisenet_WAVE_Media/archivos_sistema_semefo/exp09/1/video.webm

    - exp09/1/audio.m4a
      -> 172.21.82.4/Wisenet_WAVE_Media/archivos_sistema_semefo/exp09/1/audio.m4a
    """
    if not path_any:
        return None

    p = str(path_any).strip()
    base = _share_base()

    # A) Absoluta dentro del mount /mnt/wave/...
    if p.startswith(WAVE_MOUNT + "/"):
        rel = p[len(WAVE_MOUNT):].lstrip("/")  # quita /mnt/wave/
        return f"{base}/{rel}"

    # B) Absoluta dentro de EXPEDIENTES_PATH (por si cambia WAVE_MOUNT)
    if p.startswith(EXPEDIENTES_PATH + "/"):
        # Queremos que quede bajo /archivos_sistema_semefo/...
        idx = p.find("/archivos_sistema_semefo/")
        if idx != -1:
            rel = p[idx+1:]  # quita el primer "/"
            return f"{base}/{rel}"

        # fallback: cuelga del share tal cual (menos ideal)
        rel = p.lstrip("/")
        return f"{base}/{rel}"

    # C) Relativa (exp09/1/audio.m4a o archivos_sistema_semefo/exp09/1/...)
    rel = p.lstrip("/")
    if rel.startswith("archivos_sistema_semefo/"):
        return f"{base}/{rel}"

    return f"{base}/archivos_sistema_semefo/{rel}"
