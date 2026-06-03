import api from "./api";

export type AppSessionRow = {
    id: number;
    usuario_ldap: string;
    tablet_id: string;
    estado: string;
    sesion_id: number | null;
    numero_expediente: string | null;
    nombre_sesion: string | null;
    last_heartbeat_at: string;
    logged_in_at: string;
    is_stale: boolean;
    can_admin_revoke: boolean;
};

export async function listAppSessions(): Promise<AppSessionRow[]> {
    const { data } = await api.get<AppSessionRow[]>("/dashboard/app-sessions");
    return data;
}

export async function revokeAppSession(sessionId: number): Promise<void> {
    await api.post(`/dashboard/app-sessions/${sessionId}/revoke`);
}
