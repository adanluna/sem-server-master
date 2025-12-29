<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "../api/api";
import PlanchaForm from "./PlanchaForm.vue";

const route = useRoute();
const router = useRouter();

const plancha = ref<any>(null);

onMounted(async () => {
    const { data } = await api.get(`/planchas/${route.params.id}`);
    plancha.value = data;
});

function regresar() {
    router.push("/planchas");
}

function onSaved() {
    router.push("/planchas");
}
</script>

<template>
    <div v-if="plancha" class="card">
        <div class="card-header d-flex align-items-center justify-content-between">
            <h5 class="mb-0">Editar Plancha</h5>

            <button class="btn btn-outline-secondary btn-sm" @click="regresar">
                ← Regresar
            </button>
        </div>

        <div class="card-body">
            <PlanchaForm v-model="plancha" modo="edit" @saved="onSaved" />
        </div>
    </div>
</template>
