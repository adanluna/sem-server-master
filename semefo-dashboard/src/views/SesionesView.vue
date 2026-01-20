<template>
    <section class="container-fluid">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h2 class="mb-0">Sesiones</h2>
        </div>

        <!-- Filtros -->
        <div class="card mb-3">
            <div class="card-body">
                <div class="row g-2 align-items-end">
                    <div class="col-auto">
                        <label class="form-label mb-0">Desde</label>
                        <input type="date" v-model="desde" class="form-control" />
                    </div>

                    <div class="col-auto">
                        <label class="form-label mb-0">Hasta</label>
                        <input type="date" v-model="hasta" class="form-control" />
                    </div>

                    <div class="col-auto">
                        <button class="btn btn-primary" @click="loadSesiones">
                            Buscar
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tabla -->
        <div class="card">
            <div class="table-responsive">
                <table class="table table-hover table-sm mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Expediente</th>
                            <th>Sesión</th>
                            <th>Usuario</th>
                            <th>Fecha</th>
                            <th>Estado</th>
                            <th>Jobs</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="s in sesiones" :key="s.sesion_id">
                            <td class="fw-semibold">
                                {{ s.numero_expediente }}
                            </td>
                            <td class="fw-semibold">
                                {{ s.nombre_sesion }}
                            </td>
                            <td>{{ s.usuario_ldap }}</td>
                            <td>{{ formatDate(s.fecha) }}</td>
                            <td>
                                <span class="badge" :class="estadoBadge(s.estado)">
                                    {{ s.estado }}
                                </span>
                            </td>
                            <td>
                                <span class="text-success me-2">
                                    ✔ {{ s.jobs.completado }}
                                </span>
                                <span class="text-warning me-2">
                                    ⏳ {{ s.jobs.procesando }}
                                </span>
                                <span class="text-danger">
                                    ✖ {{ s.jobs.error }}
                                </span>
                            </td>
                        </tr>

                        <tr v-if="!sesiones.length">
                            <td colspan="5" class="text-center py-4 text-muted">
                                No hay sesiones en el rango seleccionado
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="card-footer">
                <Pagination :page="page" :total-pages="totalPages" @change="changePage" />
            </div>
        </div>
    </section>
</template>


<script setup lang="ts">
import { ref, onMounted } from "vue";
import { fetchSesiones } from "../api/dashboard";
import Pagination from "../components/Pagination.vue";

const sesiones = ref<any[]>([]);
const page = ref(1);
const perPage = 25;
const totalPages = ref(1);

const desde = ref(new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10));
const hasta = ref(new Date().toISOString().slice(0, 10));

async function loadSesiones() {
    const res = await fetchSesiones({
        desde: `${desde.value}T00:00:00Z`,
        hasta: `${hasta.value}T23:59:59Z`,
        page: page.value,
        per_page: perPage
    });

    sesiones.value = res.data;
    totalPages.value = res.meta.total_pages;
}

function changePage(p: number) {
    page.value = p;
    loadSesiones();
}

function formatDate(d: string) {
    return new Date(d).toLocaleString();
}

function estadoBadge(estado: string) {
    switch (estado) {
        case "finalizada":
            return "bg-success";
        case "procesando":
            return "bg-primary";
        case "pausada":
            return "bg-warning text-dark";
        case "error":
            return "bg-danger";
        default:
            return "bg-secondary";
    }
}

onMounted(loadSesiones);
</script>