"""Estados válidos de sesiones (enum PostgreSQL estado_sesion_enum)."""

from __future__ import annotations

ESTADOS_SESION_VALIDOS = frozenset({
    "procesando",
    "pausada",
    "finalizada",
    "error",
})


def validar_estado_sesion(estado: str) -> str:
    """Normaliza y valida un estado de sesión. Lanza ValueError si es inválido."""
    if not isinstance(estado, str):
        raise ValueError(
            f"Estado de sesión debe ser texto, recibido: {type(estado).__name__}"
        )

    normalizado = estado.strip().lower()
    if normalizado not in ESTADOS_SESION_VALIDOS:
        permitidos = ", ".join(sorted(ESTADOS_SESION_VALIDOS))
        raise ValueError(
            f"Estado de sesión inválido: {estado!r}. "
            f"Valores permitidos: {permitidos}"
        )
    return normalizado


def asignar_estado_sesion(sesion, estado: str) -> None:
    """Asigna estado a una fila Sesion tras validar contra el enum."""
    sesion.estado = validar_estado_sesion(estado)
