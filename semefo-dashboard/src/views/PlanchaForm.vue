<script setup lang="ts">
import { ref, watch } from "vue";
import { updatePlancha, createPlancha } from "../api/planchas";

const props = defineProps<{
    modelValue: any;
    modo: "create" | "edit";
}>();

const emit = defineEmits<{
    (e: "update:modelValue", v: any): void;
    (e: "saved"): void;
}>();

const form = ref({ ...props.modelValue });
const errors = ref<Record<string, string>>({});

// Debounced emitter to avoid emitting on every keystroke
const emitUpdateDebounced = (() => {
    let timer: number | null = null;
    const delay = 150; // ms, adjust if needed
    return (v: any) => {
        if (timer) clearTimeout(timer);
        // @ts-ignore
        timer = setTimeout(() => {
            emit("update:modelValue", v);
            timer = null;
        }, delay) as unknown as number;
    };
})();

/* Sync padre → hijo */
watch(() => props.modelValue, (v) => {
    // Only copy from parent when the incoming modelValue actually differs
    // This helps avoid overwriting the local `form` while the user types.
    try {
        if (JSON.stringify(v) !== JSON.stringify(form.value)) {
            form.value = { ...v };
        }
    } catch (e) {
        form.value = { ...v };
    }
});

/* Sync hijo → padre */
watch(form, (v) => emitUpdateDebounced(v), { deep: true });

function validar(): boolean {
    errors.value = {};

    if (!form.value.nombre?.trim()) {
        errors.value.nombre = "El nombre es obligatorio";
    }

    if (form.value.camara1_activa) {
        if (!form.value.camara1_ip)
            errors.value.camara1_ip = "IP requerida para cámara 1";
        if (!form.value.camara1_id)
            errors.value.camara1_id = "ID requerido para cámara 1";
    }

    if (form.value.camara2_activa) {
        if (!form.value.camara2_ip)
            errors.value.camara2_ip = "IP requerida para cámara 2";
        if (!form.value.camara2_id)
            errors.value.camara2_id = "ID requerido para cámara 2";
    }

    if (
        form.value.camara1_ip &&
        form.value.camara2_ip &&
        form.value.camara1_ip === form.value.camara2_ip
    ) {
        errors.value.camara2_ip =
            "La IP de la cámara 2 no puede ser igual a la cámara 1";
    }

    if (
        form.value.asignada &&
        !form.value.camara1_activa &&
        !form.value.camara2_activa
    ) {
        errors.value.asignada =
            "No se puede asignar una plancha sin cámaras activas";
    }

    return Object.keys(errors.value).length === 0;
}

async function guardar() {
    if (!validar()) return;

    if (props.modo === "create") {
        await createPlancha(form.value);
    } else {
        await updatePlancha(form.value.id, form.value);
    }

    emit("saved");
}
</script>

<template>
    <div class="card-body">

        <!-- ===================== -->
        <!-- DATOS GENERALES -->
        <!-- ===================== -->
        <h6 class="border-bottom pb-2 mb-3">Datos Generales</h6>

        <div class="row mb-3">
            <div class="col-md-6">
                <label class="form-label">Nombre</label>
                <input v-model="form.nombre" class="form-control" :class="{ 'is-invalid': errors.nombre }" />
                <div class="invalid-feedback">
                    {{ errors.nombre }}
                </div>
            </div>

            <div class="col-md-3">
                <label class="form-label">Activa</label>
                <select v-model="form.activo" class="form-select">
                    <option :value="true">Sí</option>
                    <option :value="false">No</option>
                </select>
            </div>

            <div class="col-md-3">
                <label class="form-label">Asignada</label>
                <select v-model="form.asignada" class="form-select" :class="{ 'is-invalid': errors.asignada }">
                    <option :value="true">Sí</option>
                    <option :value="false">No</option>
                </select>
                <div class="invalid-feedback d-block">
                    {{ errors.asignada }}
                </div>
            </div>
        </div>

        <!-- ===================== -->
        <!-- CÁMARA 1 -->
        <!-- ===================== -->
        <h6 class="border-bottom pb-2 mt-4">Cámara 1</h6>

        <div class="row mb-3">
            <div class="col-md-4">
                <label class="form-label">IP Cámara 1</label>
                <input v-model="form.camara1_ip" class="form-control" :disabled="!form.camara1_activa" :class="{ 'is-invalid': errors.camara1_ip }" />
                <div class="invalid-feedback">
                    {{ errors.camara1_ip }}
                </div>
            </div>

            <div class="col-md-4">
                <label class="form-label">ID Cámara 1</label>
                <input v-model="form.camara1_id" class="form-control" :disabled="!form.camara1_activa" :class="{ 'is-invalid': errors.camara1_id }" />
                <div class="invalid-feedback">
                    {{ errors.camara1_id }}
                </div>
            </div>

            <div class="col-md-4 d-flex align-items-end">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" v-model="form.camara1_activa" />
                    <label class="form-check-label">Activa</label>
                </div>
            </div>
        </div>

        <!-- ===================== -->
        <!-- CÁMARA 2 -->
        <!-- ===================== -->
        <h6 class="border-bottom pb-2 mt-4">Cámara 2</h6>

        <div class="row mb-4">
            <div class="col-md-4">
                <label class="form-label">IP Cámara 2</label>
                <input v-model="form.camara2_ip" class="form-control" :disabled="!form.camara2_activa" :class="{ 'is-invalid': errors.camara2_ip }" />
                <div class="invalid-feedback">
                    {{ errors.camara2_ip }}
                </div>
            </div>

            <div class="col-md-4">
                <label class="form-label">ID Cámara 2</label>
                <input v-model="form.camara2_id" class="form-control" :disabled="!form.camara2_activa" :class="{ 'is-invalid': errors.camara2_id }" />
                <div class="invalid-feedback">
                    {{ errors.camara2_id }}
                </div>
            </div>

            <div class="col-md-4 d-flex align-items-end">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" v-model="form.camara2_activa" />
                    <label class="form-check-label">Activa</label>
                </div>
            </div>
        </div>

        <!-- ===================== -->
        <!-- BOTÓN -->
        <!-- ===================== -->
        <div class="text-end">
            <button class="btn btn-primary" @click="guardar">
                {{ modo === "create" ? "Crear Plancha" : "Guardar Cambios" }}
            </button>
        </div>

    </div>
</template>
