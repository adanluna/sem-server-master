<template>
    <div class="modal fade" ref="modalRef" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">

                <div class="modal-header">
                    <h5 class="modal-title text-danger">Confirmar eliminación</h5>
                    <button class="btn-close" @click="close"></button>
                </div>

                <div class="modal-body">
                    ¿Seguro que deseas borrar la plancha
                    <strong>{{ nombre }}</strong>?
                    <br />
                    Esta acción no se puede deshacer.
                </div>

                <div class="modal-footer">
                    <button class="btn btn-secondary" @click="close">
                        Cancelar
                    </button>
                    <button class="btn btn-danger" @click="confirm">
                        Borrar
                    </button>
                </div>

            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Modal } from "bootstrap";

defineProps({
    nombre: {
        type: String,
        default: "",
    }
});
const emit = defineEmits(["confirm"]);

const modalRef = ref<HTMLElement | null>(null);
let modal: Modal;



onMounted(() => {
    modal = new Modal(modalRef.value!);
});

function open() {
    modal.show();
}

function close() {
    modal.hide();
}

function confirm() {
    emit("confirm");
    close();
}

defineExpose({ open });
</script>
