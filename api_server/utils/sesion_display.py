"""Etiquetas legibles de etapa de sesión para el dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def compute_etapa_sesion(
    *,
    estado: str | None,
    inicio: datetime | None = None,
    fin: datetime | None = None,
    tiene_payload: bool = False,
    jobs_total: int = 0,
    jobs_error: int = 0,
) -> dict[str, str]:
    """
    Devuelve etapa (clave interna) y etapa_label (texto UI).
    No confundir estado BD (enum) con etapa operativa.
    """
    estado_norm = (estado or "").strip().lower()
    jobs_total = int(jobs_total or 0)
    jobs_error = int(jobs_error or 0)

    if estado_norm == "finalizada":
        return {"etapa": "finalizada", "etapa_label": "Finalizada"}

    if estado_norm == "error" or jobs_error > 0:
        return {"etapa": "error", "etapa_label": "Con error"}

    if estado_norm == "pausada":
        if not inicio:
            return {"etapa": "creada", "etapa_label": "Creada (sin grabar)"}
        if inicio and not fin:
            return {"etapa": "pausada", "etapa_label": "Pausada (grabando)"}
        return {"etapa": "pausada", "etapa_label": "Pausada"}

    # procesando u otro abierto
    if not inicio:
        return {"etapa": "creada", "etapa_label": "Creada (sin grabar)"}
    if inicio and not fin:
        return {"etapa": "grabando", "etapa_label": "Grabando"}
    if fin and not tiene_payload and jobs_total == 0:
        return {"etapa": "sin_procesar", "etapa_label": "Grabada · sin procesar"}
    if tiene_payload or jobs_total > 0:
        return {"etapa": "pipeline", "etapa_label": "En pipeline"}

    return {"etapa": "abierta", "etapa_label": "Abierta"}


def enrich_sesion_resumen(row: dict[str, Any]) -> dict[str, Any]:
    """Añade etapa / etapa_label a una fila del resumen del dashboard."""
    out = dict(row)
    extra = compute_etapa_sesion(
        estado=out.get("estado"),
        inicio=out.get("inicio"),
        fin=out.get("fin"),
        tiene_payload=bool(out.get("tiene_payload")),
        jobs_total=out.get("jobs_total") or 0,
        jobs_error=out.get("jobs_error") or 0,
    )
    out.update(extra)
    return out
