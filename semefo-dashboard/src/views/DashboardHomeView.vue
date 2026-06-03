<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { fetchDashboardResumen } from "../api/dashboard";
import { formatFechaLocal } from "../utils/fechas";
import { etapaBadgeClass, etapaLabel, etapaKey } from "../utils/sesionEtapa";

const loading = ref(true);
const resumen = ref<any>(null);

const sesionesAbiertas = computed(
    () => resumen.value?.abiertas ?? resumen.value?.pendientes ?? []
);

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
      <p class="text-muted small mb-4">
        <strong>Etapa</strong> describe qué pasa con la sesión (creada, grabando, pipeline…).
        <strong>Estado BD</strong> es el valor técnico guardado en PostgreSQL.
        Las listas muestran como máximo 10 filas; use
        <router-link to="/sesiones">Sesiones</router-link> para ver todas.
      </p>

      <!-- KPIs -->
      <div class="row g-3 mb-4">
        <div class="col-md-3">
          <div class="card shadow-sm h-100">
            <div class="card-body">
              <div class="text-muted">Sesiones (30 días)</div>
              <div class="fs-3 fw-bold">{{ resumen.kpis.total_30_dias }}</div>
            </div>
          </div>
        </div>

        <div class="col-md-3">
          <div class="card shadow-sm h-100">
            <div class="card-body">
              <div class="text-muted">Finalizadas</div>
              <div class="fs-3 fw-bold">{{ resumen.kpis.finalizadas }}</div>
              <div class="small text-muted">Evidencia completa</div>
            </div>
          </div>
        </div>

        <div class="col-md-3">
          <div class="card shadow-sm h-100">
            <div class="card-body">
              <div class="text-muted">Abiertas</div>
              <div class="fs-3 fw-bold">{{ resumen.kpis.abiertas ?? resumen.kpis.pendientes }}</div>
              <div class="small text-muted">Sin finalizar (procesando / pausada)</div>
            </div>
          </div>
        </div>

        <div class="col-md-3">
          <div class="card shadow-sm h-100">
            <div class="card-body">
              <div class="text-muted">Con errores</div>
              <div class="fs-3 fw-bold">{{ resumen.kpis.errores }}</div>
              <div class="small text-muted">Job o archivo en error</div>
            </div>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <!-- Abiertas recientes -->
        <div class="col-lg-12">
          <div class="card shadow-sm">
            <div class="card-header fw-semibold">
              Sesiones abiertas recientes
              <span class="text-muted fw-normal small ms-1">(top 10 · más nuevas primero)</span>
            </div>
            <div class="table-responsive">
              <table class="table table-sm table-hover mb-0">
                <thead>
                  <tr>
                    <th>Expediente</th>
                    <th>Sesión</th>
                    <th>Plancha</th>
                    <th>Etapa</th>
                    <th>Estado BD</th>
                    <th>Creada</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in sesionesAbiertas" :key="'a-' + s.id">
                    <td class="text-truncate" style="max-width:140px">{{ s.numero_expediente }}</td>
                    <td class="text-truncate" style="max-width:120px">{{ s.nombre_sesion }}</td>
                    <td class="text-truncate" style="max-width:120px">{{ s.plancha_nombre }}</td>
                    <td>
                      <span class="badge" :class="etapaBadgeClass(etapaKey(s))">
                        {{ etapaLabel(s) }}
                      </span>
                    </td>
                    <td><span class="badge bg-light text-dark border">{{ s.estado }}</span></td>
                    <td class="text-nowrap small">{{ formatFechaLocal(s.fecha) }}</td>
                  </tr>
                  <tr v-if="!sesionesAbiertas.length">
                    <td colspan="6" class="text-muted p-3">No hay sesiones abiertas</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Últimas creadas -->
        <div class="col-lg-12">
          <div class="card shadow-sm">
            <div class="card-header fw-semibold">
              Últimas sesiones creadas
              <span class="text-muted fw-normal small ms-1">(top 10 · incluye finalizadas)</span>
            </div>
            <div class="table-responsive">
              <table class="table table-sm table-hover mb-0">
                <thead>
                  <tr>
                    <th>Expediente</th>
                    <th>Sesión</th>
                    <th>Plancha</th>
                    <th>Etapa</th>
                    <th>Estado BD</th>
                    <th>Creada</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in resumen.ultimas" :key="'u-' + s.id">
                    <td class="text-truncate" style="max-width:140px">{{ s.numero_expediente }}</td>
                    <td class="text-truncate" style="max-width:120px">{{ s.nombre_sesion }}</td>
                    <td class="text-truncate" style="max-width:120px">{{ s.plancha_nombre }}</td>
                    <td>
                      <span class="badge" :class="etapaBadgeClass(etapaKey(s))">
                        {{ etapaLabel(s) }}
                      </span>
                    </td>
                    <td><span class="badge bg-light text-dark border">{{ s.estado }}</span></td>
                    <td class="text-nowrap small">{{ formatFechaLocal(s.fecha) }}</td>
                  </tr>
                  <tr v-if="!resumen.ultimas?.length">
                    <td colspan="6" class="text-muted p-3">Sin datos</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Errores -->
        <div class="col-lg-12">
          <div class="card shadow-sm">
            <div class="card-header fw-semibold d-flex justify-content-between align-items-center">
              <span>Con error en pipeline</span>
              <router-link to="/sesiones-fallidas" class="small">Ver todas →</router-link>
            </div>
            <div class="table-responsive">
              <table class="table table-sm table-hover mb-0">
                <thead>
                  <tr>
                    <th>Expediente</th>
                    <th>Sesión</th>
                    <th>Origen</th>
                    <th>Error</th>
                    <th>Fecha</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in resumen.errores" :key="s.id">
                    <td class="text-truncate" style="max-width:140px">{{ s.numero_expediente }}</td>
                    <td class="text-truncate" style="max-width:140px">{{ s.nombre_sesion }}</td>
                    <td class="text-truncate" style="max-width:120px">{{ s.origen }}</td>
                    <td class="text-truncate text-danger small" style="max-width:200px" :title="s.mensaje">
                      {{ s.mensaje || "—" }}
                    </td>
                    <td class="text-nowrap small">{{ formatFechaLocal(s.ultima_actualizacion) }}</td>
                    <td class="text-nowrap">
                      <router-link
                        :to="`/sesiones-fallidas?sesion=${s.id}`"
                        class="btn btn-outline-primary btn-sm"
                        title="Abrir en Sesiones fallidas (requiere JSON guardado)"
                      >
                        Ver / reprocesar
                      </router-link>
                    </td>
                  </tr>
                  <tr v-if="!resumen.errores?.length">
                    <td colspan="6" class="text-muted p-3">Sin errores</td>
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
