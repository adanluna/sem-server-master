"""Comprobaciones de grabador Hanwha y montaje /mnt/wave (master + reporte whisper)."""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone, timedelta
from typing import Any, TYPE_CHECKING
from urllib.parse import urlparse

from api_server.utils.ping import _ping_probe

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

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
WHISPER_MOUNT_STALE_MINUTES = int(os.getenv("WHISPER_MOUNT_STALE_MINUTES", "2"))
WHISPER_MOUNT_HTTP_STALE_MINUTES = int(
    os.getenv(
        "WHISPER_MOUNT_HTTP_STALE_MINUTES",
        os.getenv("WHISPER_MOUNT_STALE_MINUTES", "2"),
    )
)


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


def _whisper_base_no_reporte() -> dict[str, Any]:
    return {
        "mount_point": WAVE_MOUNT,
        "mounted": False,
        "readable": False,
        "status": "sin_reporte",
        "reported_at": None,
        "message": "Sin reporte desde servidor Whisper",
        "ok": False,
        "source": None,
    }


def _parse_reported_at(reported_at: Any) -> datetime | None:
    if not reported_at:
        return None
    try:
        raw = str(reported_at).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _is_report_stale(reported_at: Any, max_minutes: int) -> bool:
    dt = _parse_reported_at(reported_at)
    if dt is None:
        return True
    age = datetime.now(timezone.utc) - dt
    return age > timedelta(minutes=max_minutes)


def read_whisper_mount_from_db(db: Session | None) -> dict[str, Any] | None:
    if db is None:
        return None
    try:
        from api_server import models

        row = (
            db.query(models.WhisperMountReport)
            .order_by(models.WhisperMountReport.fecha.desc())
            .first()
        )
    except Exception:
        return None
    if not row:
        return None

    ra = row.reported_at or row.fecha
    reported_at = ra.isoformat() if ra else None
    ok = bool(row.ok)
    return {
        "mount_point": row.mount_point,
        "probe_path": row.probe_path,
        "mounted": bool(row.mounted),
        "readable": bool(row.readable),
        "status": "ok" if ok else "error",
        "reported_at": reported_at,
        "message": row.message or ("ok" if ok else "Montaje whisper no disponible"),
        "ok": ok,
        "source": "http",
    }


def _read_whisper_mount_file() -> dict[str, Any]:
    path = WHISPER_MOUNT_REPORT
    base = _whisper_base_no_reporte()

    if not os.path.isfile(path):
        return base

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        out = dict(base)
        out["status"] = "error_lectura"
        out["message"] = f"No se pudo leer reporte whisper: {e}"
        out["source"] = "file"
        return out

    reported_at = data.get("reported_at") or data.get("timestamp")
    mounted = bool(data.get("mounted"))
    readable = bool(data.get("readable"))
    stale = _is_report_stale(reported_at, WHISPER_MOUNT_STALE_MINUTES)

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
        "source": "file",
    }


def resolve_whisper_mount_status(db: Session | None = None) -> dict[str, Any]:
    """
    Combina reporte HTTP (BD) y JSON en share.
    Prioriza HTTP reciente; no confía en JSON OK si HTTP dejó de llegar.
    """
    http = read_whisper_mount_from_db(db)
    file = _read_whisper_mount_file()

    http_fresh = http is not None and not _is_report_stale(
        http.get("reported_at"), WHISPER_MOUNT_HTTP_STALE_MINUTES
    )
    file_fresh = file.get("status") not in (
        "sin_reporte",
        "error_lectura",
    ) and not _is_report_stale(file.get("reported_at"), WHISPER_MOUNT_STALE_MINUTES)

    if http_fresh:
        out = dict(http)
        out["status"] = "ok" if http.get("ok") else "error"
        return out

    http_stale_but_present = http is not None and not http_fresh

    if file.get("ok") and file_fresh and http_stale_but_present:
        return {
            "mount_point": file.get("mount_point", WAVE_MOUNT),
            "mounted": file.get("mounted", False),
            "readable": file.get("readable", False),
            "status": "stale",
            "reported_at": file.get("reported_at"),
            "message": (
                "Montaje whisper sin confirmación HTTP reciente "
                "(reporte JSON posiblemente obsoleto)"
            ),
            "ok": False,
            "source": "merged",
            "file_reported_at": file.get("reported_at"),
            "http_reported_at": http.get("reported_at"),
        }

    if http is not None:
        out = dict(http)
        out["status"] = "stale"
        out["ok"] = False
        if not out.get("message") or out.get("ok"):
            out["message"] = "Reporte HTTP whisper desactualizado"
        return out

    return file


def read_whisper_mount_report(db: Session | None = None) -> dict[str, Any]:
    """Compat: delega en resolve_whisper_mount_status."""
    return resolve_whisper_mount_status(db)


def build_wave_mount_status(db: Session | None = None) -> dict[str, Any]:
    return {
        "master": check_wave_mount_local(),
        "whisper": resolve_whisper_mount_status(db),
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
    if not whisper.get("ok"):
        return False
    if whisper.get("status") in ("error", "stale", "sin_reporte", "error_lectura"):
        return False
    if camaras_offline > 0:
        return False
    return True


def build_infraestructura_extra(
    *,
    timeout: int = 1,
    retries: int = 2,
    camaras_offline: int = 0,
    db: Session | None = None,
) -> dict[str, Any]:
    grabador = check_grabador(timeout=timeout, retries=retries)
    wave_mount = build_wave_mount_status(db)
    infra_ok = compute_infra_ok(
        grabador, wave_mount, camaras_offline=camaras_offline
    )
    return {
        "grabador": grabador,
        "wave_mount": wave_mount,
        "infra_ok": infra_ok,
    }
