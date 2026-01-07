<template>
  <span
    v-if="daysRemaining !== null"
    :class="[
      'expiry-badge inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
      badgeClass,
      { 'animate-pulse-slow': isPulsing }
    ]"
    :title="tooltipText"
  >
    <span v-if="showIcon" class="expiry-dot w-2 h-2 rounded-full" :class="dotClass"></span>
    <span>{{ label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  date: {
    type: [String, Date],
    required: true
  },
  criticalDays: {
    type: Number,
    default: 7
  },
  warningDays: {
    type: Number,
    default: 30
  },
  showIcon: {
    type: Boolean,
    default: true
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const { t } = useI18n()

const daysRemaining = computed(() => {
  if (!props.date) return null
  const expiryDate = typeof props.date === 'string' ? new Date(props.date) : props.date
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  expiryDate.setHours(0, 0, 0, 0)
  const diffTime = expiryDate.getTime() - today.getTime()
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return diffDays
})

const severity = computed(() => {
  if (daysRemaining.value === null) return 'none'
  if (daysRemaining.value < 0) return 'expired'
  if (daysRemaining.value <= props.criticalDays) return 'critical'
  if (daysRemaining.value <= props.warningDays) return 'warning'
  return 'ok'
})

const isPulsing = computed(() => {
  return severity.value === 'critical' || severity.value === 'expired'
})

const badgeClass = computed(() => {
  switch (severity.value) {
    case 'expired':
      return 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300'
    case 'critical':
      return 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300'
    case 'warning':
      return 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300'
    case 'ok':
      return 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300'
    default:
      return 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
  }
})

const dotClass = computed(() => {
  switch (severity.value) {
    case 'expired':
    case 'critical':
      return 'bg-red-500 animate-ping-slow'
    case 'warning':
      return 'bg-yellow-500'
    case 'ok':
      return 'bg-green-500'
    default:
      return 'bg-gray-400'
  }
})

const label = computed(() => {
  if (daysRemaining.value === null) return ''
  if (daysRemaining.value < 0) {
    return props.compact ? t('status.expired') : t('contracts.expiredDaysAgo', { days: Math.abs(daysRemaining.value) })
  }
  if (daysRemaining.value === 0) return t('contracts.expiresToday')
  if (daysRemaining.value === 1) return t('contracts.expiresTomorrow')
  return props.compact
    ? `${daysRemaining.value}d`
    : t('contracts.daysRemainingLabel', { days: daysRemaining.value })
})

const tooltipText = computed(() => {
  if (!props.date) return ''
  const expiryDate = typeof props.date === 'string' ? new Date(props.date) : props.date
  return expiryDate.toLocaleDateString()
})
</script>

<style scoped>
@keyframes ping-slow {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.5);
    opacity: 0.5;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes pulse-slow {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.animate-ping-slow {
  animation: ping-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-pulse-slow {
  animation: pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.expiry-dot {
  flex-shrink: 0;
}
</style>
