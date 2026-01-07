<template>
  <SlideOver
    v-model="visible"
    :title="equipment?.name || ''"
    :subtitle="equipment?.serial_number || equipment?.asset_tag || ''"
    icon="pi-box"
    size="lg"
  >
    <div v-if="loading" class="flex justify-center py-12">
      <i class="pi pi-spinner pi-spin text-3xl"></i>
    </div>

    <div v-else-if="equipment" class="space-y-6">
      <!-- Quick Stats -->
      <div class="grid grid-cols-3 gap-4">
        <div class="stat-card p-4 rounded-lg" style="background-color: var(--bg-app);">
          <div class="text-sm opacity-60 mb-1">{{ t('ipam.status') }}</div>
          <Tag :value="getStatusLabel(equipment.status)" :severity="getStatusSeverity(equipment.status)" />
        </div>
        <div class="stat-card p-4 rounded-lg" style="background-color: var(--bg-app);">
          <div class="text-sm opacity-60 mb-1">{{ t('inventory.type') }}</div>
          <div class="font-medium flex items-center gap-2">
            <i v-if="equipment.model?.equipment_type?.icon" :class="['pi', equipment.model.equipment_type.icon]"></i>
            {{ equipment.model?.equipment_type?.name || '-' }}
          </div>
        </div>
        <div class="stat-card p-4 rounded-lg" style="background-color: var(--bg-app);">
          <div class="text-sm opacity-60 mb-1">{{ t('inventory.warrantyExpiry') }}</div>
          <ExpiryBadge v-if="equipment.warranty_expiry" :date="equipment.warranty_expiry" compact />
          <span v-else class="opacity-50">-</span>
        </div>
      </div>

      <!-- Model & Manufacturer -->
      <section class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-th-large"></i>
          {{ t('inventory.model') }}
        </h4>
        <div class="section-content grid grid-cols-2 gap-4">
          <div>
            <div class="label">{{ t('inventory.manufacturer') }}</div>
            <div class="value">{{ equipment.model?.manufacturer?.name || '-' }}</div>
          </div>
          <div>
            <div class="label">{{ t('inventory.model') }}</div>
            <div class="value">{{ equipment.model?.name || '-' }}</div>
          </div>
        </div>
      </section>

      <!-- Location -->
      <section class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-map-marker"></i>
          {{ t('inventory.location') }}
        </h4>
        <div class="section-content">
          <div v-if="equipment.location" class="flex items-center gap-2">
            <span>{{ equipment.location.site }}</span>
            <i v-if="equipment.location.building" class="pi pi-chevron-right text-xs opacity-50"></i>
            <span v-if="equipment.location.building">{{ equipment.location.building }}</span>
            <i v-if="equipment.location.room" class="pi pi-chevron-right text-xs opacity-50"></i>
            <span v-if="equipment.location.room">{{ equipment.location.room }}</span>
          </div>
          <span v-else class="opacity-50">-</span>
        </div>
      </section>

      <!-- DCIM - Rack Position -->
      <section v-if="equipment.rack_id" class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-server"></i>
          {{ t('dcim.rackPlacement') }}
        </h4>
        <div class="section-content">
          <div class="flex items-center gap-4">
            <div>
              <div class="label">{{ t('dcim.racks') }}</div>
              <router-link
                :to="`/dcim?rack=${equipment.rack_id}`"
                class="value text-blue-500 hover:underline cursor-pointer"
              >
                {{ equipment.rack?.name || `Rack #${equipment.rack_id}` }}
              </router-link>
            </div>
            <div>
              <div class="label">{{ t('dcim.positionU') }}</div>
              <div class="value">U{{ equipment.position_u }}</div>
            </div>
            <div>
              <div class="label">{{ t('dcim.heightU') }}</div>
              <div class="value">{{ equipment.height_u }}U</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Linked Contracts -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-file"></i>
            {{ t('contracts.linkedContracts') }}
          </span>
          <span class="text-sm font-normal opacity-60">{{ linkedContracts.length }}</span>
        </h4>
        <div class="section-content">
          <div v-if="linkedContracts.length" class="space-y-2">
            <div
              v-for="contract in linkedContracts"
              :key="contract.id"
              class="linked-item p-3 rounded-lg flex items-center justify-between cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              style="background-color: var(--bg-app);"
              @click="navigateTo('contract', contract.id)"
            >
              <div class="flex items-center gap-3">
                <Tag :value="contract.contract_type" :severity="getContractTypeSeverity(contract.contract_type)" />
                <div>
                  <div class="font-medium">{{ contract.name }}</div>
                  <div class="text-sm opacity-60">{{ contract.contract_number }}</div>
                </div>
              </div>
              <ExpiryBadge :date="contract.end_date" compact />
            </div>
          </div>
          <div v-else class="text-sm opacity-50">{{ t('contracts.noLinkedContracts') }}</div>
        </div>
      </section>

      <!-- Open Tickets -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-ticket"></i>
            {{ t('tickets.openTickets') }}
          </span>
          <span class="text-sm font-normal opacity-60">{{ openTickets.length }}</span>
        </h4>
        <div class="section-content">
          <div v-if="openTickets.length" class="space-y-2">
            <div
              v-for="ticket in openTickets"
              :key="ticket.id"
              class="linked-item p-3 rounded-lg flex items-center justify-between cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              style="background-color: var(--bg-app);"
              @click="navigateTo('ticket', ticket.id)"
            >
              <div class="flex items-center gap-3">
                <Tag :value="ticket.status" :severity="getTicketStatusSeverity(ticket.status)" />
                <div>
                  <div class="font-medium">{{ ticket.title }}</div>
                  <div class="text-sm opacity-60">{{ ticket.ticket_number }}</div>
                </div>
              </div>
              <Tag :value="ticket.priority" :severity="getPrioritySeverity(ticket.priority)" />
            </div>
          </div>
          <div v-else class="text-sm opacity-50">{{ t('tickets.noOpenTickets') }}</div>
        </div>
      </section>

      <!-- IP Addresses -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-sitemap"></i>
            {{ t('ip.linkedIps') }}
          </span>
          <span class="text-sm font-normal opacity-60">{{ equipment.ip_addresses?.length || 0 }}</span>
        </h4>
        <div class="section-content">
          <div v-if="equipment.ip_addresses?.length" class="space-y-2">
            <div
              v-for="ip in equipment.ip_addresses"
              :key="ip.id"
              class="linked-item p-3 rounded-lg flex items-center justify-between"
              style="background-color: var(--bg-app);"
            >
              <div class="flex items-center gap-3">
                <span class="font-mono text-sm">{{ ip.address }}</span>
                <span v-if="ip.hostname" class="text-sm opacity-60">({{ ip.hostname }})</span>
              </div>
              <Tag :value="ip.status" :severity="getIpStatusSeverity(ip.status)" />
            </div>
          </div>
          <div v-else class="text-sm opacity-50">{{ t('ip.noIpLinked') }}</div>
        </div>
      </section>

      <!-- Notes -->
      <section v-if="equipment.notes" class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-comment"></i>
          {{ t('inventory.notes') }}
        </h4>
        <div class="section-content">
          <p class="text-sm whitespace-pre-wrap opacity-80">{{ equipment.notes }}</p>
        </div>
      </section>
    </div>

    <template #footer>
      <div class="flex items-center gap-3">
        <Button
          :label="t('tickets.createTicket')"
          icon="pi pi-ticket"
          severity="secondary"
          outlined
          @click="createTicketForEquipment"
        />
        <Button
          :label="t('common.edit')"
          icon="pi pi-pencil"
          @click="$emit('edit', equipment)"
        />
      </div>
    </template>
  </SlideOver>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../../api'
