export const PERMISSION_KEYS = [
    "dashboard",
    "sesiones",
    "sesiones_fallidas",
    "jobs",
    "planchas",
    "tokens",
    "infraestructura",
    "usuarios",
] as const;

export type PermissionKey = (typeof PERMISSION_KEYS)[number];

export type DashboardPermissions = Record<PermissionKey, boolean>;

export const PERMISSION_LABELS: Record<PermissionKey, string> = {
    dashboard: "Dashboard",
    sesiones: "Sesiones",
    sesiones_fallidas: "Sesiones fallidas",
    jobs: "Jobs",
    planchas: "Planchas",
    tokens: "Tokens (API)",
    infraestructura: "Infraestructura",
    usuarios: "Usuarios del panel",
};

export function emptyPermissions(): DashboardPermissions {
    return {
        dashboard: false,
        sesiones: false,
        sesiones_fallidas: false,
        jobs: false,
        planchas: false,
        tokens: false,
        infraestructura: false,
        usuarios: false,
    };
}

export function fullPermissions(): DashboardPermissions {
    const p = emptyPermissions();
    for (const k of PERMISSION_KEYS) {
        p[k] = true;
    }
    return p;
}
