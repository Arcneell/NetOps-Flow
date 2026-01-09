<template>
  <SlideOver
    v-model="visible"
    :title="subnet?.cidr || ''"
    :subtitle="subnet?.name || ''"
    icon="pi-sitemap"
    size="xl"
  >
    <div v-if="loading" class="flex justify-center py-12">
      <i class="pi pi-spinner pi-spin text-3xl"></i>
    </div>

    <div v-else-if="subnet" class="space-y-6">
      <!-- Quick Stats -->
      <div class="grid grid-cols-3 gap-4">
        <div class="stat-card p-4 rounded-lg">
          <div class="text-sm mb-1">{{ t('ipam.totalIps') }}</div>
          <div class="text-2xl font-bold text-blue-500">{{ ipData.total }}</div>
        </div>
        <div class="stat-card p-4 rounded-lg">
          <div class="text-sm mb-1">{{ t('ipam.activeIps') }}</div>
          <div class="text-2xl font-bold text-green-500">{{ activeCount }}</div>
        </div>
        <div class="stat-card p-4 rounded-lg">
          <div class="text-sm mb-1">{{ t('ipam.reservedIps') }}</div>
          <div class="text-2xl font-bold text-orange-500">{{ reservedCount }}</div>
        </div>
      </div>

      <!-- Subnet Info -->
      <section class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-info-circle"></i>
          {{ t('common.details') }}
        </h4>
        <div class="section-content">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="label">{{ t('ipam.cidr') }}</div>
              <div class="value font-mono">{{ subnet.cidr }}</div>
            </div>
            <div>
              <div class="label">{{ t('common.name') }}</div>
              <div class="value">{{ subnet.name || '-' }}</div>
            </div>
          </div>
          <div v-if="subnet.description" class="mt-4">
            <div class="label">{{ t('ipam.description') }}</div>
            <div class="value text-sm">{{ subnet.description }}</div>
          </div>
        </div>
      </section>

      <!-- IP Addresses -->
      <section class="detail-section flex-1">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-list"></i>
            {{ t('ipam.allocatedIps') }}
          </span>
          <div class="flex items-center gap-2">
            <span class="text-sm font-normal opacity-60">
              {{ ipData.total }} {{ t('ipam.addressesFound') }}
            </span>
            <Button
              icon="pi pi-plus"
              size="small"
              @click="showAddIpDialog = true"
              v-tooltip.left="t('ipam.addIp')"
              class="!bg-blue-500 !text-white hover:!bg-blue-600"
            />
          </div>
        </h4>
        <div class="section-content">
          <!-- Filter -->
          <div class="flex gap-2 mb-4">
            <Dropdown
              v-model="statusFilter"
              :options="statusFilterOptions"
              optionLabel="label"
              optionValue="value"
              :placeholder="t('filters.allStatuses')"
              showClear
              class="w-40"
            />
            <InputText
              v-model="searchQuery"
              :placeholder="t('search.searchIps')"
              class="flex-1"
            />
          </div>

          <!-- Bulk Selection Bar -->
          <div v-if="selectedIps.length > 0" class="flex items-center gap-3 mb-4 p-3 rounded-lg" style="background-color: var(--bg-secondary);">
            <div class="flex items-center gap-2">
              <i class="pi pi-check-square text-sky-500"></i>
              <span class="font-medium text-sm">{{ selectedIps.length }} {{ t('common.selected') }}</span>
            </div>
            <div class="flex-1"></div>
            <Button :label="t('bulk.openBulkActions')" icon="pi pi-list-check" size="small" @click="showBulkDialog = true" />
            <Button icon="pi pi-times" text rounded size="small" @click="selectedIps = []" v-tooltip.top="t('common.clearSelection')" />
          </div>

          <!-- IP List -->
          <div v-if="loadingIps" class="flex justify-center py-8">
            <i class="pi pi-spinner pi-spin text-2xl opacity-50"></i>
          </div>

          <div v-else-if="ipData.items.length" class="ip-list-container">
            <div
              v-for="ip in filteredIps"
              :key="ip.id"
              class="ip-item p-3 rounded-lg flex items-center justify-between"
              :class="{ 'ring-2 ring-blue-500': isIpSelected(ip) }"
            >
              <div class="flex items-center gap-4 flex-1 min-w-0">
                <Checkbox :modelValue="isIpSelected(ip)" @update:modelValue="toggleIpSelection(ip)" :binary="true" />
                <span class="font-mono text-sm font-medium ip-address">{{ ip.address }}</span>
                <span v-if="ip.hostname" class="text-sm opacity-60 truncate">{{ ip.hostname }}</span>
                <div v-if="ip.equipment" class="flex items-center gap-2 text-sm">
                  <i class="pi pi-box text-blue-500"></i>
                  <span
                    class="font-medium text-blue-500 hover:underline cursor-pointer"
                    @click="navigateToEquipment(ip.equipment)"
                  >
                    {{ ip.equipment.name }}
                  </span>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span v-if="ip.mac_address" class="font-mono text-xs opacity-50">{{ ip.mac_address }}</span>
                <Tag :value="ip.status" :severity="getStatusSeverity(ip.status)" />
                <Button
                  icon="pi pi-trash"
                  text
                  rounded
                  size="small"
                  severity="danger"
                  @click="confirmDeleteIp(ip)"
                  v-tooltip.left="t('common.delete')"
                />
              </div>
            </div>

            <!-- Pagination -->
            <div v-if="ipData.total > pageSize" class="flex justify-center mt-4">
              <Paginator
                :rows="pageSize"
                :totalRecords="ipData.total"
                :first="currentPage * pageSize"
                @page="onPageChange"
                template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink"
              />
            </div>
          </div>

          <div v-else class="text-sm text-muted text-center py-8">
            <i class="pi pi-inbox text-4xl mb-2 opacity-30"></i>
            <p>{{ t('ipam.noIps') }}</p>
          </div>
        </div>
      </section>
    </div>

    <template #footer>
      <div class="flex items-center gap-3">
        <Button
          :label="t('ipam.scanSubnet')"
          icon="pi pi-search"
          severity="secondary"
          outlined
          @click="scanSubnet"
        />
        <Button
          :label="t('ipam.addIp')"
          icon="pi pi-plus"
          @click="showAddIpDialog = true"
        />
      </div>
    </template>
  </SlideOver>

  <!-- Add IP Dialog -->
  <Dialog v-model:visible="showAddIpDialog" modal :header="t('ipam.manualIpAllocation')" :style="{ width: '400px' }" @keydown.enter="onIpDialogEnter">
    <div class="flex flex-col gap-4 mt-2">
      <div class="flex flex-col gap-2">
        <label for="ipaddr" class="text-sm font-medium">{{ t('ipam.ipAddress') }} <span class="text-red-500">*</span></label>
        <InputText id="ipaddr" v-model="newIp.address" :placeholder="getIpPlaceholder()" />
      </div>
      <div class="flex flex-col gap-2">
        <label for="hostname" class="text-sm font-medium">{{ t('ipam.hostname') }}</label>
        <InputText id="hostname" v-model="newIp.hostname" />
      </div>
      <div class="flex flex-col gap-2">
        <label for="mac" class="text-sm font-medium">{{ t('ipam.mac') }}</label>
        <InputText id="mac" v-model="newIp.mac_address" placeholder="00:00:00:00:00:00" />
      </div>
      <div class="flex flex-col gap-2">
        <label for="status" class="text-sm font-medium">{{ t('ipam.status') }}</label>
        <Dropdown id="status" v-model="newIp.status" :options="['available', 'active', 'reserved']" class="w-full" />
      </div>
    </div>
    <template #footer>
      <div class="flex justify-end gap-3">
        <Button :label="t('common.cancel')" severity="secondary" outlined @click="showAddIpDialog = false" />
        <Button :label="t('common.add')" icon="pi pi-check" @click="createIp" />
      </div>
    </template>
  </Dialog>

  <!-- Delete IP Confirmation -->
  <Dialog v-model:visible="showDeleteIpDialog" modal :header="t('common.confirmDelete')" :style="{ width: '400px' }">
    <div class="flex items-start gap-4">
      <i class="pi pi-exclamation-triangle text-orange-500 text-3xl"></i>
      <div>
        <p class="mb-2">{{ t('ipam.confirmDeleteIp') }}</p>
        <p class="font-mono font-bold">{{ deletingIp?.address }}</p>
      </div>
    </div>
    <template #footer>
      <div class="flex justify-end gap-3">
        <Button :label="t('common.cancel')" severity="secondary" outlined @click="showDeleteIpDialog = false" />
        <Button :label="t('common.delete')" icon="pi pi-trash" severity="danger" @click="deleteIp" />
      </div>
    </template>
  </Dialog>

  <!-- Bulk Actions Dialog -->
  <Dialog v-model:visible="showBulkDialog" modal :header="t('bulk.title')" :style="{ width: '450px' }">
    <div class="space-y-4">
      <!-- Selection Summary -->
      <div class="p-4 rounded-xl" style="background: var(--bg-secondary); border: 1px solid var(--border-default);">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background: linear-gradient(135deg, rgba(14, 165, 233, 0.2) 0%, rgba(14, 165, 233, 0.1) 100%);">
            <i class="pi pi-check-square text-sky-500 text-lg"></i>
          </div>
          <div>
            <div class="text-2xl font-bold">{{ selectedIps.length }}</div>
            <div class="text-sm opacity-60">{{ t('bulk.elementsSelected') }}</div>
          </div>
        </div>
      </div>

      <!-- Change Status Action -->
      <div class="action-card p-4 rounded-xl cursor-pointer" @click="showBulkStatusAction = !showBulkStatusAction">
        <div class="flex items-center gap-4">
          <div class="action-icon">
            <i class="pi pi-sync"></i>
          </div>
          <div class="flex-1">
            <div class="font-semibold">{{ t('bulk.changeStatus') }}</div>
            <div class="text-sm opacity-60">{{ t('bulk.changeStatusDesc') }}</div>
          </div>
          <i :class="['pi transition-transform', showBulkStatusAction ? 'pi-chevron-up' : 'pi-chevron-down']"></i>
        </div>
        <div v-if="showBulkStatusAction" class="mt-4 pt-4 border-t" style="border-color: var(--border-default);" @click.stop>
          <Dropdown v-model="bulkStatus" :options="bulkStatusOptions" optionLabel="label" optionValue="value"
                    :placeholder="t('ipam.changeStatus')" class="w-full mb-3" />
          <Button :label="t('bulk.applyToAll', { count: selectedIps.length })" icon="pi pi-check"
                  class="w-full" @click="applyBulkStatus" :disabled="!bulkStatus" :loading="bulkLoading" />
        </div>
      </div>

      <!-- Release Action -->
      <div class="action-card p-4 rounded-xl cursor-pointer" @click="applyBulkRelease">
        <div class="flex items-center gap-4">
          <div class="action-icon" style="background: linear-gradient(135deg, rgba(234, 179, 8, 0.2) 0%, rgba(234, 179, 8, 0.1) 100%);">
            <i class="pi pi-undo text-yellow-500"></i>
          </div>
          <div class="flex-1">
            <div class="font-semibold">{{ t('bulk.releaseItems') }}</div>
            <div class="text-sm opacity-60">{{ t('bulk.releaseItemsDesc') }}</div>
          </div>
          <i class="pi pi-chevron-right"></i>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-between items-center">
        <Button :label="t('common.clearSelection')" text size="small" @click="selectedIps = []; showBulkDialog = false" />
        <Button :label="t('common.close')" severity="secondary" outlined @click="showBulkDialog = false" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import api from '../../api'