import SlideOver from './SlideOver.vue'
import ExpiryBadge from './ExpiryBadge.vue'

const props = defineProps({
  modelValue: Boolean,
  equipmentId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'edit'])

const router = useRouter()
const { t } = useI18n()

// State
const equipment = ref(null)
const linkedContracts = ref([])
const openTickets = ref([])
const loading = ref(false)

// Computed
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Methods
const loadEquipmentDetails = async () => {
  if (!props.equipmentId) return

  loading.value = true
  try {
    // Load equipment details
    const eqResponse = await api.get(`/inventory/equipment/${props.equipmentId}`)
    equipment.value = eqResponse.data

    // Load linked contracts
    try {
      const contractsResponse = await api.get(`/inventory/equipment/${props.equipmentId}/contracts`)
      linkedContracts.value = contractsResponse.data || []
    } catch {
      linkedContracts.value = []
    }

    // Load related tickets (searching by equipment name or ID)
    try {
      const ticketsResponse = await api.get('/tickets/', {
        params: {
          equipment_id: props.equipmentId,
          status: ['new', 'open', 'pending']
        }
      })
      openTickets.value = ticketsResponse.data?.items || ticketsResponse.data || []
    } catch {
      openTickets.value = []
    }
  } catch (error) {
    console.error('Failed to load equipment details:', error)
  } finally {
    loading.value = false
  }
}

