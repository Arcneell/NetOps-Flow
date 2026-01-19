<template>
  <Transition name="route-loading">
    <div
      v-if="isRouteLoading"
      class="route-loading-overlay"
      aria-live="polite"
      aria-busy="true"
      role="status"
    >
      <div class="route-loading-backdrop" />
      <div class="route-loading-content">
        <i class="pi pi-spin pi-spinner route-loading-spinner" aria-hidden="true" />
        <span class="route-loading-text">{{ t('common.loading') }}</span>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { isRouteLoading } from '../../routeLoading'

const { t } = useI18n()
</script>

<style scoped>
.route-loading-overlay {
  position: fixed;
  inset: 0;
  z-index: 9998;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
}

.route-loading-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
}

.route-loading-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem 2rem;
  border-radius: var(--radius-xl);
  background: var(--bg-card-solid);
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-xl);
}

.route-loading-spinner {
  font-size: 2rem;
  color: var(--primary);
}

.route-loading-text {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-secondary);
}

/* Transition */
.route-loading-enter-active,
.route-loading-leave-active {
  transition: opacity 0.2s ease;
}

.route-loading-enter-from,
.route-loading-leave-to {
  opacity: 0;
}

.route-loading-enter-active .route-loading-content,
.route-loading-leave-active .route-loading-content {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.route-loading-enter-from .route-loading-content,
.route-loading-leave-to .route-loading-content {
  opacity: 0;
  transform: scale(0.97);
}
</style>