import SlideOver from './SlideOver.vue'

const props = defineProps({
  modelValue: Boolean,
  subnetId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'refresh'])

const router = useRouter()
const toast = useToast()
const { t } = useI18n()

// State
const subnet = ref(null)
const ipData = ref({ items: [], total: 0, skip: 0, limit: 50 })
const loading = ref(false)
const loadingIps = ref(false)
const showAddIpDialog = ref(false)
const showDeleteIpDialog = ref(false)
const deletingIp = ref(null)
const newIp = ref({ address: '', hostname: '', mac_address: '', status: 'active' })

// Pagination and filtering
const pageSize = ref(50)
const currentPage = ref(0)
const statusFilter = ref(null)
const searchQuery = ref('')

// Bulk operations
const selectedIps = ref([])
const bulkStatus = ref(null)
const bulkLoading = ref(false)
const showBulkDialog = ref(false)
const showBulkStatusAction = ref(false)

const bulkStatusOptions = computed(() => [
  { label: t('status.available'), value: 'available' },
  { label: t('status.reserved'), value: 'reserved' },
  { label: t('status.assigned'), value: 'assigned' },
  { label: t('status.dhcp'), value: 'dhcp' }
])

const isIpSelected = (ip) => selectedIps.value.some(s => s.id === ip.id)

