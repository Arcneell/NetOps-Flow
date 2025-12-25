<template>
  <Dialog
    v-model:visible="visible"
    :header="header"
    :modal="true"
    :closable="true"
    :style="{ width: '450px' }"
    :breakpoints="{ '640px': '90vw' }"
  >
    <div class="flex items-start gap-4">
      <i
        :class="[iconClass, 'text-3xl']"
        :style="{ color: iconColor }"
      />
      <div>
        <p class="m-0">{{ message }}</p>
        <slot name="content" />
      </div>
    </div>

    <template #footer>
      <div class="flex justify-between items-center w-full">
        <Button
          :label="computedCancelLabel"
          severity="secondary"
          text
          @click="handleCancel"
          class="cancel-btn"
        />
        <Button
          :label="computedConfirmLabel"
          :severity="severity"
          @click="handleConfirm"
          :loading="loading"
          class="confirm-btn min-w-[120px]"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  header: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'warning',
    validator: (value) => ['warning', 'danger', 'info'].includes(value)
  },
  confirmLabel: {
    type: String,
    default: ''
  },
  cancelLabel: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const severity = computed(() => {
  const severityMap = {
    warning: 'warning',
    danger: 'danger',
    info: 'info'
  }
  return severityMap[props.type] || 'warning'
})

const iconClass = computed(() => {
  const iconMap = {
    warning: 'pi pi-exclamation-triangle',
    danger: 'pi pi-trash',
    info: 'pi pi-info-circle'
  }
  return iconMap[props.type] || 'pi pi-question-circle'
})

const iconColor = computed(() => {
  const colorMap = {
    warning: 'var(--yellow-500)',
    danger: 'var(--red-500)',
    info: 'var(--blue-500)'
  }
  return colorMap[props.type] || 'var(--yellow-500)'
})

const computedConfirmLabel = computed(() => props.confirmLabel || t('common.confirm'))
const computedCancelLabel = computed(() => props.cancelLabel || t('common.cancel'))

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  visible.value = false
  emit('cancel')
}
</script>

<style scoped>
.cancel-btn {
  font-weight: 500;
}

.confirm-btn {
  font-weight: 600;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
  transition: all 0.15s ease;
}

.confirm-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
}

.confirm-btn:active:not(:disabled) {
  transform: translateY(0);
}
</style>
