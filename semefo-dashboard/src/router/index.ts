import { createRouter, createWebHistory } from "vue-router";
import { hasPermission, firstAllowedRoute } from "../utils/permissions";
import type { PermissionKey } from "../types/permissions";

const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: "/", redirect: "/login" },

        {
            path: "/login",
            name: "login",
            component: () => import("../views/LoginView.vue"),
            meta: { title: "Login | SEMEFO" }
        },

        // =========================
        // DASHBOARD (PROTEGIDO)
        // =========================
        {
            path: "/",
            component: () => import("../views/DashboardLayout.vue"),
            meta: { requiresAuth: true },
            children: [
                {
                    path: "dashboard",
                    name: "dashboard",
                    component: () => import("../views/DashboardHomeView.vue"),
                    meta: { title: "Dashboard | SEMEFO", permission: "dashboard" as PermissionKey }
                },
                {
                    path: "planchas",
                    name: "planchas",
                    component: () => import("../views/PlanchasView.vue"),
                    meta: { title: "Planchas | SEMEFO", permission: "planchas" as PermissionKey }
                },
                {
                    path: "planchas/nueva",
                    name: "plancha-nueva",
                    component: () => import("../views/PlanchaCreateView.vue"),
                    meta: { title: "Nueva Plancha | SEMEFO", permission: "planchas" as PermissionKey }
                },
                {
                    path: "planchas/:id",
                    name: "plancha-editar",
                    component: () => import("../views/PlanchaEditView.vue"),
                    meta: { title: "Editar Plancha | SEMEFO", permission: "planchas" as PermissionKey }
                },
                {
                    path: "sesiones",
                    name: "sesiones",
                    component: () => import("../views/SesionesView.vue"),
                    meta: { title: "Sesiones | SEMEFO", permission: "sesiones" as PermissionKey }
                },
                {
                    path: "sesiones-app",
                    name: "sesiones-app",
                    component: () => import("../views/SesionesAppView.vue"),
                    meta: { title: "Sesiones app | SEMEFO", permission: "sesiones" as PermissionKey }
                },
                {
                    path: "sesiones-fallidas",
                    name: "sesiones-fallidas",
                    component: () => import("../views/SesionesFallidasView.vue"),
                    meta: { title: "Sesiones Fallidas | SEMEFO", permission: "sesiones_fallidas" as PermissionKey }
                },
                {
                    path: "jobs/:estado",
                    name: "jobs",
                    component: () => import("../views/JobsView.vue"),
                    meta: { title: "Jobs | SEMEFO", permission: "jobs" as PermissionKey }
                },
                {
                    path: "infraestructura",
                    name: "infraestructura",
                    component: () => import("../views/InfraestructuraView.vue"),
                    meta: { title: "Infraestructura | SEMEFO", permission: "infraestructura" as PermissionKey }
                },

                // =========================
                // SERVICE CLIENTS (API KEYS)
                // =========================
                {
                    path: "service-clients",
                    name: "service-clients",
                    component: () => import("../views/ServiceClientsView.vue"),
                    meta: { title: "Service Clients | SEMEFO", permission: "tokens" as PermissionKey }
                },
                {
                    path: "usuarios",
                    name: "usuarios",
                    component: () => import("../views/UsuariosView.vue"),
                    meta: { title: "Usuarios | SEMEFO", permission: "usuarios" as PermissionKey }
                },
            ]
        },

        { path: "/:pathMatch(.*)*", redirect: "/dashboard" }
    ]
});

// =======================================================
// 🔒 GUARD GLOBAL DE AUTENTICACIÓN
// =======================================================
router.beforeEach((to, _from, next) => {
    const requiresAuth = to.matched.some((r) => r.meta.requiresAuth);
    const token = localStorage.getItem("token");

    if (requiresAuth && !token) {
        next("/login");
        return;
    }

    const perm = to.meta.permission as PermissionKey | undefined;
    if (requiresAuth && perm && !hasPermission(perm)) {
        const fallback = firstAllowedRoute();
        if (fallback && fallback !== to.path) {
            next(fallback);
            return;
        }
        next("/login");
        return;
    }

    next();
});

export default router;
