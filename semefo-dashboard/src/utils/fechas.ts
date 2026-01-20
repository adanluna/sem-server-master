/**
 * Utilidades para manejo de fechas UTC y conversión a hora local
 */

/**
 * Convierte una fecha UTC (como string ISO o Date) a hora local del navegador
 * y la formatea en formato legible: dd/mm/yyyy hh:mm
 * 
 * @param fechaUtc - Fecha en formato UTC (string ISO o Date object)
 * @returns String formateado con la fecha en hora local, o "-" si es null/undefined
 * 
 * @example
 * // Si la fecha UTC es "2026-01-20T17:34:00Z" y estás en México (UTC-6)
 * formatFechaLocal("2026-01-20T17:34:00Z") // "20/01/2026 11:34"
 */
export function formatFechaLocal(fechaUtc: string | Date | null | undefined): string {
    if (!fechaUtc) return "-";

    // Parsear la fecha - JavaScript automáticamente convierte UTC a hora local
    const fecha = new Date(fechaUtc);

    // Verificar que sea una fecha válida
    if (isNaN(fecha.getTime())) return "-";

    const dia = String(fecha.getDate()).padStart(2, "0");
    const mes = String(fecha.getMonth() + 1).padStart(2, "0");
    const anio = fecha.getFullYear();
    const hora = String(fecha.getHours()).padStart(2, "0");
    const min = String(fecha.getMinutes()).padStart(2, "0");

    return `${dia}/${mes}/${anio} ${hora}:${min}`;
}

/**
 * Convierte una fecha UTC a formato corto (solo fecha): dd/mm/yyyy
 * 
 * @param fechaUtc - Fecha en formato UTC
 * @returns String formateado solo con la fecha
 */
export function formatFechaCorta(fechaUtc: string | Date | null | undefined): string {
    if (!fechaUtc) return "-";

    const fecha = new Date(fechaUtc);
    if (isNaN(fecha.getTime())) return "-";

    const dia = String(fecha.getDate()).padStart(2, "0");
    const mes = String(fecha.getMonth() + 1).padStart(2, "0");
    const anio = fecha.getFullYear();

    return `${dia}/${mes}/${anio}`;
}

/**
 * Convierte una fecha UTC a formato de hora: hh:mm
 * 
 * @param fechaUtc - Fecha en formato UTC
 * @returns String formateado solo con la hora
 */
export function formatHoraLocal(fechaUtc: string | Date | null | undefined): string {
    if (!fechaUtc) return "-";

    const fecha = new Date(fechaUtc);
    if (isNaN(fecha.getTime())) return "-";

    const hora = String(fecha.getHours()).padStart(2, "0");
    const min = String(fecha.getMinutes()).padStart(2, "0");

    return `${hora}:${min}`;
}

/**
 * Convierte una fecha UTC a formato relativo ("hace 2 horas", "ayer", etc.)
 * 
 * @param fechaUtc - Fecha en formato UTC
 * @returns String con el tiempo relativo
 */
export function formatFechaRelativa(fechaUtc: string | Date | null | undefined): string {
    if (!fechaUtc) return "-";

    const fecha = new Date(fechaUtc);
    if (isNaN(fecha.getTime())) return "-";

    const ahora = new Date();
    const diffMs = ahora.getTime() - fecha.getTime();
    const diffMinutos = Math.floor(diffMs / 60000);
    const diffHoras = Math.floor(diffMs / 3600000);
    const diffDias = Math.floor(diffMs / 86400000);

    if (diffMinutos < 1) return "ahora";
    if (diffMinutos < 60) return `hace ${diffMinutos} min`;
    if (diffHoras < 24) return `hace ${diffHoras}h`;
    if (diffDias === 1) return "ayer";
    if (diffDias < 7) return `hace ${diffDias} días`;

    return formatFechaCorta(fechaUtc);
}
