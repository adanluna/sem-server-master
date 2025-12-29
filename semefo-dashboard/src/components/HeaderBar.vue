<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

// Puedes luego sacar esto del token JWT
const username = computed(() => {
    const raw = localStorage.getItem("user_nombre");

    if (!raw) return "Usuario";

    // Capitaliza primera letra
    return raw.charAt(0).toUpperCase() + raw.slice(1);
});

function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user_nombre");
    router.push("/");
}
</script>

<template>
    <header class="header">
        <!-- Izquierda -->
        <div class="left">
            <span class="logo">SEMEFO</span>
            <span class="divider">|</span>
            <span class="title">Dashboard</span>
        </div>

        <!-- Derecha -->
        <div class="right">
            <span class="user">{{ username }}</span>
            <button class="logout" @click="logout">
                Cerrar sesión
            </button>
        </div>
    </header>
</template>
<style scoped>
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 56px;
    padding: 0 20px;
    background: #0f172a;
    /* azul institucional oscuro */
    color: #f8fafc;
    border-bottom: 1px solid #1e293b;
}

/* Lado izquierdo */
.left {
    display: flex;
    align-items: center;
    gap: 8px;
}

.logo {
    font-weight: 700;
    letter-spacing: 0.5px;
    font-size: 15px;
}

.divider {
    opacity: 0.5;
}

.title {
    font-size: 14px;
    color: #cbd5f5;
}

/* Lado derecho */
.right {
    display: flex;
    align-items: center;
    gap: 16px;
}

.user {
    font-size: 13px;
    opacity: 0.9;
}

/* Botón logout */
.logout {
    background: transparent;
    border: 1px solid #475569;
    color: #f8fafc;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.logout:hover {
    background: #dc2626;
    border-color: #dc2626;
}
</style>