const toggleIpSelection = (ip) => {
  const index = selectedIps.value.findIndex(s => s.id === ip.id)
  if (index === -1) {
    selectedIps.value.push(ip)
  } else {
    selectedIps.value.splice(index, 1)
  }
}

// Computed
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const statusFilterOptions = computed(() => [
  { label: t('status.active'), value: 'active' },
  { label: t('status.reserved'), value: 'reserved' },
  { label: t('status.available'), value: 'available' }
])

const activeCount = computed(() => {
  return ipData.value.items.filter(ip => ip.status === 'active').length
})

const reservedCount = computed(() => {
  return ipData.value.items.filter(ip => ip.status === 'reserved').length
})

const filteredIps = computed(() => {
  let result = ipData.value.items

  if (statusFilter.value) {
    result = result.filter(ip => ip.status === statusFilter.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(ip =>
      ip.address.toLowerCase().includes(query) ||
      (ip.hostname && ip.hostname.toLowerCase().includes(query)) ||
      (ip.mac_address && ip.mac_address.toLowerCase().includes(query)) ||
      (ip.equipment?.name && ip.equipment.name.toLowerCase().includes(query))
    )
  }

  return result
})

// Methods
const loadSubnetDetails = async () => {
  if (!props.subnetId) return

  loading.value = true
  try {
    // Load all subnets and find the one we need
    const response = await api.get('/subnets/')
    subnet.value = response.data.find(s => s.id === props.subnetId)

    // Load IPs
    await loadIps()
  } catch (error) {
    console.error('Failed to load subnet details:', error)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('ipam.failedLoadSubnet'), life: 3000 })
  } finally {
    loading.value = false
  }
}

