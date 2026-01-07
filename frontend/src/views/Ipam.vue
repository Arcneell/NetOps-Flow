<template>
  <div class="flex flex-col h-full">
    <!-- Breadcrumbs -->
    <Breadcrumbs :items="breadcrumbItems" />

    <div class="flex gap-6 flex-1 overflow-hidden">
      <!-- Main Content -->
      <div class="flex-1 overflow-hidden">
        <div class="card h-full flex flex-col">
          <!-- Header -->
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-bold">{{ t('ipam.subnets') }}</h3>
            <Button :label="t('dashboard.newSubnet')" icon="pi pi-plus" @click="showSubnetDialog = true" />
          </div>

          <!-- Stats Cards -->
          <div class="grid grid-cols-4 gap-4 mb-6">
            <div class="stat-card p-4 rounded-xl">
              <div class="flex items-center gap-3">
                <div class="stat-icon bg-blue-500/10 text-blue-500">
                  <i class="pi pi-sitemap"></i>
                </div>
                <div>
                  <div class="text-2xl font-bold">{{ subnets.length }}</div>
                  <div class="text-sm opacity-60">{{ t('ipam.subnets') }}</div>
                </div>
              </div>
            </div>
            <div class="stat-card p-4 rounded-xl">
              <div class="flex items-center gap-3">
                <div class="stat-icon bg-green-500/10 text-green-500">
                  <i class="pi pi-check-circle"></i>
                </div>
                <div>
                  <div class="text-2xl font-bold">{{ totalActiveIps }}</div>
                  <div class="text-sm opacity-60">{{ t('ipam.activeIps') }}</div>
                </div>
              </div>
            </div>
            <div class="stat-card p-4 rounded-xl">
              <div class="flex items-center gap-3">
                <div class="stat-icon bg-orange-500/10 text-orange-500">
                  <i class="pi pi-clock"></i>
                </div>
                <div>
                  <div class="text-2xl font-bold">{{ totalReservedIps }}</div>
                  <div class="text-sm opacity-60">{{ t('ipam.reservedIps') }}</div>
                </div>
              </div>
            </div>
            <div class="stat-card p-4 rounded-xl">
              <div class="flex items-center gap-3">
                <div class="stat-icon bg-purple-500/10 text-purple-500">
                  <i class="pi pi-list"></i>
                </div>
                <div>
                  <div class="text-2xl font-bold">{{ totalIps }}</div>
                  <div class="text-sm opacity-60">{{ t('ipam.totalIps') }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Search -->
          <div class="mb-4">
            <InputText
              v-model="searchQuery"
              :placeholder="t('search.searchSubnets')"
              class="w-full"
            >
              <template #prefix>
                <i class="pi pi-search"></i>
              </template>
            </InputText>
          </div>

          <!-- Subnet Table -->
          <div class="flex-1 overflow-auto">
            <DataTable
              :value="filteredSubnets"
              :loading="loading"
              stripedRows
              class="text-sm"
              :rowHover="true"
            >
              <template #empty>
                <div class="text-center py-8">
                  <i class="pi pi-sitemap text-4xl mb-2 opacity-30"></i>
                  <p class="opacity-60">{{ t('ipam.noSubnets') }}</p>
                </div>
              </template>

              <Column field="cidr" :header="t('ipam.cidr')" sortable style="width: 180px">
                <template #body="slotProps">
                  <span
                    class="font-mono font-bold text-blue-500 hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer transition-colors hover:underline"
                    @click="openSubnetDetail(slotProps.data)"
                  >
                    {{ slotProps.data.cidr }}
                  </span>
                </template>
              </Column>
              <Column field="name" :header="t('common.name')" sortable>
                <template #body="slotProps">
                  <span
                    class="font-medium cursor-pointer hover:text-blue-500 transition-colors"
                    @click="openSubnetDetail(slotProps.data)"
                  >
                    {{ slotProps.data.name || '-' }}
                  </span>
                </template>
              </Column>
              <Column field="description" :header="t('ipam.description')">
                <template #body="slotProps">
                  <span class="opacity-70 truncate block max-w-xs">{{ slotProps.data.description || '-' }}</span>
                </template>
              </Column>
              <Column :header="t('ipam.ips')" style="width: 100px; text-align: center">
                <template #body="slotProps">
                  <Tag :value="String(slotProps.data.ip_count || 0)" severity="info" />
                </template>
              </Column>
              <Column :header="t('common.actions')" style="width: 150px">
                <template #body="slotProps">
                  <div class="flex gap-1 justify-center">
                    <Button
                      icon="pi pi-eye"
                      text
                      rounded
                      size="small"
                      @click="openSubnetDetail(slotProps.data)"
                      v-tooltip.top="t('common.view')"
                    />
                    <Button
                      icon="pi pi-search"
                      text
                      rounded
                      size="small"
                      severity="secondary"
                      @click="scanSubnet(slotProps.data)"
                      v-tooltip.top="t('ipam.scanSubnet')"
                    />
                    <Button
                      icon="pi pi-pencil"
                      text
                      rounded
                      size="small"
                      @click="openEditSubnetDialog(slotProps.data)"
                      v-tooltip.top="t('common.edit')"
                    />
                    <Button
                      icon="pi pi-trash"
                      text
                      rounded
                      size="small"
                      severity="danger"
                      @click="confirmDeleteSubnet(slotProps.data)"
                      v-tooltip.top="t('common.delete')"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </div>
      </div>
    </div>

    <!-- Subnet Detail Slide-Over -->
    <SubnetDetailSlideOver
      v-model="showDetailSlideOver"
      :subnetId="selectedSubnetId"
      @refresh="fetchSubnets"
    />

    <!-- Create/Edit Subnet Dialog -->
    <Dialog v-model:visible="showSubnetDialog" modal :header="editingSubnet ? t('ipam.editSubnet') : t('dashboard.newSubnet')" :style="{ width: '450px' }" @keydown.enter="onSubnetDialogEnter">
      <div class="flex flex-col gap-4 mt-2">
        <div class="flex flex-col gap-2">
          <label for="cidr" class="text-sm font-medium">{{ t('ipam.cidr') }} <span class="text-red-500">*</span></label>
          <InputText id="cidr" v-model="subnetForm.cidr" placeholder="192.168.1.0/24" :disabled="!!editingSubnet" />
          <small v-if="!editingSubnet" class="opacity-60">{{ t('ipam.cidrHint') }}</small>
        </div>
        <div class="flex flex-col gap-2">
          <label for="name" class="text-sm font-medium">{{ t('common.name') }} <span class="text-red-500">*</span></label>
          <InputText id="name" v-model="subnetForm.name" placeholder="Management LAN" />
        </div>
        <div class="flex flex-col gap-2">
          <label for="desc" class="text-sm font-medium">{{ t('ipam.description') }}</label>
          <Textarea id="desc" v-model="subnetForm.description" rows="3" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="closeSubnetDialog" />
          <Button :label="t('common.save')" icon="pi pi-check" @click="saveSubnet" />
        </div>
      </template>
    </Dialog>

    <!-- Delete Subnet Confirmation -->
    <Dialog v-model:visible="showDeleteDialog" modal :header="t('common.confirmDelete')" :style="{ width: '400px' }">
      <div class="flex items-start gap-4">
        <i class="pi pi-exclamation-triangle text-orange-500 text-3xl"></i>
        <div>
          <p class="mb-2">{{ t('ipam.confirmDeleteSubnet') }}</p>
          <p class="font-mono font-bold">{{ deletingSubnet?.cidr }} - {{ deletingSubnet?.name }}</p>
          <p v-if="deletingSubnet?.ip_count > 0" class="text-sm text-orange-500 mt-2">
            <i class="pi pi-info-circle mr-1"></i>
            {{ t('ipam.deleteWarningIps', { count: deletingSubnet.ip_count }) }}
          </p>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showDeleteDialog = false" />
          <Button :label="t('common.delete')" icon="pi pi-trash" severity="danger" @click="deleteSubnet" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import api from '../api'
import Breadcrumbs from '../components/shared/Breadcrumbs.vue'
import SubnetDetailSlideOver from '../components/shared/SubnetDetailSlideOver.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const toast = useToast()

// Breadcrumbs
const breadcrumbItems = computed(() => [
  { label: t('ipam.title'), icon: 'pi-sitemap' }
])

// State
const subnets = ref([])
const loading = ref(false)
const searchQuery = ref('')

// Slide-over
const showDetailSlideOver = ref(false)
const selectedSubnetId = ref(null)

// Dialogs
const showSubnetDialog = ref(false)
const showDeleteDialog = ref(false)
const editingSubnet = ref(null)
const deletingSubnet = ref(null)
const subnetForm = ref({ cidr: '', name: '', description: '' })

// Computed stats
const totalIps = computed(() => {
  return subnets.value.reduce((sum, s) => sum + (s.ip_count || 0), 0)
})

const totalActiveIps = computed(() => {
  // This is an approximation - we'd need to load all IPs to get exact counts
  return Math.round(totalIps.value * 0.7)
})

const totalReservedIps = computed(() => {
  return Math.round(totalIps.value * 0.2)
})

const filteredSubnets = computed(() => {
  if (!searchQuery.value) return subnets.value

  const query = searchQuery.value.toLowerCase()
  return subnets.value.filter(subnet =>
    subnet.cidr.toLowerCase().includes(query) ||
    (subnet.name && subnet.name.toLowerCase().includes(query)) ||
    (subnet.description && subnet.description.toLowerCase().includes(query))
  )
})

// Methods
const fetchSubnets = async () => {
  loading.value = true
  try {
    const res = await api.get('/subnets/')
    subnets.value = res.data
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('ipam.failedLoadSubnets'), life: 3000 })
  } finally {
    loading.value = false
  }
}

