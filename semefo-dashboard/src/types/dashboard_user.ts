import type { DashboardPermissions } from "./permissions";

export interface DashboardUser {
    id: number;
    username: string;
    activo: boolean;
    permissions: DashboardPermissions;
    is_protected: boolean;
    last_login_at?: string | null;
    created_at: string;
}

export interface DashboardUserCreate {
    username: string;
    password: string;
    activo: boolean;
    permissions: DashboardPermissions;
}

export interface DashboardUserUpdate {
    password?: string;
    activo?: boolean;
    permissions?: DashboardPermissions;
}
