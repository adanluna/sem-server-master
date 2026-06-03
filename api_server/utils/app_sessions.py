"""Sesiones de app (operador LDAP / tablet): login único, heartbeat, timeout."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api_server import models
from api_server.utils.sesion_estado import asignar_estado_sesion
from api_server.utils.sesion_procesamiento import finalizar_sesion_por_takeover_tablet

APP_SESSION_STALE_MINUTES = int(os.getenv("APP_SESSION_STALE_MINUTES", "30"))
# Si 0/false: no cerrar sesiones idle por timeout en background (logout manual o admin).
APP_SESSION_AUTO_CLOSE_IDLE = os.getenv("APP_SESSION_AUTO_CLOSE_IDLE", "0") == "1"
APP_SESSION_STATE_IDLE = "idle"
APP_SESSION_STATE_RECORDING = "recording"

REVOKE_LOGOUT = "logout"
REVOKE_TAKEOVER = "takeover"
REVOKE_TIMEOUT = "timeout"
REVOKE_ADMIN = "admin"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def is_session_stale(row: models.AppUserSession) -> bool:
    hb = _ensure_aware(row.last_heartbeat_at)
    if hb is None:
        return True
    return (_now_utc() - hb) > timedelta(minutes=APP_SESSION_STALE_MINUTES)


def pause_sesion_forensic(db: Session, sesion_id: int | None, note: str) -> None:
    if not sesion_id:
        return
    sesion = db.query(models.Sesion).filter_by(id=sesion_id).first()
    if not sesion or sesion.estado == "finalizada":
        return
    asignar_estado_sesion(sesion, "pausada")
    sesion.ultima_actualizacion = _now_utc()
    extra = note.strip()
    if extra:
        prev = (sesion.observaciones or "").strip()
        sesion.observaciones = f"{prev}\n{extra}".strip() if prev else extra
    db.commit()


def revoke_ldap_refresh_tokens(db: Session, username: str) -> int:
    subject = f"ldap:{username}"
    now = _now_utc()
    rows = (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.subject == subject,
            models.RefreshToken.revoked_at.is_(None),
        )
        .all()
    )
    for row in rows:
        row.revoked_at = now
    if rows:
        db.commit()
    return len(rows)


def get_active_app_session(db: Session, username: str) -> models.AppUserSession | None:
    return (
        db.query(models.AppUserSession)
        .filter(
            models.AppUserSession.usuario_ldap == username,
            models.AppUserSession.revoked_at.is_(None),
        )
        .order_by(models.AppUserSession.logged_in_at.desc())
        .first()
    )


def get_active_app_session_for_tablet(
    db: Session, tablet_id: str
) -> models.AppUserSession | None:
    return (
        db.query(models.AppUserSession)
        .filter(
            models.AppUserSession.tablet_id == tablet_id,
            models.AppUserSession.revoked_at.is_(None),
        )
        .order_by(models.AppUserSession.logged_in_at.desc())
        .first()
    )


def close_app_session(
    db: Session,
    row: models.AppUserSession,
    *,
    reason: str,
    revoked_by: str | None = None,
    pause_sesion: bool = True,
) -> None:
    if row.revoked_at is not None:
        return
    row.revoked_at = _now_utc()
    row.revoke_reason = reason
    row.revoked_by = revoked_by
    db.commit()

    if pause_sesion and row.sesion_id:
        pause_sesion_forensic(
            db,
            row.sesion_id,
            f"Pausada automáticamente ({reason}).",
        )

    revoke_ldap_refresh_tokens(db, row.usuario_ldap)


def close_stale_sessions(db: Session) -> int:
    """
    Cierra sesiones idle abandonadas (sin heartbeat reciente).
    Nunca cierra sesiones en estado recording (operador grabando).
    Desactivado por defecto (APP_SESSION_AUTO_CLOSE_IDLE=0).
    """
    if not APP_SESSION_AUTO_CLOSE_IDLE:
        return 0

    cutoff = _now_utc() - timedelta(minutes=APP_SESSION_STALE_MINUTES)
    stale = (
        db.query(models.AppUserSession)
        .filter(
            models.AppUserSession.revoked_at.is_(None),
            models.AppUserSession.estado != APP_SESSION_STATE_RECORDING,
            models.AppUserSession.last_heartbeat_at < cutoff,
        )
        .all()
    )
    count = 0
    for row in stale:
        close_app_session(db, row, reason=REVOKE_TIMEOUT, pause_sesion=True)
        count += 1
    return count


def app_session_to_dict(row: models.AppUserSession) -> dict:
    sesion = row.sesion
    inv = sesion.investigacion if sesion else None
    return {
        "id": row.id,
        "usuario_ldap": row.usuario_ldap,
        "tablet_id": row.tablet_id,
        "estado": row.estado,
        "sesion_id": row.sesion_id,
        "numero_expediente": inv.numero_expediente if inv else None,
        "nombre_sesion": sesion.nombre_sesion if sesion else None,
        "last_heartbeat_at": row.last_heartbeat_at,
        "logged_in_at": row.logged_in_at,
        "is_stale": is_session_stale(row),
        "can_admin_revoke": row.estado != APP_SESSION_STATE_RECORDING,
    }


def resolve_login_conflict(
    db: Session,
    username: str,
    tablet_id: str,
    force_takeover: bool = False,
) -> models.AppUserSession | None:
    """
    Resuelve conflictos de login.
    force_takeover solo aplica para TABLET_SESSION_ACTIVE (otro usuario en esta tablet).
    Nunca permite takeover remoto (SESSION_ACTIVE_ELSEWHERE).
    """
    close_stale_sessions(db)

    existing_user = get_active_app_session(db, username)
    if existing_user and existing_user.tablet_id == tablet_id:
        return existing_user

    if existing_user and existing_user.tablet_id != tablet_id:
        # Mismo usuario en otra tablet: bloquear (sin takeover remoto).
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SESSION_ACTIVE_ELSEWHERE",
                "message": (
                    f"Ya hay una sesión activa en la tablet {existing_user.tablet_id}. "
                    "Cierre sesión en esa tablet antes de iniciar aquí."
                ),
                "tablet_id": existing_user.tablet_id,
                "sesion_id": existing_user.sesion_id,
                "can_takeover": False,
            },
        )

    occupied_tablet = get_active_app_session_for_tablet(db, tablet_id)
    if occupied_tablet and occupied_tablet.usuario_ldap != username:
        recording = occupied_tablet.estado == APP_SESSION_STATE_RECORDING
        if force_takeover:
            if recording and occupied_tablet.sesion_id:
                processed = finalizar_sesion_por_takeover_tablet(
                    db, occupied_tablet.sesion_id
                )
                if not processed:
                    pause_sesion_forensic(
                        db,
                        occupied_tablet.sesion_id,
                        "Pausada por takeover de tablet (sin datos para procesar).",
                    )
            close_app_session(
                db,
                occupied_tablet,
                reason=REVOKE_TAKEOVER,
                pause_sesion=False,
            )
            return None

        msg = (
            f"Esta tablet tiene una sesión activa del usuario "
            f"{occupied_tablet.usuario_ldap}."
        )
        if recording:
            msg += (
                " Hay una grabación en curso que se finalizará y enviará "
                "a procesar si cierra esa sesión."
            )
        msg += " ¿Desea cerrarla e iniciar sesión aquí?"

        raise HTTPException(
            status_code=409,
            detail={
                "code": "TABLET_SESSION_ACTIVE",
                "message": msg,
                "tablet_id": tablet_id,
                "usuario_ldap": occupied_tablet.usuario_ldap,
                "sesion_id": occupied_tablet.sesion_id,
                "is_recording": recording,
                "can_takeover": True,
            },
        )

    return None


def create_or_refresh_app_session(
    db: Session,
    *,
    username: str,
    tablet_id: str,
    existing: models.AppUserSession | None,
) -> models.AppUserSession:
    now = _now_utc()
    if existing and existing.tablet_id == tablet_id and existing.revoked_at is None:
        existing.last_heartbeat_at = now
        if existing.estado != APP_SESSION_STATE_RECORDING:
            existing.estado = APP_SESSION_STATE_IDLE
        db.commit()
        db.refresh(existing)
        return existing

    row = models.AppUserSession(
        usuario_ldap=username,
        tablet_id=tablet_id,
        estado=APP_SESSION_STATE_IDLE,
        last_heartbeat_at=now,
        logged_in_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_heartbeat(
    db: Session,
    session_id: int,
    *,
    tablet_id: str,
    estado: str,
    sesion_id: int | None,
) -> models.AppUserSession:
    row = db.query(models.AppUserSession).filter_by(id=session_id).first()
    if not row or row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Sesión de app inválida o cerrada")

    if row.tablet_id != tablet_id:
        raise HTTPException(status_code=403, detail="Tablet no coincide con la sesión")

    row.last_heartbeat_at = _now_utc()
    if estado == APP_SESSION_STATE_RECORDING:
        row.estado = APP_SESSION_STATE_RECORDING
        row.sesion_id = sesion_id
    else:
        row.estado = APP_SESSION_STATE_IDLE
        if sesion_id is not None:
            row.sesion_id = sesion_id

    db.commit()
    db.refresh(row)
    return row


def validate_app_session_for_token(
    db: Session,
    *,
    username: str,
    app_session_id: int | None,
    tablet_id: str | None,
) -> None:
    if not app_session_id:
        return
    row = db.query(models.AppUserSession).filter_by(id=app_session_id).first()
    if not row or row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Sesión de app cerrada")
    if row.usuario_ldap != username:
        raise HTTPException(status_code=403, detail="Sesión de app inválida")
    if tablet_id and row.tablet_id != tablet_id:
        raise HTTPException(status_code=403, detail="Sesión de app en otra tablet")
    # No cerrar por timeout automático: solo logout manual o revocación admin.
