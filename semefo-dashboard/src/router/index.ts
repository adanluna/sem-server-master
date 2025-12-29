import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
    history: createWebHistory(),
    routes: [
        // -------------------------
        // Redirect inicial
        // -------------------------
        { path: "/", redirect: "/login" },

        // -------------------------
        // Login
        // -------------------------
        {
            path: "/login",
            name: "login",
            component: () => import("../views/LoginView.vue"),
            meta: { title: "Login | SEMEFO" }
        },

        // =================================================
        // LAYOUT DASHBOARD (sin prefijo en URL)
        // =================================================
        {
            path: "/",
            component: () => import("../views/DashboardLayout.vue"),
            meta: { requiresAuth: true },
            children: [
                // -------- Dashboard home --------
                {
                    path: "dashboard",
                    name: "dashboard",
                    component: () => import("../views/DashboardHomeView.vue"),
                    meta: { title: "Dashboard | SEMEFO" }
                },

                // -------- Planchas --------
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

                // -------- Sesiones --------
                {
                    path: "sesiones",
                    name: "sesiones",
                    component: () => import("../views/SesionesView.vue"),
                    meta: { title: "Sesiones | SEMEFO" }
                },

                // -------- Jobs --------
                {
                    path: "jobs/:estado",
                    name: "jobs",
                    component: () => import("../views/JobsView.vue"),
                    meta: { title: "Jobs | SEMEFO" }
                },

                // -------- Infraestructura --------
                {
                    path: "infraestructura",
                    name: "infraestructura",
                    component: () => import("../views/InfraestructuraView.vue"),
                    meta: { title: "Infraestructura | SEMEFO" }
                },
            ]
        },

        // -------------------------
        // Fallback (404)
        // -------------------------
        {
            path: "/:pathMatch(.*)*",
            redirect: "/dashboard"
        }
    ]
});

export default router;
