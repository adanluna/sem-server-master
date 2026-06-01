import api from "./api";
import type {
    DashboardUser,
    DashboardUserCreate,
    DashboardUserUpdate,
} from "../types/dashboard_user";
import type { DashboardPermissions } from "../types/permissions";

export interface DashboardMe {
    username: string;
    permissions: DashboardPermissions;
    is_protected: boolean;
}

export async function fetchDashboardMe(): Promise<DashboardMe> {
    const { data } = await api.get<DashboardMe>("/dashboard/me");
    return data;
}

export async function listDashboardUsers(): Promise<DashboardUser[]> {
    const { data } = await api.get<DashboardUser[]>("/dashboard/usuarios");
    return data;
}

export async function getDashboardUser(id: number): Promise<DashboardUser> {
    const { data } = await api.get<DashboardUser>(`/dashboard/usuarios/${id}`);
    return data;
}

export async function createDashboardUser(
    payload: DashboardUserCreate
): Promise<DashboardUser> {
    const { data } = await api.post<DashboardUser>("/dashboard/usuarios", payload);
    return data;
}

export async function updateDashboardUser(
    id: number,
    payload: DashboardUserUpdate
): Promise<DashboardUser> {
    const { data } = await api.put<DashboardUser>(`/dashboard/usuarios/${id}`, payload);
    return data;
}

export async function deleteDashboardUser(id: number): Promise<void> {
    await api.delete(`/dashboard/usuarios/${id}`);
}
