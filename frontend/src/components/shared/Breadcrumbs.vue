<template>
  <nav class="breadcrumbs flex items-center gap-2 text-sm mb-4" aria-label="Breadcrumb">
    <!-- Home -->
    <router-link
      to="/"
      class="breadcrumb-item flex items-center gap-1 opacity-60 hover:opacity-100 transition-opacity"
    >
      <i class="pi pi-home text-sm"></i>
      <span v-if="!compact" class="hidden sm:inline">{{ t('nav.dashboard') }}</span>
    </router-link>

    <!-- Separator & Items -->
    <template v-for="(item, index) in items" :key="index">
      <i class="pi pi-chevron-right text-xs opacity-40"></i>

      <!-- Last item (current page) -->
      <span
        v-if="index === items.length - 1"
        class="breadcrumb-current font-medium"
        :class="{ 'truncate max-w-48': truncate }"
      >
        <i v-if="item.icon" :class="['pi', item.icon, 'mr-1.5']"></i>
        {{ item.label }}
      </span>

      <!-- Navigable item -->
      <router-link
        v-else
        :to="item.to"
        class="breadcrumb-item opacity-60 hover:opacity-100 transition-opacity"
        :class="{ 'truncate max-w-32': truncate }"
      >
        <i v-if="item.icon" :class="['pi', item.icon, 'mr-1.5']"></i>
        {{ item.label }}
      </router-link>
    </template>
  </nav>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  items: {
    type: Array,
    required: true,
    validator: (value) => value.every(item => item.label)
  },
  compact: {
    type: Boolean,
    default: false
  },
  truncate: {
    type: Boolean,
    default: true
  }
})
</script>

<style scoped>
.breadcrumbs {
  min-height: 24px;
}

.breadcrumb-item {
  text-decoration: none;
  color: inherit;
}

.breadcrumb-item:hover {
  color: var(--primary-color, #0ea5e9);
}

.breadcrumb-current {
  color: var(--text-color);
}
</style>
