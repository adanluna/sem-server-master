<template>
    <div class="pagination">
        <button :disabled="page <= 1" @click="$emit('change', page - 1)">
            ◀
        </button>

        <span>Página {{ page }} de {{ totalPages }}</span>

        <button :disabled="page >= totalPages" @click="$emit('change', page + 1)">
            ▶
        </button>
    </div>
</template>

<script setup lang="ts">
defineProps<{
    page: number;
    totalPages: number;
}>();
</script>

<style scoped>
.pagination {
    display: flex;
    align-items: center;
    gap: 12px;
    justify-content: flex-end;
    margin-top: 12px;
}

button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}
</style>
