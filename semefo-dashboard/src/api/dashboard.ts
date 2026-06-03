import api from "./api";

export type DashboardResumen = {
    kpis: {
        total_30_dias: number;
        finalizadas: number;
        pendientes: number;
        abiertas?: number;
        errores: number;
    };
    pendientes: SesionResumenRow[];
    abiertas?: SesionResumenRow[];
    ultimas: SesionResumenRow[];
    errores: any[];
};

export type SesionResumenRow = {
    id: number;
    numero_expediente?: string;
    nombre_sesion?: string;
    plancha_nombre?: string;
    estado?: string;
    etapa?: string;
    etapa_label?: string;
    fecha?: string;
};

export async function fetchSesionProcesos(sesionId: number) {
    const { data } = await api.get(`/dashboard/jobs/sesion/${sesionId}`);
    return data;
}

export async function fetchDashboardResumen(): Promise<DashboardResumen> {
    const { data } = await api.get<DashboardResumen>("/dashboard/resumen");
    return data;
}

export async function fetchSesiones(params: {
    desde: string;
    hasta: string;
    page: number;
    per_page: number;
}) {
    const { data } = await api.get("/dashboard/sesiones", { params });
    return data;
}

export async function fetchJobs(params: {
    estado: string;
    page: number;
    per_page: number;
}) {
    const { data } = await api.get("/dashboard/jobs", { params });
    return data;
}
