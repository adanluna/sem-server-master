import type { DashboardPermissions } from "./permissions";

export interface LoginResponse {
    access_token: string;
    refresh_token: string;
    token_type: "bearer";
}

export interface JwtDashboardPayload {
    sub?: string;
    roles?: string[];
    permissions?: DashboardPermissions;
    type?: string;
}