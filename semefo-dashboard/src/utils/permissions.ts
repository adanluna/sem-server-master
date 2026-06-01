import { parseJwt } from "./jwt";
import {
    PERMISSION_KEYS,
    type DashboardPermissions,
    type PermissionKey,
    emptyPermissions,
    fullPermissions,
} from "../types/permissions";

const STORAGE_KEY = "user_permissions";

function legacyFromRoles(roles: string[] | undefined): DashboardPermissions {
    const set = new Set((roles || []).map((r) => r.trim()));
    if (set.has("dashboard_admin")) {
        const p = fullPermissions();
        p.usuarios = false;
        return p;
    }
    if (set.has("dashboard_read")) {
        const p = emptyPermissions();
        p.dashboard = true;
        p.sesiones = true;
        p.jobs = true;
        p.planchas = true;
        return p;
    }
    return emptyPermissions();
}

export function normalizePermissions(raw: unknown): DashboardPermissions {
    const base = emptyPermissions();
    if (!raw || typeof raw !== "object") {
        return base;
    }
    for (const key of PERMISSION_KEYS) {
        if (key in (raw as object)) {
            base[key] = Boolean((raw as Record<string, unknown>)[key]);
        }
    }
    return base;
}

export function getStoredUsername(): string | null {
    return localStorage.getItem("user_nombre");
}

export function isSuperAdmin(): boolean {
    return getStoredUsername() === "admin";
}

export function loadPermissions(): DashboardPermissions {
    if (isSuperAdmin()) {
        return fullPermissions();
    }

    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
        try {
            const parsed = normalizePermissions(JSON.parse(stored));
            if (PERMISSION_KEYS.some((k) => parsed[k])) {
                return parsed;
            }
        } catch {
            /* ignore */
        }
    }

    const token = localStorage.getItem("token");
    const payload = token ? parseJwt(token) : null;
    const fromToken = normalizePermissions(payload?.permissions);
    if (PERMISSION_KEYS.some((k) => fromToken[k])) {
        return fromToken;
    }
    return legacyFromRoles(payload?.roles);
}

export function savePermissionsFromToken(token: string): void {
    const payload = parseJwt(token);
    const perms = isSuperAdmin()
        ? fullPermissions()
        : normalizePermissions(payload?.permissions);
    const hasAny = PERMISSION_KEYS.some((k) => perms[k]);
    const effective = hasAny ? perms : legacyFromRoles(payload?.roles);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(effective));
}

export function clearPermissions(): void {
    localStorage.removeItem(STORAGE_KEY);
}

export function hasPermission(key: PermissionKey): boolean {
    if (isSuperAdmin()) {
        return true;
    }
    return !!loadPermissions()[key];
}

export function firstAllowedRoute(): string | null {
    const order: { path: string; key: PermissionKey }[] = [
        { path: "/dashboard", key: "dashboard" },
        { path: "/sesiones", key: "sesiones" },
        { path: "/sesiones-fallidas", key: "sesiones_fallidas" },
        { path: "/jobs/pendiente", key: "jobs" },
        { path: "/planchas", key: "planchas" },
        { path: "/service-clients", key: "tokens" },
        { path: "/infraestructura", key: "infraestructura" },
        { path: "/usuarios", key: "usuarios" },
    ];
    for (const item of order) {
        if (hasPermission(item.key)) {
            return item.path;
        }
    }
    return null;
}