const loadIps = async () => {
  if (!props.subnetId) return

  loadingIps.value = true
  try {
    const response = await api.get(`/subnets/${props.subnetId}/ips/`, {
      params: {
        skip: currentPage.value * pageSize.value,
        limit: pageSize.value
      }
    })
    ipData.value = {
      items: response.data.items || [],
      total: response.data.total || 0,
      skip: response.data.skip || 0,
      limit: response.data.limit || pageSize.value
    }
  } catch (error) {
    console.error('Failed to load IPs:', error)
    ipData.value = { items: [], total: 0, skip: 0, limit: pageSize.value }
  } finally {
    loadingIps.value = false
  }
}

const onPageChange = (event) => {
  currentPage.value = event.page
  loadIps()
}

const getIpPlaceholder = () => {
  if (!subnet.value?.cidr) return '192.168.1.1'
  // Extract network part from CIDR
  const cidr = subnet.value.cidr
  const parts = cidr.split('/')
  if (parts.length > 0) {
    const network = parts[0].split('.')
    if (network.length === 4) {
      return `${network[0]}.${network[1]}.${network[2]}.x`
    }
  }
  return '192.168.1.1'
}

const createIp = async () => {
  if (!newIp.value.address) {
    toast.add({ severity: 'warn', summary: t('common.error'), detail: t('validation.fillRequiredFields'), life: 3000 })
    return
  }
  try {
    await api.post(`/subnets/${props.subnetId}/ips/`, newIp.value)
    showAddIpDialog.value = false
    newIp.value = { address: '', hostname: '', mac_address: '', status: 'active' }
    await loadIps()
    emit('refresh')
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('ipam.ipAllocated'), life: 3000 })
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: error.response?.data?.detail || t('ipam.failedAllocateIp'), life: 3000 })
  }
}

const confirmDeleteIp = (ip) => {
  deletingIp.value = ip
  showDeleteIpDialog.value = true
}

const deleteIp = async () => {
  if (!deletingIp.value) return
  try {
    await api.delete(`/subnets/${props.subnetId}/ips/${deletingIp.value.id}`)
    showDeleteIpDialog.value = false
    await loadIps()
    emit('refresh')
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('ipam.ipDeleted'), life: 3000 })
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: error.response?.data?.detail || t('common.error'), life: 3000 })
  }
}

const scanSubnet = async () => {
  try {
    await api.post(`/subnets/${props.subnetId}/scan`)
    toast.add({ severity: 'info', summary: t('ipam.scanStarted'), detail: `${t('ipam.scanningBackground')} ${subnet.value?.cidr}`, life: 5000 })
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('ipam.failedStartScan'), life: 3000 })
  }
}