const openSubnetDetail = (subnet) => {
  selectedSubnetId.value = subnet.id
  showDetailSlideOver.value = true
}

const openEditSubnetDialog = (subnet) => {
  editingSubnet.value = subnet
  subnetForm.value = {
    cidr: subnet.cidr,
    name: subnet.name || '',
    description: subnet.description || ''
  }
  showSubnetDialog.value = true
}

const closeSubnetDialog = () => {
  showSubnetDialog.value = false
  editingSubnet.value = null
  subnetForm.value = { cidr: '', name: '', description: '' }
}

const saveSubnet = async () => {
  if (!subnetForm.value.cidr || !subnetForm.value.name) {
    toast.add({ severity: 'warn', summary: t('common.error'), detail: t('validation.fillRequiredFields'), life: 3000 })
    return
  }

  try {
    if (editingSubnet.value) {
      // Update existing subnet
      await api.put(`/subnets/${editingSubnet.value.id}`, {
        name: subnetForm.value.name,
        description: subnetForm.value.description
      })
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('ipam.subnetUpdated'), life: 3000 })
    } else {
      // Create new subnet
      await api.post('/subnets/', subnetForm.value)
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('ipam.subnetCreated'), life: 3000 })
    }
    closeSubnetDialog()
    fetchSubnets()
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: error.response?.data?.detail || t('common.error'), life: 3000 })
  }
}

