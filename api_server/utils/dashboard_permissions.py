"""Permisos por sección del panel (/dashboard/*)."""

from __future__ import annotations

from typing import Any

ALL_PERMISSION_KEYS = (
    "dashboard",
    "sesiones",
    "sesiones_fallidas",
    "jobs",
    "planchas",
    "tokens",
    "infraestructura",
    "usuarios",
)

# Compatibilidad con tokens JWT antiguos (solo roles CSV)
_LEGACY_READ_KEYS = frozenset({"dashboard", "sesiones", "jobs", "planchas"})

PROTECTED_USERNAME = "admin"


def default_permissions() -> dict[str, bool]:
    return {k: False for k in ALL_PERMISSION_KEYS}


def full_permissions() -> dict[str, bool]:
    return {k: True for k in ALL_PERMISSION_KEYS}


def is_super_admin(username: str | None) -> bool:
    return (username or "").strip().lower() == PROTECTED_USERNAME


def username_from_sub(sub: str | None) -> str | None:
    if not sub:
        return None
    if ":" in sub:
        return sub.split(":", 1)[1]
    return sub


def normalize_permissions(raw: Any) -> dict[str, bool]:
    base = default_permissions()
    if not isinstance(raw, dict):
        return base
    for key in ALL_PERMISSION_KEYS:
        if key in raw:
            base[key] = bool(raw[key])
    return base


def permissions_from_legacy_roles(roles: list[str] | None) -> dict[str, bool]:
    roles_set = {r.strip() for r in (roles or []) if r and str(r).strip()}
    if "dashboard_admin" in roles_set:
        perms = full_permissions()
        perms["usuarios"] = False
        return perms
    if "dashboard_read" in roles_set:
        perms = default_permissions()
        for key in _LEGACY_READ_KEYS:
            perms[key] = True
        return perms
    return default_permissions()


def effective_permissions(
    *,
    username: str | None,
    permissions: Any = None,
    roles: list[str] | None = None,
) -> dict[str, bool]:
    if is_super_admin(username):
        return full_permissions()
    perms = normalize_permissions(permissions)
    if any(perms.values()):
        return perms
    if roles:
        return permissions_from_legacy_roles(roles)
    return perms


def has_permission(
    *,
    username: str | None,
    permission_key: str,
    permissions: dict[str, bool] | None = None,
    roles: list[str] | None = None,
) -> bool:
    eff = effective_permissions(
        username=username, permissions=permissions, roles=roles
    )
    return bool(eff.get(permission_key))


def principal_has_permission(principal: dict, permission_key: str) -> bool:
    username = username_from_sub(principal.get("sub"))
    perms = principal.get("permissions")
    roles = principal.get("roles") or []
    if not isinstance(roles, list):
        roles = list(roles) if roles else []
    return has_permission(
        username=username,
        permission_key=permission_key,
        permissions=normalize_permissions(perms) if isinstance(perms, dict) else None,
        roles=roles,
    )
