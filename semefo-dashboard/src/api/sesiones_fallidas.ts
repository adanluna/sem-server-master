import api from "./api";

export type SesionFallida = {
    id: number;
    numero_expediente: string | null;
    nombre_sesion: string;
    plancha_nombre: string | null;
    usuario_ldap: string;
    user_nombre: string | null;
    estado: string;
    fecha: string;
    fecha_error_procesamiento: string | null;
    error_procesamiento: string | null;
    error_origen: string | null;
    reintentos_procesamiento: number;
    tiene_payload: boolean;
    jobs_error: number;
    archivos_error: number;
};

export type SesionFallidaDetalle = {
    sesion: SesionFallida & {
        inicio: string | null;
        fin: string | null;
        duracion_real: number | null;
        fecha_ultimo_procesamiento: string | null;
    };
    payload_procesamiento: Record<string, unknown> | null;
    jobs: Array<{
        id: number;
        tipo: string;
        estado: string;
        archivo: string;
        error: string | null;
        fecha_creacion: string;
        fecha_actualizacion: string;
    }>;
    archivos: Array<{
        id: number;
        tipo_archivo: string;
        estado: string;
        mensaje: string | null;
        ruta_convertida: string | null;
        conversion_completa: boolean;
        fecha_finalizacion: string | null;
    }>;
};

export async function fetchSesionesFallidas(params: {
    page: number;
    per_page: number;
}) {
    const { data } = await api.get("/dashboard/sesiones-fallidas", { params });
    return data;
}

export async function fetchSesionFallidaDetalle(sesionId: number) {
    const { data } = await api.get<SesionFallidaDetalle>(
        `/dashboard/sesiones-fallidas/${sesionId}`
    );
    return data;
}

export async function reprocesarSesionFallida(sesionId: number) {
    const { data } = await api.post(`/dashboard/sesiones-fallidas/${sesionId}/reprocesar`);
    return data;
}
