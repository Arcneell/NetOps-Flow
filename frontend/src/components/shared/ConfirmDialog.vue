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
      <div class="flex justify-end gap-2">
        <Button
          :label="cancelLabel"
          severity="secondary"
          text
          @click="handleCancel"
        />
        <Button
          :label="confirmLabel"
          :severity="severity"
          @click="handleConfirm"
          :loading="loading"
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
