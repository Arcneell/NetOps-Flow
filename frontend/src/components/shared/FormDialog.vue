<template>
  <Dialog
    v-model:visible="visible"
    :header="header"
    :modal="true"
    :closable="true"
    :style="{ width: width }"
    :breakpoints="{ '960px': '75vw', '640px': '95vw' }"
  >
    <form @submit.prevent="handleSubmit">
      <slot />
    </form>

    <template #footer>
      <div class="flex justify-end gap-2">
        <Button
          :label="cancelLabel"
          severity="secondary"
          text
          @click="handleCancel"
          :disabled="loading"
        />
        <Button
          :label="submitLabel"
          :severity="submitSeverity"
          @click="handleSubmit"
          :loading="loading"
          :disabled="disabled"
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
    required: true
  },
  width: {
    type: String,
    default: '500px'
  },
  submitLabel: {
    type: String,
    default: ''
  },
  cancelLabel: {
    type: String,
    default: ''
  },
  submitSeverity: {
    type: String,
    default: 'primary'
  },
  loading: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'submit', 'cancel'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const computedSubmitLabel = computed(() => props.submitLabel || t('common.save'))
const computedCancelLabel = computed(() => props.cancelLabel || t('common.cancel'))

function handleSubmit() {
  emit('submit')
}

function handleCancel() {
  visible.value = false
  emit('cancel')
}
</script>
