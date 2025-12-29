<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { loginDashboard } from "../api/auth";
import { parseJwt } from "../utils/jwt";

const router = useRouter();

const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

async function login() {
    error.value = "";
    loading.value = true;

    try {
        const res = await loginDashboard(username.value, password.value);

        localStorage.setItem(
            "token",
            res.access_token
        );

        const payload = parseJwt(res.access_token);

        if (payload?.sub) {
            // "dash:admin" -> "admin"
            const cleanUser = payload.sub.includes(":")
                ? payload.sub.split(":")[1]
                : payload.sub;

            localStorage.setItem("user_nombre", cleanUser);
        }
        router.push("/dashboard");
    } catch (e) {
        error.value = "Usuario o contraseña incorrectos";
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="login-wrapper d-flex align-items-center justify-content-center">
        <div class="card shadow-sm login-card">
            <div class="card-body">

                <!-- LOGO / TÍTULO -->
                <div class="text-center mb-4">
                    <h3 class="fw-bold mb-1">SEMEFO</h3>
                    <p class="text-muted mb-0">Dashboard administrativo</p>
                </div>

                <!-- ERROR -->
                <div v-if="error" class="alert alert-danger py-2">
                    {{ error }}
                </div>

                <!-- FORM -->
                <form @submit.prevent="login">

                    <div class="mb-3">
                        <label class="form-label">Usuario</label>
                        <input v-model="username" type="text" class="form-control" placeholder="usuario" required autofocus />
                    </div>

                    <div class="mb-4">
                        <label class="form-label">Contraseña</label>
                        <input v-model="password" type="password" class="form-control" placeholder="••••••••" required />
                    </div>

                    <button class="btn btn-primary w-100" type="submit" :disabled="loading">
                        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                        Iniciar sesión
                    </button>

                </form>
            </div>
        </div>
    </div>
</template>

<style scoped>
.login-wrapper {
    min-height: 100vh;
    background: #f1f3f5;
}

.login-card {
    width: 100%;
    max-width: 380px;
    border-radius: 8px;
}
</style>
