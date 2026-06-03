<template>
    <section class="container-fluid">

        <!-- HEADER -->
        <div class="d-flex align-items-center justify-content-between mb-4">
            <h2 class="mb-0">
                <i class="bi bi-diagram-3 me-2"></i>
                Infraestructura
            </h2>

            <div class="d-flex align-items-center gap-2">
                <button class="btn btn-outline-secondary btn-sm" :disabled="loading" @click="loadInfra">
                    <i class="bi bi-arrow-clockwise me-1"></i>
                    Actualizar
                </button>
                <span class="badge fs-6" :class="infraBadge(estado.infra_status)">
                    <i class="me-1" :class="{
                        'bi bi-check-circle': estado.infra_status === 'ok',
                        'bi bi-exclamation-triangle': estado.infra_status === 'warning',
                        'bi bi-x-circle': estado.infra_status === 'error'
                    }"></i>
                    {{ estado.infra_status?.toUpperCase() }}
                </span>
            </div>
        </div>

        <!-- NODOS: MASTER | WHISPER | GRABADOR -->
        <div class="row g-3 mb-4">
            <div class="col-lg-4">
                <div class="card h-100 border-primary border-opacity-25">
                    <div class="card-header fw-semibold d-flex justify-content-between align-items-center">
                        <span><i class="bi bi-server me-1"></i> Master</span>
                        <span class="badge" :class="nodoBadge(masterOk)">{{ masterOk ? "OK" : "ERROR" }}</span>
                    </div>
                    <div class="card-body small">
                        <div class="d-flex justify-content-between">
                            <span>API</span>
                            <span :class="statusClass(estado.api)">{{ estado.api?.toUpperCase() }}</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Base de datos</span>
                            <span :class="statusClass(estado.db)">{{ estado.db?.toUpperCase() }}</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>RabbitMQ</span>
                            <span :class="statusClass(estado.rabbitmq)">{{ estado.rabbitmq?.toUpperCase() }}</span>
                        </div>
                        <div class="d-flex justify-content-between mt-1">
                            <span>Montaje WAVE</span>
                            <span :class="statusClass(estado.wave_master_status)">
                                {{ (estado.wave_master_status || "—").toUpperCase() }}
                            </span>
                        </div>
                        <div v-if="estado.wave_mount?.master?.message" class="text-muted mt-2">
                            {{ estado.wave_mount.master.message }}
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-4">
                <div class="card h-100 border-info border-opacity-25">
                    <div class="card-header fw-semibold d-flex justify-content-between align-items-center">
                        <span><i class="bi bi-mic me-1"></i> Whisper</span>
                        <span class="badge" :class="whisperBadge(estado.disco?.whisper?.status)">
                            {{ estado.disco?.whisper?.status || "sin_reporte" }}
                        </span>
                    </div>
                    <div class="card-body small">
                        <div class="d-flex justify-content-between">
                            <span>Montaje WAVE</span>
                            <span :class="statusClass(estado.wave_whisper_status)">
                                {{ (estado.wave_whisper_status || "—").toUpperCase() }}
                            </span>
                        </div>
                        <div v-if="estado.wave_mount?.whisper?.reported_at" class="text-muted mt-1">
                            Reporte montaje:
                            {{ formatDate(estado.wave_mount.whisper.reported_at) }}
                        </div>
                        <div v-if="estado.disco?.whisper?.fecha" class="text-muted mt-1">
                            Reporte disco:
                            {{ formatDate(estado.disco.whisper.fecha) }}
                        </div>
                        <div v-if="estado.wave_mount?.whisper?.message" class="text-muted mt-2">
                            {{ estado.wave_mount.whisper.message }}
                        </div>
                        <div v-else-if="!estado.disco?.whisper?.total_gb" class="text-muted mt-2">
                            Sin reporte reciente desde el servidor Whisper.
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-4">
                <div class="card h-100 border-warning border-opacity-50">
                    <div class="card-header fw-semibold d-flex justify-content-between align-items-center">
                        <span><i class="bi bi-hdd-rack me-1"></i> Grabador Hanwha</span>
                        <span class="badge" :class="nodoBadge(grabadorOk)">{{ grabadorOk ? "OK" : "ERROR" }}</span>
                    </div>
                    <div class="card-body small">
                        <div><strong>IP:</strong> {{ grabador.ip }}</div>
                        <div class="d-flex justify-content-between mt-1">
                            <span>Ping</span>
                            <span :class="grabador.online ? 'text-success' : 'text-danger'">
                                {{ grabador.online ? "OK" : "Fallo" }}
                            </span>
                        </div>
                        <div v-if="grabador.smb_port_open != null" class="d-flex justify-content-between">
                            <span>SMB (445)</span>
                            <span :class="grabador.smb_port_open ? 'text-success' : 'text-danger'">
                                {{ grabador.smb_port_open ? "OK" : "Cerrado" }}
                            </span>
                        </div>
                        <div v-if="grabador.metodo" class="text-muted mt-1">
                            Método ping: {{ grabador.metodo }}
                        </div>
                        <div class="text-muted mt-2">{{ grabador.message }}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- SERVICIOS (resumen rápido) -->
        <div class="row g-3 mb-4">
            <div class="col-md-4 col-lg-3" v-for="s in servicios" :key="s.label">
                <div class="card text-center h-100">
                    <div class="card-body">
                        <h6 class="text-muted mb-2">
                            <i :class="s.icon" class="me-1"></i>
                            {{ s.label }}
                        </h6>

                        <span class="badge fs-6" :class="{
                            'bg-success': s.status === 'ok',
                            'bg-danger': s.status === 'error'
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
            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-header fw-semibold">
                        <i class="bi bi-hdd-fill me-1"></i>
                        Disco MASTER
                    </div>

                    <div class="card-body" v-if="estado.disco?.master">
                        <DiskBar :disk="estado.disco.master" />
                    </div>

                    <div class="card-body text-muted" v-else>
                        <i class="bi bi-question-circle me-1"></i>
                        Sin información
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-header fw-semibold d-flex justify-content-between align-items-center">
                        <div>
                            <i class="bi bi-hdd-network me-1"></i>
                            Disco WHISPER
                        </div>

                        <span class="badge" :class="whisperBadge(estado.disco?.whisper?.status)">
                            <i class="me-1" :class="{
                                'bi bi-check-circle': estado.disco?.whisper?.status === 'ok',
                                'bi bi-exclamation-triangle': estado.disco?.whisper?.status === 'stale',
                                'bi bi-dash-circle': estado.disco?.whisper?.status === 'sin_reporte'
                            }"></i>
                            {{ estado.disco?.whisper?.status }}
                        </span>
                    </div>

                    <div class="card-body" v-if="estado.disco?.whisper?.total_gb">
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

