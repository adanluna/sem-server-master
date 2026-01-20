<script setup lang="ts">
import { ref, onMounted } from "vue";
import type { ServiceClient, ServiceClientCreate, ServiceClientUpdate } from "../types/service_client";
import {
    listServiceClients,
    createServiceClient,
    updateServiceClient,
    rotateServiceClientToken,
    activateServiceClient,
    deactivateServiceClient,
    deleteServiceClient
} from "../api/service_clients";

const loading = ref(false);
const q = ref("");
const soloActivos = ref(false);
const rows = ref<ServiceClient[]>([]);

const showTokenModal = ref(false);
const lastToken = ref<string>("");
const lastClientId = ref<string>("");

const formMode = ref<"create" | "edit">("create");
const formOpen = ref(false);

const formCreate = ref<ServiceClientCreate>({
    client_id: "",
    roles: "semefo_read",
    activo: true,
    allowed_ips: "",
    token: null,
});

const formEditId = ref<number | null>(null);
const formEdit = ref<ServiceClientUpdate>({
    roles: "",
    activo: true,
    allowed_ips: "",
});

async function load() {
    loading.value = true;
    try {
        rows.value = await listServiceClients({ q: q.value || undefined, solo_activos: soloActivos.value });
    } finally {
        loading.value = false;
    }
}

function openCreate() {
    formMode.value = "create";
    formCreate.value = { client_id: "", roles: "semefo_read", activo: true, allowed_ips: "", token: null };
    formOpen.value = true;
}

function openEdit(sc: ServiceClient) {
    formMode.value = "edit";
    formEditId.value = sc.id;
    formEdit.value = {
        roles: sc.roles,
        activo: sc.activo,
        allowed_ips: sc.allowed_ips ?? "",
    };
    formOpen.value = true;
}

async function save() {
    loading.value = true;
    try {
        if (formMode.value === "create") {
            const res = await createServiceClient({
                ...formCreate.value,
                allowed_ips: (formCreate.value.allowed_ips || "").trim() || null,
                token: formCreate.value.token?.trim() || null,
            });

            // Mostrar token solo aquí
            lastToken.value = res.token;
            lastClientId.value = res.service_client.client_id;
            showTokenModal.value = true;

            formOpen.value = false;
            await load();
            return;
        }

        // edit
        if (!formEditId.value) return;
        await updateServiceClient(formEditId.value, {
            roles: formEdit.value.roles?.trim() || undefined,
            activo: formEdit.value.activo,
            allowed_ips: (formEdit.value.allowed_ips || "").trim() || null,
        });

        formOpen.value = false;
        await load();
    } finally {
        loading.value = false;
    }
}

async function rotate(sc: ServiceClient) {
    if (!confirm(`¿Rotar token para ${sc.client_id}? El anterior quedará inválido.`)) return;

    loading.value = true;
    try {
        const res = await rotateServiceClientToken(sc.id);
        lastToken.value = res.token;
        lastClientId.value = res.service_client.client_id;
        showTokenModal.value = true;
        await load();
    } finally {
        loading.value = false;
    }
}

async function toggle(sc: ServiceClient) {
    loading.value = true;
    try {
        if (sc.activo) await deactivateServiceClient(sc.id);
        else await activateServiceClient(sc.id);
        await load();
    } finally {
        loading.value = false;
    }
}

async function confirmDelete(sc: ServiceClient) {
    const ok = confirm(
        `⚠️ ELIMINAR SERVICE CLIENT\n\n` +
        `Client ID: ${sc.client_id}\n\n` +
        `Esta acción:\n` +
        `• Revoca el token inmediatamente\n` +
        `• Puede tumbar workers activos\n` +
        `• NO se puede deshacer\n\n` +
        `¿Deseas continuar?`
    );

    if (!ok) return;

    loading.value = true;
    try {
        await deleteServiceClient(sc.id);
        await load();
        alert("Service client eliminado correctamente.");
    } catch (e) {
        alert("No se pudo eliminar el service client.");
    } finally {
        loading.value = false;
    }
}


function copyToken() {
    const text = (lastToken.value || "").trim();
    if (!text) return;

    console.log("[copyToken] intentando copiar...");

    // ✅ Clipboard API (solo HTTPS o localhost)
    if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(text)
            .then(() => {
                console.log("[copyToken] copiado con clipboard API");
                alert("Token copiado al portapapeles.");
            })
            .catch((e) => {
                console.warn("[copyToken] clipboard API falló, usando fallback", e);
                fallbackCopy(text);
            });
        return;
    }

    // ❌ HTTP por IP / sin permisos
    fallbackCopy(text);
}

function fallbackCopy(text: string) {
    try {
        const textarea = document.createElement("textarea");
        textarea.value = text;

        // Importante: debe ser seleccionable
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        textarea.style.top = "0";
        textarea.style.opacity = "0";

        document.body.appendChild(textarea);

        // Selección robusta
        textarea.focus();
        textarea.select();
        textarea.setSelectionRange(0, textarea.value.length);

        const ok = document.execCommand("copy");
        document.body.removeChild(textarea);

        if (ok) {
            console.log("[copyToken] copiado con fallback execCommand");
            alert("Token copiado al portapapeles.");
        } else {
            console.warn("[copyToken] execCommand devolvió false");
            alert("No se pudo copiar automáticamente. Cópialo manualmente.");
        }
    } catch (err) {
        console.error("[copyToken] error en fallback", err);
        alert("No se pudo copiar automáticamente. Cópialo manualmente.");
    }
}


