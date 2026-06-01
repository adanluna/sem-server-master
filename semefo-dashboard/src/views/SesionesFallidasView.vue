<template>
    <section class="container-fluid">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h2 class="mb-0">Sesiones Fallidas</h2>
            <router-link to="/dashboard" class="btn btn-outline-secondary btn-sm">
                Volver al dashboard
            </router-link>
        </div>

        <div v-if="mensaje" class="alert" :class="mensajeOk ? 'alert-success' : 'alert-danger'">
            {{ mensaje }}
        </div>

        <div class="card">
            <div class="table-responsive">
                <table class="table table-hover table-sm mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>ID</th>
                            <th>Expediente</th>
                            <th>Sesión</th>
                            <th>Plancha</th>
                            <th>Usuario</th>
                            <th>Estado</th>
                            <th>Error</th>
                            <th>Origen</th>
                            <th>Fecha error</th>
                            <th>Reintentos</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="s in sesiones" :key="s.id">
                            <td>{{ s.id }}</td>
                            <td class="text-truncate" style="max-width: 120px">
                                {{ s.numero_expediente || "—" }}
                            </td>
                            <td class="text-truncate" style="max-width: 140px">
                                {{ s.nombre_sesion }}
                            </td>
                            <td>{{ s.plancha_nombre || "—" }}</td>
                            <td>{{ s.usuario_ldap }}</td>
                            <td>
                                <span class="badge bg-danger">{{ s.estado }}</span>
                            </td>
                            <td style="max-width: 220px">
                                <div class="small text-danger text-truncate" :title="s.error_procesamiento || ''">
                                    {{ s.error_procesamiento || "—" }}
                                </div>
                                <div v-if="s.jobs_error || s.archivos_error" class="text-muted small">
                                    Jobs ✖ {{ s.jobs_error }} · Archivos ✖ {{ s.archivos_error }}
                                </div>
                            </td>
                            <td class="small">{{ s.error_origen || "—" }}</td>
                            <td class="text-nowrap small">
                                {{ s.fecha_error_procesamiento ? formatFechaLocal(s.fecha_error_procesamiento) : "—" }}
                            </td>
                            <td>{{ s.reintentos_procesamiento }}</td>
                            <td class="text-nowrap">
                                <button
                                    class="btn btn-outline-secondary btn-sm me-1"
                                    @click="abrirDetalle(s.id)"
                                >
                                    Detalle
                                </button>
                                <button
                                    class="btn btn-primary btn-sm"
                                    :disabled="!s.tiene_payload || reprocesandoId === s.id"
                                    @click="confirmarReprocesar(s)"
                                >
                                    {{ reprocesandoId === s.id ? "Enviando..." : "Volver a procesar" }}
                                </button>
                            </td>
                        </tr>
                        <tr v-if="!loading && !sesiones.length">
                            <td colspan="11" class="text-center py-4 text-muted">
                                No hay sesiones fallidas con JSON guardado
                            </td>
                        </tr>
                        <tr v-if="loading">
                            <td colspan="11" class="text-center py-4 text-muted">Cargando...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="card-footer">
                <Pagination :page="page" :total-pages="totalPages" @change="changePage" />
            </div>
        </div>

        <!-- Modal detalle -->
        <div v-if="detalle" class="modal fade show d-block" tabindex="-1" style="background: rgba(0,0,0,.45)">
            <div class="modal-dialog modal-xl modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            Sesión {{ detalle.sesion.id }} — {{ detalle.sesion.nombre_sesion }}
                        </h5>
                        <button type="button" class="btn-close" @click="cerrarDetalle" />
                    </div>
                    <div class="modal-body">
                        <div class="row g-3 mb-3">
                            <div class="col-md-4">
                                <div class="text-muted small">Expediente</div>
                                <div>{{ detalle.sesion.numero_expediente || "—" }}</div>
                            </div>
                            <div class="col-md-4">
                                <div class="text-muted small">Plancha</div>
                                <div>{{ detalle.sesion.plancha_nombre || "—" }}</div>
                            </div>
                            <div class="col-md-4">
                                <div class="text-muted small">Forense</div>
                                <div>{{ detalle.sesion.user_nombre || detalle.sesion.usuario_ldap }}</div>
                            </div>
                            <div class="col-12">
                                <div class="text-muted small">Error</div>
                                <div class="text-danger">{{ detalle.sesion.error_procesamiento || "—" }}</div>
                                <div v-if="detalle.sesion.error_origen" class="small text-muted">
                                    Origen: {{ detalle.sesion.error_origen }}
                                </div>
                            </div>
                        </div>

                        <h6 class="fw-semibold">Jobs</h6>
                        <div class="table-responsive mb-3">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Tipo</th>
                                        <th>Estado</th>
                                        <th>Error</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="j in detalle.jobs" :key="j.id">
                                        <td>{{ j.tipo }}</td>
                                        <td>{{ j.estado }}</td>
                                        <td class="text-danger small">{{ j.error || "—" }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <h6 class="fw-semibold">Archivos</h6>
                        <div class="table-responsive mb-3">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Tipo</th>
                                        <th>Estado</th>
                                        <th>Mensaje</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="a in detalle.archivos" :key="a.id">
                                        <td>{{ a.tipo_archivo }}</td>
                                        <td>{{ a.estado }}</td>
                                        <td class="text-danger small">{{ a.mensaje || "—" }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <h6 class="fw-semibold">JSON guardado (payload_procesamiento)</h6>
                        <pre class="bg-light border rounded p-3 small mb-0" style="max-height: 320px; overflow: auto;">{{ jsonFormateado }}</pre>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="cerrarDetalle">Cerrar</button>
                        <button
                            class="btn btn-primary"
                            :disabled="!detalle.sesion.tiene_payload || reprocesandoId === detalle.sesion.id"
                            @click="confirmarReprocesar(detalle.sesion)"
                        >
                            Volver a procesar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import Pagination from "../components/Pagination.vue";
import { formatFechaLocal } from "../utils/fechas";
import {
    fetchSesionesFallidas,
    fetchSesionFallidaDetalle,
    reprocesarSesionFallida,
    type SesionFallida,
    type SesionFallidaDetalle,
} from "../api/sesiones_fallidas";

const route = useRoute();

const sesiones = ref<SesionFallida[]>([]);
const detalle = ref<SesionFallidaDetalle | null>(null);
const loading = ref(true);
const page = ref(1);
const perPage = 25;
const totalPages = ref(1);
const reprocesandoId = ref<number | null>(null);
const mensaje = ref("");
const mensajeOk = ref(true);

const jsonFormateado = computed(() => {
    if (!detalle.value?.payload_procesamiento) return "—";
    return JSON.stringify(detalle.value.payload_procesamiento, null, 2);
});

async function loadSesiones() {
    loading.value = true;
    try {
        const res = await fetchSesionesFallidas({ page: page.value, per_page: perPage });
        sesiones.value = res.data;
        totalPages.value = res.meta.total_pages || 1;
    } finally {
        loading.value = false;
    }
}

function changePage(p: number) {
    page.value = p;
    loadSesiones();
}

async function abrirDetalle(sesionId: number) {
    detalle.value = await fetchSesionFallidaDetalle(sesionId);
}

function cerrarDetalle() {
    detalle.value = null;
}

async function confirmarReprocesar(s: SesionFallida) {
    const ok = window.confirm(
        `¿Volver a procesar la sesión ${s.id} (${s.nombre_sesion})?\n\n` +
            "Se usará el JSON guardado en la base de datos."
    );
    if (!ok) return;

    reprocesandoId.value = s.id;
    mensaje.value = "";
    try {
        const res = await reprocesarSesionFallida(s.id);
        mensajeOk.value = true;
        mensaje.value = res.message || `Sesión ${s.id} enviada a reprocesar.`;
        cerrarDetalle();
        await loadSesiones();
    } catch (e: any) {
        mensajeOk.value = false;
        mensaje.value =
            e?.response?.data?.detail ||
            e?.message ||
            "No se pudo reprocesar la sesión.";
    } finally {
        reprocesandoId.value = null;
    }
}

onMounted(async () => {
    await loadSesiones();
    const sesionParam = route.query.sesion;
    if (sesionParam) {
        const id = Number(sesionParam);
        if (!Number.isNaN(id)) {
            await abrirDetalle(id);
        }
    }
});
</script>
