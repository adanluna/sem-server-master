<template>
    <div class="card shadow-sm">
        <div class="card-header d-flex justify-content-between">
            <h5 class="mb-0">Planchas</h5>
            <router-link to="/planchas/nueva" class="btn btn-success">
                + Nueva Plancha
            </router-link>
        </div>

        <table class="table table-striped mb-0">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Nombre</th>
                    <th>Estado</th>
                    <th>Asignada</th>
                    <th class="text-end">Acciones</th>
                </tr>
            </thead>

            <tbody>
                <tr v-for="p in planchas" :key="p.id">
                    <td>{{ p.id }}</td>
                    <td>{{ p.nombre }}</td>
                    <td>
                        <span class="badge" :class="p.activo ? 'bg-success' : 'bg-secondary'">
                            {{ p.activo ? "Activa" : "Inactiva" }}
                        </span>
                    </td>

                    <td>
                        <span class="badge" :class="p.asignada ? 'bg-info' : 'bg-light text-dark'">
                            {{ p.asignada ? "Sí" : "No" }}
                        </span>
                    </td>
                    <td class="text-end">
                        <button class="btn btn-outline-primary btn-sm" @click="$router.push(`/planchas/${p.id}`)">
                            Configurar
                        </button>
                        <button v-if="!p.asignada" class="btn btn-outline-danger btn-sm ms-1" @click="confirmarBorrado(p)">
                            Borrar
                        </button>
                    </td>
                </tr>
            </tbody>
        </table>

    </div>
    <ConfirmDeleteModal ref="deleteModal" :nombre="toDelete?.nombre" @confirm="borrar" />
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { fetchPlanchas } from "../api/planchas";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.vue";
import { deletePlancha } from "../api/planchas";

const planchas = ref<any[]>([]);
const deleteModal = ref<any>(null);
let toDelete: any = null;

function confirmarBorrado(p: any) {
    toDelete = p;
    deleteModal.value.open();
}

async function borrar() {
    await deletePlancha(toDelete.id);
    await load();
}

async function load() {
    planchas.value = await fetchPlanchas();
}

onMounted(load);

</script>
