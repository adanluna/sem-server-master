<script setup lang="ts">
import { onMounted, ref } from "vue";
import { fetchDashboardResumen } from "../api/dashboard";
import { formatFechaLocal } from "../utils/fechas";

const loading = ref(true);
const resumen = ref<any>(null);

function badgeClass(estado: string) {
  if (estado === "finalizada") return "bg-success";
  if (estado === "error") return "bg-danger";
  if (estado === "pausada") return "bg-warning text-dark";
  if (estado === "procesando") return "bg-info text-dark";
  return "bg-secondary";
}

onMounted(async () => {
  loading.value = true;
  try {
    resumen.value = await fetchDashboardResumen();
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h4 class="mb-0">Dashboard</h4>
      <small class="text-muted">Últimos 30 días</small>
    </div>

    <div v-if="loading" class="text-muted">Cargando...</div>

    <div v-else>
      <!-- KPIs -->
      <div class="row g-3 mb-4">
        <div class="col-md-3">
          <div class="card shadow-sm">
            <div class="card-body">
              <div class="text-muted">Sesiones (30 días)</div>
              <div class="fs-3 fw-bold">{{ resumen.kpis.total_30_dias }}</div>
            </div>
          </div>
        </div>

        <div class="col-md-3">
          <div class="card shadow-sm">
            <div class="card-body">
              <div class="text-muted">Finalizadas</div>
              <div class="fs-3 fw-bold">{{ resumen.kpis.finalizadas }}</div>
            </div>
          </div>
        </div>

        <div class="col-md-3">
          <div class="card shadow-sm">
            <div class="card-body">
              <div class="text-muted">Pendientes</div>
              <div class="fs-3 fw-bold">{{ resumen.kpis.pendientes }}</div>
            </div>
          </div>
        </div>

        <div class="col-md-3">
          <div class="card shadow-sm">
            <div class="card-body">
              <div class="text-muted">Con errores</div>
              <div class="fs-3 fw-bold">{{ resumen.kpis.errores }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3 columnas: pendientes / ultimas / errores -->
      <div class="row g-3">
        <!-- Pendientes -->
        <div class="col-lg-12">
          <div class="card shadow-sm">
            <div class="card-header fw-semibold">Top 10 pendientes</div>
            <div class="table-responsive">
              <table class="table table-sm table-hover mb-0">
                <thead>
                  <tr>
                    <th>Expediente</th>
                    <th>Plancha</th>
                    <th>Estado</th>
                    <th>Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in resumen.pendientes" :key="s.id">
                    <td class="text-truncate" style="max-width:140px">{{ s.numero_expediente }}</td>
                    <td class="text-truncate" style="max-width:120px">{{ s.plancha_nombre }}</td>
                    <td><span class="badge" :class="badgeClass(s.estado)">{{ s.estado }}</span></td>
                    <td class="text-nowrap small">{{ formatFechaLocal(s.fecha) }}</td>
                  </tr>
                  <tr v-if="!resumen.pendientes?.length">
                    <td colspan="4" class="text-muted p-3">Sin pendientes</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Últimas -->
        <div class="col-lg-12">
          <div class="card shadow-sm">
            <div class="card-header fw-semibold">Top 10 últimas creadas</div>
            <div class="table-responsive">
              <table class="table table-sm table-hover mb-0">
                <thead>
                  <tr>
                    <th>Expediente</th>
                    <th>Plancha</th>
                    <th>Estado</th>
                    <th>Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in resumen.ultimas" :key="s.id">
                    <td class="text-truncate" style="max-width:140px">{{ s.numero_expediente }}</td>
                    <td class="text-truncate" style="max-width:120px">{{ s.plancha_nombre }}</td>
                    <td><span class="badge" :class="badgeClass(s.estado)">{{ s.estado }}</span></td>
                    <td class="text-nowrap small">{{ formatFechaLocal(s.fecha) }}</td>
                  </tr>
                  <tr v-if="!resumen.ultimas?.length">
                    <td colspan="4" class="text-muted p-3">Sin datos</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Errores -->
        <div class="col-lg-12">
          <div class="card shadow-sm">
            <div class="card-header fw-semibold">Top 10 con error</div>
            <div class="table-responsive">
              <table class="table table-sm table-hover mb-0">
                <thead>
                  <tr>
                    <th>Expediente</th>
                    <th>Origen</th>
                    <th>Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in resumen.errores" :key="s.id">
                    <td class="text-truncate" style="max-width:140px">{{ s.numero_expediente }}</td>
                    <td class="text-truncate" style="max-width:120px">{{ s.origen }}</td>
                    <td class="text-nowrap small">{{ formatFechaLocal(s.ultima_actualizacion) }}</td>
                  </tr>
                  <tr v-if="!resumen.errores?.length">
                    <td colspan="3" class="text-muted p-3">Sin errores</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>
