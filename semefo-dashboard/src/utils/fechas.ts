function toIsoUtc(fechaUtc: string | Date): string | Date {
    if (fechaUtc instanceof Date) return fechaUtc;

    const s = fechaUtc.trim();

    // Ya viene en ISO con Z u offset -> dejarlo
    if (/Z$/.test(s) || /[+-]\d{2}:\d{2}$/.test(s)) return s;

    // Formato típico Postgres: "YYYY-MM-DD HH:MM:SS.ffffff"
    // -> "YYYY-MM-DDTHH:MM:SS.mmmZ"
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$/.test(s)) {
        const [datePart, timePart = ""] = s.split(" ");
        const ms = (timePart.split(".")[1] || "0").padEnd(3, "0").slice(0, 3);
        const base = timePart.split(".")[0];
        return `${datePart}T${base}.${ms}Z`;
    }

    // fallback
    return s;
}

export function formatFechaLocal(fechaUtc: string | Date | null | undefined): string {
    if (!fechaUtc) return "-";

    const normalized = toIsoUtc(fechaUtc);
    const fecha = new Date(normalized as any);

    if (isNaN(fecha.getTime())) return "-";

    const dia = String(fecha.getDate()).padStart(2, "0");
    const mes = String(fecha.getMonth() + 1).padStart(2, "0");
    const anio = fecha.getFullYear();
    const hora = String(fecha.getHours()).padStart(2, "0");
    const min = String(fecha.getMinutes()).padStart(2, "0");

    return `${dia}/${mes}/${anio} ${hora}:${min}`;
}
