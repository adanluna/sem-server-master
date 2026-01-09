<template>
    <section class="container-fluid">

        <!-- HEADER -->
        <div class="d-flex align-items-center justify-content-between mb-4">
            <h2 class="mb-0">
                <i class="bi bi-diagram-3 me-2"></i>
                Infraestructura
            </h2>

            <span class="badge fs-6" :class="infraBadge(estado.infra_status)">
                <i class="me-1" :class="{
                    'bi bi-check-circle': estado.infra_status === 'ok',
                    'bi bi-exclamation-triangle': estado.infra_status === 'warning',
                    'bi bi-x-circle': estado.infra_status === 'error'
                }"></i>
                {{ estado.infra_status?.toUpperCase() }}
            </span>
        </div>

        <!-- SERVICIOS -->
        <div class="row g-3 mb-4">
            <div class="col-md-4" v-for="s in servicios" :key="s.label">
                <div class="card text-center h-100">
                    <div class="card-body">
                        <h6 class="text-muted mb-2">
                            <i :class="s.icon" class="me-1"></i>
                            {{ s.label }}
                        </h6>

                        <span class="badge fs-6" :class="{
                            'bg-success': s.status === 'ok',
                            'bg-warning text-dark': s.status === 'error'
                        }">
                            <i class="me-1" :class="{
                                'bi bi-check-circle': s.status === 'ok',
                                'bi bi-x-circle': s.status === 'error'
                            }"></i>
                            {{ s.status?.toUpperCase() }}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <!-- WORKERS -->
        <div class="card mb-4">
            <div class="card-header fw-semibold">
                <i class="bi bi-cpu me-1"></i>
                Workers
            </div>

            <div class="card-body">
                <div class="row g-2">
                    <div class="col-md-2 col-6" v-for="(v, k) in estado.workers" :key="k">
                        <div class="border rounded p-2 text-center h-100">
                            <div class="small text-muted text-uppercase mb-1">
                                {{ k }}
                            </div>

                            <span class="badge" :class="workerBadge(v)">
                                <i class="me-1" :class="v === 'activo'
                                    ? 'bi bi-play-circle'
                                    : 'bi bi-pause-circle'"></i>
                                {{ v === 'inactivo' ? 'sin actividad' : v }}
                            </span>
                        </div>
                    </div>
                </div>

                <div class="text-muted small mt-3">
                    <i class="bi bi-info-circle me-1"></i>
                    “Sin actividad” significa que el worker está disponible pero no ha procesado jobs recientemente.
                </div>
            </div>
        </div>

        <!-- DISCO -->
        <div class="row g-3 mb-4">

            <!-- MASTER -->
            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-header fw-semibold">
                        <i class="bi bi-hdd-fill me-1"></i>
                        Disco MASTER
                    </div>

                    <div class="card-body" v-if="estado.disco.master">
                        <DiskBar :disk="estado.disco.master" />
                    </div>

                    <div class="card-body text-muted" v-else>
                        <i class="bi bi-question-circle me-1"></i>
                        Sin información
                    </div>
                </div>
            </div>

            <!-- WHISPER -->
            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-header fw-semibold d-flex justify-content-between align-items-center">
                        <div>
                            <i class="bi bi-hdd-network me-1"></i>
                            Disco WHISPER
                        </div>

                        <span class="badge" :class="whisperBadge(estado.disco.whisper?.status)">
                            <i class="me-1" :class="{
                                'bi bi-check-circle': estado.disco.whisper?.status === 'ok',
                                'bi bi-exclamation-triangle': estado.disco.whisper?.status === 'stale',
                                'bi bi-dash-circle': estado.disco.whisper?.status === 'sin_reporte'
                            }"></i>
                            {{ estado.disco.whisper?.status }}
                        </span>
                    </div>

                    <div class="card-body" v-if="estado.disco.whisper?.total_gb">
                        <DiskBar :disk="estado.disco.whisper" />

                        <div class="text-muted small mt-2">
                            <i class="bi bi-clock me-1"></i>
                            Último reporte:
                            {{ formatDate(estado.disco.whisper.fecha) }}
                        </div>
                    </div>

                    <div class="card-body text-muted" v-else>
                        <i class="bi bi-question-circle me-1"></i>
                        Sin reporte de Whisper
                    </div>
                </div>
            </div>
        </div>

        <!-- PIPELINE BLOQUEADO -->
        <div class="alert alert-warning" v-if="estado.pipeline_bloqueado?.total > 0">
            <i class="bi bi-exclamation-triangle-fill me-1"></i>
            <strong>Pipeline bloqueado</strong><br />
            Sesiones afectadas:
            {{ estado.pipeline_bloqueado?.total }}
        </div>

    </section>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import api from "../api/api";
import DiskBar from "../components/DiskBar.vue";

const estado = ref<any>({
    infra_status: "ok",
    workers: {},
    disco: {}
});

const servicios = computed(() => [
    { label: "API", status: estado.value.api, icon: "bi bi-server" },
    { label: "Base de datos", status: estado.value.db, icon: "bi bi-database" },
    { label: "RabbitMQ", status: estado.value.rabbitmq, icon: "bi bi-inbox" }
]);

async function loadInfra() {
    const { data } = await api.get("/dashboard/infraestructura");
    estado.value = data;
}

function infraBadge(s: string) {
    return s === "ok"
        ? "bg-success"
        : s === "warning"
            ? "bg-warning text-dark"
            : "bg-danger";
}

function workerBadge(s: string) {
    if (s === "activo") return "bg-success";
    if (s === "inactivo") return "bg-secondary";
    return "bg-warning text-dark";
}

function whisperBadge(s: string) {
    if (s === "ok") return "bg-success";
    if (s === "stale") return "bg-warning text-dark";
    return "bg-secondary";
}

function formatDate(d: string) {
    return new Date(d).toLocaleString();
}



onMounted(loadInfra);
</script>
