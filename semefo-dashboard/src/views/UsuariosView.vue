<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import type { DashboardUser, DashboardUserCreate, DashboardUserUpdate } from "../types/dashboard_user";
import {
    PERMISSION_KEYS,
    PERMISSION_LABELS,
    emptyPermissions,
    fullPermissions,
    type DashboardPermissions,
} from "../types/permissions";
import {
    listDashboardUsers,
    createDashboardUser,
    updateDashboardUser,
    deleteDashboardUser,
} from "../api/dashboard_users";

const loading = ref(false);
const rows = ref<DashboardUser[]>([]);
const formOpen = ref(false);
const formMode = ref<"create" | "edit">("create");
const editId = ref<number | null>(null);

const formUsername = ref("");
const formPassword = ref("");
const formActivo = ref(true);
const formPermissions = ref<DashboardPermissions>(emptyPermissions());

const editingProtected = computed(
    () => formMode.value === "edit" && rows.value.find((r) => r.id === editId.value)?.is_protected
);

function permSummary(p: DashboardPermissions): string {
    const labels = PERMISSION_KEYS.filter((k) => p[k]).map((k) => PERMISSION_LABELS[k]);
    return labels.length ? labels.join(", ") : "Sin acceso";
}

async function load() {
    loading.value = true;
    try {
        rows.value = await listDashboardUsers();
    } finally {
        loading.value = false;
    }
}

function openCreate() {
    formMode.value = "create";
    editId.value = null;
    formUsername.value = "";
    formPassword.value = "";
    formActivo.value = true;
    formPermissions.value = emptyPermissions();
    formOpen.value = true;
}

function openEdit(u: DashboardUser) {
    formMode.value = "edit";
    editId.value = u.id;
    formUsername.value = u.username;
    formPassword.value = "";
    formActivo.value = u.activo;
    formPermissions.value = u.is_protected ? fullPermissions() : { ...u.permissions };
    formOpen.value = true;
}

async function save() {
    if (formMode.value === "create") {
        if (!formUsername.value.trim()) {
            alert("Indica un nombre de usuario.");
            return;
        }
        if (formPassword.value.length < 8) {
            alert("La contraseña debe tener al menos 8 caracteres.");
            return;
        }
        loading.value = true;
        try {
            const payload: DashboardUserCreate = {
                username: formUsername.value.trim(),
                password: formPassword.value,
                activo: formActivo.value,
                permissions: { ...formPermissions.value },
            };
            await createDashboardUser(payload);
            formOpen.value = false;
            await load();
        } catch {
            alert("No se pudo crear el usuario (¿ya existe?).");
        } finally {
            loading.value = false;
        }
        return;
    }

    if (!editId.value) return;
    const update: DashboardUserUpdate = {
        activo: formActivo.value,
        permissions: { ...formPermissions.value },
    };
    if (formPassword.value.trim()) {
        if (formPassword.value.length < 8) {
            alert("La contraseña debe tener al menos 8 caracteres.");
            return;
        }
        update.password = formPassword.value;
    }

    loading.value = true;
    try {
        await updateDashboardUser(editId.value, update);
        formOpen.value = false;
        await load();
    } catch {
        alert("No se pudo actualizar el usuario.");
    } finally {
        loading.value = false;
    }
}

async function confirmDelete(u: DashboardUser) {
    if (u.is_protected) {
        alert("No se puede eliminar el usuario administrador por defecto.");
        return;
    }
    if (!confirm(`¿Eliminar al usuario "${u.username}"?`)) return;

    loading.value = true;
    try {
        await deleteDashboardUser(u.id);
        await load();
    } catch {
        alert("No se pudo eliminar el usuario.");
    } finally {
        loading.value = false;
    }
}

onMounted(load);
</script>

<template>
    <div class="card shadow-sm">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">Usuarios del panel</h5>
            <button class="btn btn-success btn-sm" @click="openCreate">+ Nuevo usuario</button>
        </div>

        <div v-if="loading && !rows.length" class="card-body text-muted">Cargando...</div>

        <table v-else class="table table-striped mb-0">
            <thead>
                <tr>
                    <th>Usuario</th>
                    <th>Activo</th>
                    <th>Permisos</th>
                    <th>Último acceso</th>
                    <th class="text-end">Acciones</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="u in rows" :key="u.id">
                    <td>
                        {{ u.username }}
                        <span v-if="u.is_protected" class="badge bg-secondary ms-1">protegido</span>
                    </td>
                    <td>
                        <span class="badge" :class="u.activo ? 'bg-success' : 'bg-secondary'">
                            {{ u.activo ? "Sí" : "No" }}
                        </span>
                    </td>
                    <td class="small">{{ permSummary(u.permissions) }}</td>
                    <td class="small text-muted">{{ u.last_login_at || "—" }}</td>
                    <td class="text-end text-nowrap">
                        <button class="btn btn-outline-primary btn-sm" @click="openEdit(u)">Editar</button>
                        <button
                            v-if="!u.is_protected"
                            class="btn btn-outline-danger btn-sm ms-1"
                            @click="confirmDelete(u)"
                        >
                            Eliminar
                        </button>
                    </td>
                </tr>
                <tr v-if="!rows.length">
                    <td colspan="5" class="text-muted p-3">Sin usuarios</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div v-if="formOpen" class="modal fade show d-block" tabindex="-1" style="background: rgba(0,0,0,0.45)">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        {{ formMode === "create" ? "Nuevo usuario" : `Editar: ${formUsername}` }}
                    </h5>
                    <button type="button" class="btn-close" @click="formOpen = false" />
                </div>
                <div class="modal-body">
                    <div v-if="formMode === 'create'" class="mb-3">
                        <label class="form-label">Usuario</label>
                        <input v-model="formUsername" class="form-control" autocomplete="off" />
                    </div>

                    <div class="mb-3">
                        <label class="form-label">
                            {{ formMode === "create" ? "Contraseña" : "Nueva contraseña (opcional)" }}
                        </label>
                        <input
                            v-model="formPassword"
                            type="password"
                            class="form-control"
                            autocomplete="new-password"
                        />
                    </div>

                    <div v-if="!editingProtected" class="mb-3 form-check">
                        <input id="activo" v-model="formActivo" type="checkbox" class="form-check-input" />
                        <label class="form-check-label" for="activo">Usuario activo</label>
                    </div>

                    <p class="fw-semibold mb-2">Acceso a secciones</p>
                    <p v-if="editingProtected" class="text-muted small">
                        El usuario <strong>admin</strong> siempre tiene acceso completo.
                    </p>
                    <div class="row g-2">
                        <div v-for="key in PERMISSION_KEYS" :key="key" class="col-md-6">
                            <div class="form-check">
                                <input
                                    :id="`perm-${key}`"
                                    v-model="formPermissions[key]"
                                    type="checkbox"
                                    class="form-check-input"
                                    :disabled="editingProtected"
                                />
                                <label class="form-check-label" :for="`perm-${key}`">
                                    {{ PERMISSION_LABELS[key] }}
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" @click="formOpen = false">Cancelar</button>
                    <button class="btn btn-primary" :disabled="loading" @click="save">Guardar</button>
                </div>
            </div>
        </div>
    </div>
</template>
