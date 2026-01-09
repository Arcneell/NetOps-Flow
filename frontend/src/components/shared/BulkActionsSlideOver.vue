<template>
  <SlideOver
    v-model="visible"
    :title="title"
    :subtitle="t('bulk.itemsSelected', { count: selectedCount })"
    icon="pi-list-check"
    size="md"
  >
    <div class="space-y-6">
      <!-- Selection Summary -->
      <div class="selection-summary p-4 rounded-xl">
        <div class="flex items-center gap-3 mb-3">
          <div class="selection-icon w-10 h-10 rounded-lg flex items-center justify-center">
            <i class="pi pi-check-square text-lg"></i>
          </div>
          <div>
            <div class="text-2xl font-bold text-theme-primary">{{ selectedCount }}</div>
            <div class="text-sm text-theme-secondary">{{ t('bulk.elementsSelected') }}</div>
          </div>
        </div>
        <Button
          :label="t('common.clearSelection')"
          icon="pi pi-times"
          text
          size="small"
          severity="secondary"
          @click="$emit('clear-selection')"
        />
      </div>

      <!-- Available Actions -->
      <div class="space-y-3">
        <h4 class="text-sm font-semibold uppercase tracking-wide text-theme-secondary mb-4">
          {{ t('bulk.availableActions') }}
        </h4>

        <!-- Dynamic action sections -->
        <slot></slot>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-between items-center">
        <span class="text-sm text-theme-secondary">{{ t('bulk.selectActionAbove') }}</span>
        <Button
          :label="t('common.close')"
          severity="secondary"
          outlined
          @click="visible = false"
        />
      </div>
    </template>
  </SlideOver>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import SlideOver from './SlideOver.vue'

const props = defineProps({
  modelValue: Boolean,
  title: {
    type: String,
    default: 'Bulk Actions'
  },
  selectedCount: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:modelValue', 'clear-selection'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})
</script>

<style scoped>
.selection-summary {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
}

.selection-icon {
  background: var(--primary-light);
}

.selection-icon i {
  color: var(--primary);
}

.text-theme-primary {
  color: var(--text-primary);
}

.text-theme-secondary {
  color: var(--text-secondary);
}
</style>
