<template>
    <section class="container-fluid">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h2 class="mb-0">Sesiones app (tablets)</h2>
            <button class="btn btn-outline-secondary btn-sm" :disabled="loading" @click="load">
                Actualizar
            </button>
        </div>

        <p class="text-muted small">
            Operadores LDAP con sesión activa en la app. No se puede cerrar remotamente mientras
            <strong>estado = recording</strong>.
        </p>

        <div class="card">
            <div class="table-responsive">
                <table class="table table-hover table-sm mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Usuario</th>
                            <th>Tablet</th>
                            <th>Estado app</th>
                            <th>Expediente / sesión</th>
                            <th>Último heartbeat</th>
                            <th>Inicio sesión</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="s in rows" :key="s.id">
                            <td class="fw-semibold">{{ s.usuario_ldap }}</td>
                            <td>{{ s.tablet_id }}</td>
                            <td>
                                <span class="badge" :class="estadoBadge(s)">
                                    {{ s.estado }}
                                </span>
                                <span v-if="s.is_stale" class="badge bg-warning text-dark ms-1">
                                    stale
                                </span>
                            </td>
                            <td>
                                <template v-if="s.sesion_id">
                                    {{ s.numero_expediente ?? "—" }}
                                    <span v-if="s.nombre_sesion" class="text-muted">
                                        / {{ s.nombre_sesion }}
                                    </span>
                                </template>
                                <span v-else class="text-muted">—</span>
                            </td>
                            <td>{{ formatFechaLocal(s.last_heartbeat_at) }}</td>
                            <td>{{ formatFechaLocal(s.logged_in_at) }}</td>
                            <td>
                                <button
                                    class="btn btn-sm btn-outline-danger"
                                    :disabled="!s.can_admin_revoke || revoking === s.id"
                                    :title="
                                        s.can_admin_revoke
                                            ? 'Cerrar sesión en la tablet'
                                            : 'No disponible mientras graba'
                                    "
                                    @click="confirmRevoke(s)"
                                >
                                    Cerrar
                                </button>
                            </td>
                        </tr>
                        <tr v-if="!loading && !rows.length">
                            <td colspan="7" class="text-center py-4 text-muted">
                                No hay sesiones app activas
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { listAppSessions, revokeAppSession, type AppSessionRow } from "../api/app_sessions";
import { formatFechaLocal } from "../utils/fechas";

const loading = ref(false);
const revoking = ref<number | null>(null);
const rows = ref<AppSessionRow[]>([]);

function estadoBadge(s: AppSessionRow): string {
    if (s.estado === "recording") return "bg-danger";
    return "bg-secondary";
}

async function load() {
    loading.value = true;
    try {
        rows.value = await listAppSessions();
    } catch (e: any) {
        const msg = e?.response?.data?.detail ?? "Error al cargar sesiones app";
        alert(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
        loading.value = false;
    }
}

async function confirmRevoke(s: AppSessionRow) {
    if (!s.can_admin_revoke) return;
    if (!confirm(`¿Cerrar sesión de ${s.usuario_ldap} en tablet ${s.tablet_id}?`)) return;

    revoking.value = s.id;
    try {
        await revokeAppSession(s.id);
        await load();
    } catch (e: any) {
        const detail = e?.response?.data?.detail;
        alert(typeof detail === "string" ? detail : "No se pudo cerrar la sesión");
    } finally {
        revoking.value = null;
    }
}

onMounted(load);
</script>
