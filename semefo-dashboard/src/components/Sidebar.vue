<template>
    <aside class="sidebar">
        <div class="brand">
            <span class="logo">MENU</span>
        </div>

        <nav class="menu">
            <router-link to="/dashboard" class="item" active-class="active" exact>
                Dashboard
            </router-link>

            <router-link to="/planchas" class="item" active-class="active">
                Planchas
            </router-link>

            <router-link to="/sesiones" class="item" active-class="active">
                Sesiones
            </router-link>


            <router-link to="/jobs/pendiente" class="item" active-class="active">
                Jobs pendientes
            </router-link>

            <router-link to="/infraestructura" class="item" active-class="active">
                Infraestructura
            </router-link>
        </nav>
    </aside>
</template>
<style scoped>
/* Branding */
.brand {
    padding-left: 10px;
    padding-bottom: 12px;
    border-bottom: 1px solid #383C42;
}

.logo {
    font-weight: 700;
    font-size: 16px;
    letter-spacing: 0.5px;
}

.subtitle {
    display: block;
    font-size: 12px;
    color: #94a3b8;
    margin-top: 4px;
}

/* Menú */
.menu {
    padding: 12px 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.item {
    padding: 10px 14px;
    border-radius: 6px;
    color: #cbd5f5;
    text-decoration: none;
    font-size: 14px;
    transition: background 0.2s ease, color 0.2s ease;
}

.item:hover {
    background: #1e293b;
    color: #ffffff;
}

/* Activo */
.active {
    background: #1d4ed8;
    color: #ffffff;
    font-weight: 600;
}
</style>
