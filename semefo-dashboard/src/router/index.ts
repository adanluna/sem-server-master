import { createRouter, createWebHistory } from "vue-router";

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
                    meta: { title: "Dashboard | SEMEFO" }
                },
                {
                    path: "planchas",
                    name: "planchas",
                    component: () => import("../views/PlanchasView.vue"),
                    meta: { title: "Planchas | SEMEFO" }
                },
                {
                    path: "planchas/nueva",
                    name: "plancha-nueva",
                    component: () => import("../views/PlanchaCreateView.vue"),
                    meta: { title: "Nueva Plancha | SEMEFO" }
                },
                {
                    path: "planchas/:id",
                    name: "plancha-editar",
                    component: () => import("../views/PlanchaEditView.vue"),
                    meta: { title: "Editar Plancha | SEMEFO" }
                },
                {
                    path: "sesiones",
                    name: "sesiones",
                    component: () => import("../views/SesionesView.vue"),
                    meta: { title: "Sesiones | SEMEFO" }
                },
                {
                    path: "jobs/:estado",
                    name: "jobs",
                    component: () => import("../views/JobsView.vue"),
                    meta: { title: "Jobs | SEMEFO" }
                },
                {
                    path: "infraestructura",
                    name: "infraestructura",
                    component: () => import("../views/InfraestructuraView.vue"),
                    meta: { title: "Infraestructura | SEMEFO" }
                },

                // =========================
                // SERVICE CLIENTS (API KEYS)
                // =========================
                {
                    path: "service-clients",
                    name: "service-clients",
                    component: () => import("../views/ServiceClientsView.vue"),
                    meta: { title: "Service Clients | SEMEFO" }
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

    next();
});

export default router;
