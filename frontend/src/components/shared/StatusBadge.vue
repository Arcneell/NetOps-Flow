<template>
  <Tag :severity="severity" :value="displayLabel" :class="customClass" />
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'

const props = defineProps({
  status: {
    type: String,
    required: true
  },
  type: {
    type: String,
    default: 'equipment', // equipment, ip, execution
    validator: (value) => ['equipment', 'ip', 'execution'].includes(value)
  },
  customClass: {
    type: String,
    default: ''
  }
})

const { t } = useI18n()

const statusConfig = {
  equipment: {
    in_service: { severity: 'success', key: 'status.inService' },
    in_stock: { severity: 'info', key: 'status.inStock' },
    retired: { severity: 'danger', key: 'status.retired' },
    maintenance: { severity: 'warning', key: 'status.maintenance' }
  },
  ip: {
    active: { severity: 'success', key: 'status.active' },
    available: { severity: 'secondary', key: 'status.available' }
  },
  execution: {
    success: { severity: 'success', key: 'common.success' },
    failure: { severity: 'danger', key: 'common.error' },
    running: { severity: 'info', key: 'common.loading' },
    pending: { severity: 'warning', key: 'common.loading' },
    cancelled: { severity: 'secondary', key: 'common.cancelled' }
  }
}

const severity = computed(() => {
  const config = statusConfig[props.type]?.[props.status]
  return config?.severity || 'secondary'
})

const displayLabel = computed(() => {
  const config = statusConfig[props.type]?.[props.status]
  if (config?.key) {
    return t(config.key)
  }
  return props.status
})
</script>