const navigateToEquipment = (equipment) => {
  visible.value = false
  router.push(`/inventory?equipment=${equipment.id}`)
}

const getStatusSeverity = (status) => {
  switch (status) {
    case 'active': return 'success'
    case 'reserved': return 'warning'
    case 'available': return 'info'
    default: return null
  }
}

const onIpDialogEnter = (event) => {
  if (event.target.tagName !== 'TEXTAREA') {
    event.preventDefault()
    createIp()
  }
}

// Bulk operations functions
const applyBulkStatus = async () => {
  if (!bulkStatus.value || selectedIps.value.length === 0) return
  bulkLoading.value = true
  try {
    const response = await api.post('/subnets/ips/bulk-status', {
      ip_ids: selectedIps.value.map(ip => ip.id),
      status: bulkStatus.value
    })
    const result = response.data
    if (result.success) {
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('ipam.bulkStatusSuccess', { count: result.processed }), life: 3000 })
    } else {
      toast.add({ severity: 'warn', summary: t('common.warning'), detail: t('ipam.bulkStatusPartial', { processed: result.processed, failed: result.failed }), life: 3000 })
    }
    selectedIps.value = []
    bulkStatus.value = null
    showBulkDialog.value = false
    showBulkStatusAction.value = false
    await loadIps()
    emit('refresh')
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: error.response?.data?.detail || t('common.error'), life: 3000 })
  } finally {
    bulkLoading.value = false
  }
}

const applyBulkRelease = async () => {
  if (selectedIps.value.length === 0) return
  bulkLoading.value = true
  try {
    const response = await api.post('/subnets/ips/bulk-release', {
      ip_ids: selectedIps.value.map(ip => ip.id)
    })
    const result = response.data
    if (result.success) {
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('ipam.bulkReleaseSuccess', { count: result.processed }), life: 3000 })
    } else {
      toast.add({ severity: 'warn', summary: t('common.warning'), detail: t('ipam.bulkReleasePartial', { processed: result.processed, failed: result.failed }), life: 3000 })
    }
    selectedIps.value = []
    showBulkDialog.value = false
    await loadIps()
    emit('refresh')
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: error.response?.data?.detail || t('common.error'), life: 3000 })
  } finally {
    bulkLoading.value = false
  }
}

// Watch for changes
watch(() => [props.modelValue, props.subnetId], ([isVisible, id]) => {
  if (isVisible && id) {
    currentPage.value = 0
    statusFilter.value = null
    searchQuery.value = ''
    selectedIps.value = []
    bulkStatus.value = null
    showBulkDialog.value = false
    showBulkStatusAction.value = false
    loadSubnetDetails()
  }
}, { immediate: true })
</script>

<style scoped>
.detail-section {
  border-bottom: 1px solid var(--border-default);
  padding-bottom: 1.5rem;
}

.detail-section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
  color: var(--primary);
}

.section-content .label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.section-content .value {
  font-weight: 500;
  color: var(--text-primary);
}

.stat-card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-default);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.stat-card:hover {
  transform: translateY(-1px);
  border-color: var(--border-strong);
}

.stat-card .text-sm {
  color: var(--text-secondary);
}

.ip-list-container {
  max-height: 400px;
  overflow-y: auto;
}

.ip-item {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-default);
  margin-bottom: 0.5rem;
  transition: all 0.15s ease;
}

.ip-item:hover {
  background-color: var(--bg-hover);
  border-color: var(--border-strong);
}

.ip-item:last-child {
  margin-bottom: 0;
}

.ip-address {
  color: var(--text-primary);
  min-width: 120px;
}

.text-muted {
  color: var(--text-muted);
}

.action-card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-default);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.action-card:hover {
  border-color: var(--border-strong);
  background-color: var(--bg-hover);
}

.action-card.danger:hover {
  border-color: rgb(239 68 68 / 0.5);
  background-color: rgb(239 68 68 / 0.1);
}

.action-card.danger:hover .action-icon {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.3) 0%, rgba(239, 68, 68, 0.2) 100%);
}

.action-icon {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.2) 0%, rgba(14, 165, 233, 0.1) 100%);
  transition: all 0.2s ease;
}
</style>
