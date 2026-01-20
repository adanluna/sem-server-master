function normalizeIsoUtc(input: string | Date): string | Date {
    if (input instanceof Date) return input;

    const s = input.trim();

    // Si ya trae zona (Z u offset), se deja
    if (/(Z|[+-]\d{2}:\d{2})$/.test(s)) return s;

    // Si es ISO sin zona: "YYYY-MM-DDTHH:MM:SS(.ffffff)"
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$/.test(s)) {
        // recorta microsegundos a milisegundos
        const [base, frac] = s.split(".");
        if (!frac) return `${s}Z`;
        const ms = frac.padEnd(3, "0").slice(0, 3);
        return `${base}.${ms}Z`;
    }

    return s;
}

export function formatFechaLocal(fechaUtc: string | Date | null | undefined): string {
    if (!fechaUtc) return "-";

    const normalized = normalizeIsoUtc(fechaUtc);
    const fecha = new Date(normalized as any);
    if (isNaN(fecha.getTime())) return "-";

    const dia = String(fecha.getDate()).padStart(2, "0");
    const mes = String(fecha.getMonth() + 1).padStart(2, "0");
    const anio = fecha.getFullYear();
    const hora = String(fecha.getHours()).padStart(2, "0");
    const min = String(fecha.getMinutes()).padStart(2, "0");

    return `${dia}/${mes}/${anio} ${hora}:${min}`;
}
