<template>
    <div class="container-fluid">
        <div class="row vh-100">

            <!-- Sidebar -->
            <aside class="col-2 bg-dark text-white p-3">
                <Sidebar />
            </aside>

            <!-- Content -->
            <div class="col-10 d-flex flex-column p-0">

                <!-- Header -->
                <HeaderBar />

                <!-- Main -->
                <main class="flex-fill p-4 bg-body-secondary overflow-auto">
                    <RouterView />
                </main>

            </div>
        </div>
    </div>
</template>

<script setup>
import Sidebar from "../components/Sidebar.vue";
import HeaderBar from "../components/HeaderBar.vue";
</script>
