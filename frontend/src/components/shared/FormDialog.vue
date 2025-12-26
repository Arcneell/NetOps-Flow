<template>
  <Dialog
    v-model:visible="visible"
    :header="header"
    :modal="true"
    :closable="true"
    :style="{ width: width }"
    :breakpoints="{ '960px': '75vw', '640px': '95vw' }"
    @keydown.enter.prevent="onEnterKey"
  >
    <slot />

    <template #footer>
      <div class="flex justify-between items-center w-full">
        <Button
          :label="computedCancelLabel"
          severity="secondary"
          text
          @click="handleCancel"
          :disabled="loading"
          class="cancel-btn"
        />
        <span class="submit-btn-wrapper">
          <Button
            :label="computedSubmitLabel"
            :severity="submitSeverity"
            @click="handleSubmit"
            :loading="loading"
            :disabled="disabled"
            class="submit-btn"
          />
        </span>
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
  if (!props.disabled && !props.loading) {
    emit('submit')
  }
}

function onEnterKey(event) {
  // Don't submit if focus is on a textarea (allow multiline input)
  if (event.target.tagName === 'TEXTAREA') {
    return
  }
  handleSubmit()
}

function handleCancel() {
  visible.value = false
  emit('cancel')
}
</script>

<style scoped>
.submit-btn-wrapper {
  display: inline-block;
  border-radius: 6px;
  box-shadow: 0 0 0 3px #0ea5e9;
}
.submit-btn-wrapper :deep(.p-button) {
  font-weight: 600;
  min-width: 120px;
}
</style>
