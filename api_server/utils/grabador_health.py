"""Comprobaciones de grabador Hanwha y montaje /mnt/wave (master + reporte whisper)."""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import urlparse

from api_server.utils.ping import _ping_probe

GRABADOR_IP = os.getenv("GRABADOR_IP", "").strip()
WINDOWS_WAVE_SHARE = os.getenv(
    "WINDOWS_WAVE_SHARE", "//172.21.82.4/Wisenet_WAVE_Media"
).strip()
WAVE_MOUNT = os.getenv("WAVE_MOUNT", "/mnt/wave").rstrip("/")
EXPEDIENTES_PATH = os.getenv(
    "EXPEDIENTES_PATH", f"{WAVE_MOUNT}/archivos_sistema_semefo"
).rstrip("/")
GRABADOR_SMB_PORT = int(os.getenv("GRABADOR_SMB_PORT", "445"))
INFRA_CHECK_SMB_PORT = os.getenv("INFRA_CHECK_SMB_PORT", "1") == "1"
WHISPER_MOUNT_REPORT = os.getenv(
    "WHISPER_MOUNT_REPORT",
    f"{WAVE_MOUNT}/infra/wave_mount_whisper.json",
).strip()
WHISPER_MOUNT_STALE_MINUTES = int(os.getenv("WHISPER_MOUNT_STALE_MINUTES", "10"))


def grabador_ip() -> str:
    if GRABADOR_IP:
        return GRABADOR_IP
    share = WINDOWS_WAVE_SHARE.replace("\\", "/")
    if share.startswith("//"):
        host = share[2:].split("/", 1)[0]
        if host:
            return host
    parsed = urlparse(
        share if "://" in share else f"//{share.lstrip('/')}"
    )
    return parsed.hostname or "172.21.82.4"


def _tcp_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_grabador(
    *,
    timeout: int = 1,
    retries: int = 2,
) -> dict[str, Any]:
    ip = grabador_ip()
    ping = _ping_probe(ip, timeout=timeout, retries=retries)
    online = bool(ping.get("online"))
    smb_open = None
    if INFRA_CHECK_SMB_PORT:
        smb_open = _tcp_port_open(ip, GRABADOR_SMB_PORT, timeout=float(timeout + 1))

    ok = online and (smb_open is not False if INFRA_CHECK_SMB_PORT else True)
    parts = []
    if not online:
        parts.append("sin respuesta a ping")
    if INFRA_CHECK_SMB_PORT and smb_open is False:
        parts.append(f"puerto SMB {GRABADOR_SMB_PORT} cerrado")
    message = "ok" if ok else "; ".join(parts) or "no disponible"

    return {
        "ip": ip,
        "online": online,
        "smb_port_open": smb_open,
        "metodo": ping.get("metodo"),
        "message": message,
        "ok": ok,
    }


def check_wave_mount_local(
    mount_point: str | None = None,
    probe_path: str | None = None,
) -> dict[str, Any]:
    mount_point = (mount_point or WAVE_MOUNT).rstrip("/")
    probe_path = (probe_path or EXPEDIENTES_PATH).rstrip("/")

    mounted = os.path.ismount(mount_point)
    readable = False
    read_error = None

    if mounted:
        try:
            os.listdir(probe_path)
            readable = True
        except OSError as e:
            read_error = str(e)

    ok = mounted and readable
    if not mounted:
        message = f"{mount_point} no está montado"
    elif not readable:
        message = f"montado pero no legible: {read_error or probe_path}"
    else:
        message = "ok"

    return {
        "mount_point": mount_point,
        "probe_path": probe_path,
        "mounted": mounted,
        "readable": readable,
        "message": message,
        "ok": ok,
    }


def read_whisper_mount_report() -> dict[str, Any]:
    path = WHISPER_MOUNT_REPORT
    base = {
        "mount_point": WAVE_MOUNT,
        "mounted": False,
        "readable": False,
        "status": "sin_reporte",
        "reported_at": None,
        "message": "Sin reporte desde servidor Whisper",
        "ok": False,
    }

    if not os.path.isfile(path):
        return base

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        out = dict(base)
        out["status"] = "error_lectura"
        out["message"] = f"No se pudo leer reporte whisper: {e}"
        return out

    reported_at = data.get("reported_at") or data.get("timestamp")
    dt = None
    if reported_at:
        try:
            raw = str(reported_at).replace("Z", "+00:00")
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            dt = None

    mounted = bool(data.get("mounted"))
    readable = bool(data.get("readable"))
    stale = False
    if dt is not None:
        age = datetime.now(timezone.utc) - dt
        stale = age > timedelta(minutes=WHISPER_MOUNT_STALE_MINUTES)

    if stale:
        status = "stale"
        message = data.get("message") or "Reporte whisper desactualizado"
        ok = False
    elif mounted and readable:
        status = "ok"
        message = data.get("message") or "ok"
        ok = True
    else:
        status = "error"
        message = data.get("message") or "Montaje whisper no disponible"
        ok = False

    return {
        "mount_point": data.get("mount_point", WAVE_MOUNT),
        "mounted": mounted,
        "readable": readable,
        "status": status,
        "reported_at": reported_at,
        "message": message,
        "ok": ok,
    }


def build_wave_mount_status() -> dict[str, Any]:
    return {
        "master": check_wave_mount_local(),
        "whisper": read_whisper_mount_report(),
    }


def compute_infra_ok(
    grabador: dict[str, Any],
    wave_mount: dict[str, Any],
    camaras_offline: int = 0,
) -> bool:
    if not grabador.get("ok"):
        return False
    master = wave_mount.get("master") or {}
    if not master.get("ok"):
        return False
    whisper = wave_mount.get("whisper") or {}
    if whisper.get("status") in ("error", "stale", "sin_reporte"):
        return False
    if camaras_offline > 0:
        return False
    return True


def build_infraestructura_extra(
    *,
    timeout: int = 1,
    retries: int = 2,
    camaras_offline: int = 0,
) -> dict[str, Any]:
    grabador = check_grabador(timeout=timeout, retries=retries)
    wave_mount = build_wave_mount_status()
    infra_ok = compute_infra_ok(
        grabador, wave_mount, camaras_offline=camaras_offline
    )
    return {
        "grabador": grabador,
        "wave_mount": wave_mount,
        "infra_ok": infra_ok,
    }
