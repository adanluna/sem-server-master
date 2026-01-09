<template>
    <section class="container-fluid">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h2 class="mb-0">
                Jobs
                <span class="badge ms-2" :class="estadoBadge(estado)">
                    {{ estado }}
                </span>
            </h2>
        </div>

        <!-- Tabla -->
        <div class="card">
            <div class="table-responsive">
                <table class="table table-hover table-sm mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>ID</th>
                            <th>Sesión</th>
                            <th>Nombre sesión</th>
                            <th>Expediente</th>
                            <th>Tipo</th>
                            <th>Archivo</th>
                            <th>Fecha</th>
                            <th>Error</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="j in jobs" :key="j.job_id">
                            <td class="fw-semibold">{{ j.job_id }}</td>

                            <td>
                                <span class="badge bg-dark">
                                    {{ j.sesion_id }}
                                </span>
                            </td>

                            <td class="fw-semibold">
                                {{ j.nombre_sesion }}
                            </td>

                            <td>{{ j.numero_expediente }}</td>

                            <td>
                                <span class="badge bg-secondary">
                                    {{ j.tipo }}
                                </span>
                            </td>

                            <td class="text-truncate" style="max-width: 240px;">
                                {{ j.archivo }}
                            </td>

                            <td>{{ formatDate(j.fecha) }}</td>

                            <td style="max-width: 300px;">
                                <div v-if="j.error" class="text-danger small">
                                    {{ j.error }}
                                </div>
                                <span v-else class="text-muted">—</span>
                            </td>
                            <td>
                                <button class="btn btn-outline-primary btn-sm" @click="verProcesos(j.sesion_id)">
                                    Ver procesos
                                </button>
                            </td>
                        </tr>
                    </tbody>

                    <!-- ✅ Empty state -->
                    <tr v-if="!jobs.length">
                        <td colspan="8" class="text-center py-4 text-muted">
                            No hay jobs con estado "{{ estado }}"
                        </td>
                    </tr>
                </table>
            </div>

            <div class="card-footer">
                <Pagination :page="page" :total-pages="totalPages" @change="changePage" />
            </div>
        </div>
    </section>

    <!-- MODAL PROCESOS -->
    <div class="modal fade show" tabindex="-1" style="display: block;" v-if="showModal">
        <div class="modal-dialog modal-xl modal-dialog-scrollable">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Procesos de la sesión</h5>
                    <button type="button" class="btn-close" @click="showModal = false"></button>
                </div>

                <div class="modal-body">
                    <div v-if="loadingProcesos" class="text-center text-muted">
                        Cargando procesos…
                    </div>

                    <pre v-else class="bg-dark text-light p-3 rounded small">
                        {{ JSON.stringify(procesos, null, 2) }}
                    </pre>
                </div>

                <div class="modal-footer">
                    <button class="btn btn-secondary" @click="showModal = false">
                        Cerrar
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- backdrop -->
    <div class="modal-backdrop fade show" v-if="showModal"></div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { fetchJobs, fetchSesionProcesos } from "../api/dashboard";
import Pagination from "../components/Pagination.vue";
import { useRoute } from "vue-router";

const route = useRoute();
const estado = route.params.estado as string;

const jobs = ref<any[]>([]);
const page = ref(1);
const perPage = 50;
const totalPages = ref(1);

// Modal
const showModal = ref(false);
const procesos = ref<any | null>(null);
const loadingProcesos = ref(false);

async function loadJobs() {
    const res = await fetchJobs({
        estado,
        page: page.value,
        per_page: perPage
    });

    jobs.value = res.data;
    totalPages.value = res.meta.total_pages;
}

function changePage(p: number) {
    page.value = p;
    loadJobs();
}

function formatDate(d: string) {
    return new Date(d).toLocaleString();
}

function estadoBadge(estado: string) {
    switch (estado) {
        case "pendiente":
            return "bg-secondary";
        case "en_progreso":
            return "bg-warning text-dark";
        case "completado":
            return "bg-success";
        case "error":
            return "bg-danger";
        default:
            return "bg-dark";
    }
}

async function verProcesos(sesionId: number) {
    loadingProcesos.value = true;
    showModal.value = true;

    try {
        procesos.value = await fetchSesionProcesos(sesionId);
    } catch (e) {
        procesos.value = { error: "Error al cargar procesos" };
    } finally {
        loadingProcesos.value = false;
    }
}

onMounted(loadJobs);
</script>
