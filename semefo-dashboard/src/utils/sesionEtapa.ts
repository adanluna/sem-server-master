/** Etapa operativa de sesión (alineada con api_server/utils/sesion_display.py) */

export type SesionEtapa =
    | "creada"
    | "grabando"
    | "pausada"
    | "sin_procesar"
    | "pipeline"
    | "finalizada"
    | "error"
    | "abierta";

export function etapaBadgeClass(etapa: string | undefined): string {
    switch (etapa) {
        case "finalizada":
            return "bg-success";
        case "error":
            return "bg-danger";
        case "pausada":
            return "bg-warning text-dark";
        case "grabando":
            return "bg-primary";
        case "pipeline":
            return "bg-info text-dark";
        case "sin_procesar":
            return "bg-secondary";
        case "creada":
            return "bg-light text-dark border";
        default:
            return "bg-secondary";
    }
}

/** Badge por estado crudo en BD (fallback) */
export function estadoBadgeClass(estado: string | undefined): string {
    switch (estado) {
        case "finalizada":
            return "bg-success";
        case "error":
            return "bg-danger";
        case "pausada":
            return "bg-warning text-dark";
        case "procesando":
            return "bg-info text-dark";
        default:
            return "bg-secondary";
    }
}

export function etapaLabel(row: {
    etapa_label?: string;
    etapa?: string;
    estado?: string;
}): string {
    if (row.etapa_label) return row.etapa_label;
    if (row.estado) return row.estado;
    return "—";
}

export function etapaKey(row: {
    etapa?: string;
    estado?: string;
}): string {
    return row.etapa || row.estado || "";
}
