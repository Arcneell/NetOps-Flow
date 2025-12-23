<template>
  <div class="data-table-wrapper">
    <!-- Header with title and actions -->
    <div v-if="showHeader" class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-3">
        <h3 v-if="title" class="text-xl font-semibold m-0">{{ title }}</h3>
        <Tag v-if="showCount" :value="`${totalRecords} ${countLabel}`" severity="secondary" />
      </div>
      <div class="flex items-center gap-2">
        <slot name="header-actions" />
        <Button
          v-if="showCreate"
          :label="createLabel"
          icon="pi pi-plus"
          @click="$emit('create')"
        />
      </div>
    </div>

    <!-- Search and filters -->
    <div v-if="showSearch || $slots.filters" class="flex flex-wrap items-center gap-3 mb-4">
      <span v-if="showSearch" class="p-input-icon-left flex-1" style="min-width: 250px; max-width: 400px;">
        <i class="pi pi-search" />
        <InputText
          v-model="searchQuery"
          :placeholder="searchPlaceholder"
          class="w-full"
          @input="handleSearch"
        />
      </span>
      <slot name="filters" />
    </div>

    <!-- DataTable -->
    <DataTable
      :value="data"
      :loading="loading"
      :paginator="paginator"
      :rows="rows"
      :rowsPerPageOptions="rowsPerPageOptions"
      :totalRecords="totalRecords"
      :lazy="lazy"
      :sortField="sortField"
      :sortOrder="sortOrder"
      :dataKey="dataKey"
      :rowHover="true"
      :stripedRows="stripedRows"
      :showGridlines="showGridlines"
      responsiveLayout="scroll"
      class="custom-datatable"
      @page="handlePage"
      @sort="handleSort"
      @row-click="handleRowClick"
    >
      <template #empty>
        <div class="text-center py-8 text-gray-500">
          <i class="pi pi-inbox text-4xl mb-3" />
          <p>{{ emptyMessage }}</p>
        </div>
      </template>

      <template #loading>
        <div class="text-center py-8">
          <i class="pi pi-spin pi-spinner text-4xl" />
        </div>
      </template>

      <slot />

      <!-- Actions column -->
      <Column v-if="showActions" :header="actionsLabel" :style="{ width: actionsWidth }">
        <template #body="slotProps">
          <div class="flex gap-1">
            <Button
              v-if="showView"
              icon="pi pi-eye"
              text
              rounded
              severity="info"
              @click.stop="$emit('view', slotProps.data)"
              v-tooltip.top="viewTooltip"
            />
            <Button
              v-if="showEdit"
              icon="pi pi-pencil"
              text
              rounded
              severity="warning"
              @click.stop="$emit('edit', slotProps.data)"
              v-tooltip.top="editTooltip"
            />
            <Button
              v-if="showDelete"
              icon="pi pi-trash"
              text
              rounded
              severity="danger"
              @click.stop="$emit('delete', slotProps.data)"
              v-tooltip.top="deleteTooltip"
            />
            <slot name="row-actions" :data="slotProps.data" />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  // Pagination
  paginator: {
    type: Boolean,
    default: true
  },
  rows: {
    type: Number,
    default: 10
  },
  rowsPerPageOptions: {
    type: Array,
    default: () => [5, 10, 25, 50]
  },
  totalRecords: {
    type: Number,
    default: 0
  },
  lazy: {
    type: Boolean,
    default: false
  },
  // Sorting
  sortField: {
    type: String,
    default: null
  },
  sortOrder: {
    type: Number,
    default: 1
  },
  // Display
  dataKey: {
    type: String,
    default: 'id'
  },
  stripedRows: {
    type: Boolean,
    default: true
  },
  showGridlines: {
    type: Boolean,
    default: false
  },
  emptyMessage: {
    type: String,
    default: ''
  },
  // Header
  showHeader: {
    type: Boolean,
    default: true
  },
  showCount: {
    type: Boolean,
    default: true
  },
  countLabel: {
    type: String,
    default: 'items'
  },
  // Search
  showSearch: {
    type: Boolean,
    default: false
  },
  searchPlaceholder: {
    type: String,
    default: ''
  },
  // Create button
  showCreate: {
    type: Boolean,
    default: false
  },
  createLabel: {
    type: String,
    default: ''
  },
  // Actions column
  showActions: {
    type: Boolean,
    default: true
  },
  actionsWidth: {
    type: String,
    default: '120px'
  },
  showView: {
    type: Boolean,
    default: false
  },
  showEdit: {
    type: Boolean,
    default: true
  },
  showDelete: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'create',
  'view',
  'edit',
  'delete',
  'page',
  'sort',
  'search',
  'row-click'
])

const { t } = useI18n()

const searchQuery = ref('')

const actionsLabel = computed(() => t('common.actions'))
const viewTooltip = computed(() => t('common.details'))
const editTooltip = computed(() => t('common.edit'))
const deleteTooltip = computed(() => t('common.delete'))

const computedEmptyMessage = computed(() => props.emptyMessage || t('common.noData'))
const computedSearchPlaceholder = computed(() => props.searchPlaceholder || t('common.search'))
const computedCreateLabel = computed(() => props.createLabel || t('common.create'))

function handleSearch() {
  emit('search', searchQuery.value)
}

function handlePage(event) {
  emit('page', event)
}

function handleSort(event) {
  emit('sort', event)
}

function handleRowClick(event) {
  emit('row-click', event.data)
}
</script>

<style scoped>
.data-table-wrapper :deep(.custom-datatable) {
  border-radius: 8px;
  overflow: hidden;
}
</style>
