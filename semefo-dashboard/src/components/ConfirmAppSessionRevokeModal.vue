<template>
    <div class="modal fade" ref="modalRef" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title text-danger">Cerrar sesión app</h5>
                    <button type="button" class="btn-close" @click="close"></button>
                </div>

                <div class="modal-body">
                    ¿Confirmas que deseas cerrar la sesión de
                    <strong>{{ usuario }}</strong>
                    en la tablet <strong>{{ tabletId }}</strong>?
                    <br />
                    <span class="text-muted small">
                        El operador deberá iniciar sesión de nuevo en la tablet.
                    </span>
                </div>

                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" @click="close">
                        Cancelar
                    </button>
                    <button
                        type="button"
                        class="btn btn-danger"
                        :disabled="confirming"
                        @click="confirm"
                    >
                        {{ confirming ? "Cerrando…" : "Sí, cerrar sesión" }}
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
    usuario: {
        type: String,
        default: "",
    },
    tabletId: {
        type: String,
        default: "",
    },
    confirming: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(["confirm"]);

const modalRef = ref<HTMLElement | null>(null);
let modal: InstanceType<typeof Modal>;

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
}

defineExpose({ open, close });
</script>