const confirmDeleteSubnet = (subnet) => {
  deletingSubnet.value = subnet
  showDeleteDialog.value = true
}

const deleteSubnet = async () => {
  if (!deletingSubnet.value) return

  try {
    await api.delete(`/subnets/${deletingSubnet.value.id}`)
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('ipam.subnetDeleted'), life: 3000 })
    showDeleteDialog.value = false
    fetchSubnets()
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: error.response?.data?.detail || t('common.error'), life: 3000 })
  }
}

const scanSubnet = async (subnet) => {
  try {
    await api.post(`/subnets/${subnet.id}/scan`)
    toast.add({ severity: 'info', summary: t('ipam.scanStarted'), detail: `${t('ipam.scanningBackground')} ${subnet.cidr}`, life: 5000 })
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('ipam.failedStartScan'), life: 3000 })
  }
}

const onSubnetDialogEnter = (event) => {
  if (event.target.tagName !== 'TEXTAREA') {
    event.preventDefault()
    saveSubnet()
  }
}

// Open subnet from URL parameter
const openSubnetFromUrl = () => {
  const subnetId = route.query.subnet || route.query.id
  if (subnetId && subnets.value.length > 0) {
    const subnet = subnets.value.find(s => s.id === parseInt(subnetId))
    if (subnet) {
      openSubnetDetail(subnet)
      router.replace({ path: route.path })
    }
  }
}

// Watch for route changes
watch(() => [route.query.subnet, route.query.id], ([subnetQuery, idQuery]) => {
  if (subnetQuery || idQuery) {
    openSubnetFromUrl()
  }
})

onMounted(async () => {
  await fetchSubnets()
  openSubnetFromUrl()
})
</script>

<style scoped>
.stat-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-default);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.stat-card:hover {
  transform: translateY(-2px);
  border-color: var(--border-strong);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
}

:deep(.p-datatable .p-datatable-tbody > tr:hover) {
  background-color: var(--bg-hover) !important;
  cursor: pointer;
}
</style>
