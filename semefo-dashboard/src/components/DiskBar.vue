<template>
    <div>
        <div class="mb-2">
            <strong>Total:</strong> {{ disk.total_gb }} GB
        </div>
        <div class="mb-2">
            <strong>Usado:</strong> {{ disk.usado_gb }} GB
        </div>
        <div class="mb-2">
            <strong>Libre:</strong> {{ disk.libre_gb }} GB
        </div>

        <div class="progress mt-2">
            <div class="progress-bar" :class="barClass" :style="{ width: percent + '%' }">
                {{ percent }}%
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ disk: any }>();

const percent = computed(() =>
    Math.round((props.disk.usado_gb / props.disk.total_gb) * 100)
);

const barClass = computed(() => {
    if (percent.value < 70) return "bg-success";
    if (percent.value < 85) return "bg-warning";
    return "bg-danger";
});
</script>
