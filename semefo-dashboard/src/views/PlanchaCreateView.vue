<script setup lang="ts">
import { useRouter } from "vue-router";
import { ref } from "vue";
import PlanchaForm from "./PlanchaForm.vue";

const router = useRouter();

const nuevaPlancha = ref({
    nombre: "",
    activo: true,
    asignada: false,

    camara1_ip: "",
    camara1_id: "",
    camara1_activa: false,

    camara2_ip: "",
    camara2_id: "",
    camara2_activa: false,
});

function regresar() {
    router.push("/planchas");
}

function onSaved() {
    router.push("/planchas");
}
</script>

<template>
    <div class="card">
        <div class="card-header d-flex align-items-center justify-content-between">
            <h5 class="mb-0">Nueva Plancha</h5>

            <button class="btn btn-outline-secondary btn-sm" @click="regresar">
                ← Regresar
            </button>
        </div>

        <div class="card-body">
            <PlanchaForm v-model="nuevaPlancha" modo="create" @saved="onSaved" />
        </div>
    </div>
</template>
