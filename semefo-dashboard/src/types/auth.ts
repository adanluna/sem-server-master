export interface LoginResponse {
    access_token: string;
    refresh_token: string;
    token_type: "bearer";
}

export interface DashboardUser {
    username: string;
    roles: string[];
}