const navigateTo = (type, id) => {
  visible.value = false
  switch (type) {
    case 'contract':
      router.push(`/contracts?id=${id}`)
      break
    case 'ticket':
      router.push(`/tickets?id=${id}`)
      break
  }
}

const createTicketForEquipment = () => {
  visible.value = false
  router.push({
    path: '/tickets',
    query: {
      action: 'create',
      equipment_id: equipment.value.id,
      equipment_name: equipment.value.name
    }
  })
}

// Severity helpers
const getStatusLabel = (status) => {
  const labels = {
    in_service: t('status.inService'),
    in_stock: t('status.inStock'),
    retired: t('status.retired'),
    maintenance: t('status.maintenance')
  }
  return labels[status] || status
}

const getStatusSeverity = (status) => {
  const severities = {
    in_service: 'success',
    in_stock: 'info',
    retired: 'secondary',
    maintenance: 'warning'
  }
  return severities[status] || null
}

const getContractTypeSeverity = (type) => {
  const severities = {
    maintenance: 'info',
    insurance: 'warning',
    leasing: 'success',
    support: 'secondary'
  }
  return severities[type] || null
}

const getTicketStatusSeverity = (status) => {
  const severities = {
    new: 'info',
    open: 'warning',
    pending: 'secondary',
    resolved: 'success',
    closed: 'secondary'
  }
  return severities[status] || null
}

const getPrioritySeverity = (priority) => {
  const severities = {
    critical: 'danger',
    high: 'warning',
    medium: 'info',
    low: 'secondary'
  }
  return severities[priority] || null
}

const getIpStatusSeverity = (status) => {
  const severities = {
    active: 'success',
    reserved: 'warning',
    available: 'info'
  }
  return severities[status] || null
}

// Watch for changes
watch(() => [props.modelValue, props.equipmentId], ([isVisible, id]) => {
  if (isVisible && id) {
    loadEquipmentDetails()
  }
}, { immediate: true })
</script>

<style scoped>
.detail-section {
  border-bottom: 1px solid var(--border-color);
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
  color: var(--primary-color, #0ea5e9);
}

.section-content .label {
  font-size: 0.75rem;
  opacity: 0.6;
  margin-bottom: 0.25rem;
}

.section-content .value {
  font-weight: 500;
}

.stat-card {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.stat-card:hover {
  transform: translateY(-1px);
}

.linked-item {
  transition: all 0.15s ease;
}

.linked-item:hover {
  transform: translateX(4px);
}
</style>