const loading = ref(false);

const estado = ref<any>({
    infra_status: "ok",
    api: "ok",
    db: "error",
    rabbitmq: "error",
    workers: {},
    disco: { whisper: { status: "sin_reporte" } },
    grabador: null,
    grabador_status: "error",
    wave_mount: null,
});

const grabador = computed(() => {
    const g = estado.value.grabador;
    if (g && typeof g === "object") return g;
    return {
        ip: "—",
        online: false,
        smb_port_open: null,
        message: "Sin datos del grabador (actualice o revise el API en master)",
        ok: false,
    };
});

const grabadorOk = computed(() => estado.value.grabador_status === "ok");

const masterOk = computed(() =>
    estado.value.api === "ok" &&
    estado.value.db === "ok" &&
    estado.value.rabbitmq === "ok" &&
    estado.value.wave_master_status === "ok"
);

const servicios = computed(() => [
    { label: "API", status: estado.value.api || "error", icon: "bi bi-server" },
    { label: "Base de datos", status: estado.value.db || "error", icon: "bi bi-database" },
    { label: "RabbitMQ", status: estado.value.rabbitmq || "error", icon: "bi bi-inbox" },
    {
        label: `Grabador (${grabador.value.ip})`,
        status: grabadorOk.value ? "ok" : "error",
        icon: "bi bi-hdd-rack",
    },
    {
        label: "Montaje WAVE (master)",
        status: estado.value.wave_master_status === "ok" ? "ok" : "error",
        icon: "bi bi-folder-symlink",
    },
    {
        label: "Montaje WAVE (whisper)",
        status: estado.value.wave_whisper_status === "ok" ? "ok" : "error",
        icon: "bi bi-folder2-open",
    },
]);

async function loadInfra() {
    loading.value = true;
    try {
        const { data } = await api.get("/dashboard/infraestructura");
        estado.value = { ...estado.value, ...data };
    } finally {
        loading.value = false;
    }
}

function infraBadge(s: string) {
    return s === "ok"
        ? "bg-success"
        : s === "warning"
            ? "bg-warning text-dark"
            : "bg-danger";
}

function nodoBadge(ok: boolean) {
    return ok ? "bg-success" : "bg-danger";
}

function statusClass(status: string | undefined) {
    return status === "ok" ? "text-success fw-semibold" : "text-danger fw-semibold";
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
    if (!d) return "—";
    return new Date(d).toLocaleString();
}

onMounted(loadInfra);
</script>