onMounted(load);
</script>

<template>
    <div class="p-4">
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-semibold">Service Clients (API Keys)</h2>
            <button class="btn" @click="openCreate">+ Nuevo</button>
        </div>

        <div class="flex gap-2 mb-3">
            <input class="input" v-model="q" placeholder="Buscar por client_id..." @keyup.enter="load" />
            <label class="flex items-center gap-2">
                <input type="checkbox" v-model="soloActivos" @change="load" />
                Solo activos
            </label>
            <button class="btn" @click="load" :disabled="loading">Buscar</button>
        </div>

        <div class="card">
            <table class="table w-full">
                <thead>
                    <tr>
                        <th>client_id</th>
                        <th>roles</th>
                        <th>activo</th>
                        <th>allowed_ips</th>
                        <th>last_used</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="r in rows" :key="r.id">
                        <td class="font-mono">{{ r.client_id }}</td>
                        <td class="font-mono">{{ r.roles }}</td>
                        <td>
                            <span :class="r.activo ? 'text-green-600' : 'text-red-600'">
                                {{ r.activo ? "SI" : "NO" }}
                            </span>
                        </td>
                        <td class="font-mono">{{ r.allowed_ips || "-" }}</td>
                        <td class="font-mono">{{ r.last_used_at || "-" }}</td>
                        <td class="flex gap-2 justify-end">
                            <button class="btn" @click="openEdit(r)">Editar</button>
                            <button class="btn" @click="rotate(r)">Rotar token</button>
                            <button class="btn" @click="toggle(r)">
                                {{ r.activo ? "Desactivar" : "Activar" }}
                            </button>
                            <button class="btn btn-danger" @click="confirmDelete(r)">
                                Eliminar
                            </button>
                        </td>

                    </tr>
                    <tr v-if="rows.length === 0">
                        <td colspan="6" class="text-center py-6 text-gray-500">Sin registros</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Modal Form -->
        <div v-if="formOpen" class="modal">
            <div class="modal-content">
                <h3 class="text-lg font-semibold mb-3">
                    {{ formMode === "create" ? "Nuevo service client" : "Editar service client" }}
                </h3>

                <div v-if="formMode === 'create'" class="grid gap-2">
                    <label>client_id</label>
                    <input class="input" v-model="formCreate.client_id" />

                    <label>roles</label>
                    <input class="input" v-model="formCreate.roles" placeholder="semefo_read" />

                    <label>allowed_ips (opcional)</label>
                    <input class="input" v-model="formCreate.allowed_ips" placeholder="172.21.82.0/24, 172.21.82.4" />

                    <label class="flex items-center gap-2">
                        <input type="checkbox" v-model="formCreate.activo" />
                        activo
                    </label>

                    <label>token (opcional)</label>
                    <input class="input" v-model="formCreate.token" placeholder="Si lo dejas vacío, se genera" />
                </div>

                <div v-else class="grid gap-2">
                    <label>roles</label>
                    <input class="input" v-model="formEdit.roles" />

                    <label>allowed_ips</label>
                    <input class="input" v-model="formEdit.allowed_ips" />

                    <label class="flex items-center gap-2">
                        <input type="checkbox" v-model="formEdit.activo" />
                        activo
                    </label>
                </div>

                <div class="flex justify-end gap-2 mt-4">
                    <button class="btn" @click="formOpen = false">Cancelar</button>
                    <button class="btn btn-primary" @click="save" :disabled="loading">Guardar</button>
                </div>
            </div>
        </div>

        <!-- Token Modal -->
        <div v-if="showTokenModal" class="modal">
            <div class="modal-content">
                <h3 class="text-lg font-semibold mb-2">Token generado</h3>
                <p class="text-sm mb-2">
                    Cliente: <span class="font-mono">{{ lastClientId }}</span>
                </p>

                <div class="p-3 bg-gray-100 rounded font-mono break-all">
                    {{ lastToken }}
                </div>

                <p class="text-xs text-red-600 mt-2">
                    Guárdalo ahora. No se volverá a mostrar en listados.
                </p>

                <div class="flex justify-end gap-2 mt-4">
                    <button class="btn" @click="copyToken">Copiar</button>
                    <button class="btn btn-primary" @click="showTokenModal = false">Cerrar</button>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* Ajusta a tu CSS real: aquí pongo clases genéricas */
.btn {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
}

.btn-primary {
    border-color: #333;
}

.input {
    padding: 8px 10px;
    border: 1px solid #ddd;
    border-radius: 8px;
    width: 100%;
}

.card {
    border: 1px solid #eee;
    border-radius: 12px;
    padding: 8px;
}

.modal {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-content {
    background: white;
    border-radius: 12px;
    padding: 16px;
    width: 520px;
    max-width: 95vw;
}

.table th,
.table td {
    padding: 10px;
    border-bottom: 1px solid #f0f0f0;
}

.btn-danger {
    border-color: #dc2626;
    color: #f0f0f0
}

.btn-danger:hover {
    background: #fee2e2;
}
</style>
