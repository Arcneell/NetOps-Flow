<template>
  <SlideOver
    v-model="visible"
    :title="contract?.name || ''"
    :subtitle="contract?.contract_number || ''"
    icon="pi-file-edit"
    size="lg"
  >
    <div v-if="loading" class="flex justify-center py-12">
      <i class="pi pi-spinner pi-spin text-3xl"></i>
    </div>

    <div v-else-if="contract" class="space-y-6">
      <!-- Quick Stats -->
      <div class="grid grid-cols-3 gap-4">
        <div class="stat-card p-4 rounded-lg">
          <div class="text-sm mb-1">{{ t('inventory.type') }}</div>
          <Tag :value="contract.contract_type" :severity="getTypeSeverity(contract.contract_type)" />
        </div>
        <div class="stat-card p-4 rounded-lg">
          <div class="text-sm mb-1">{{ t('ipam.status') }}</div>
          <Tag :value="getContractStatus(contract)" :severity="getStatusSeverity(contract)" />
        </div>
        <div class="stat-card p-4 rounded-lg">
          <div class="text-sm mb-1">{{ t('contracts.endDate') }}</div>
          <ExpiryBadge v-if="contract.end_date" :date="contract.end_date" compact />
          <span v-else class="text-muted">-</span>
        </div>
      </div>

      <!-- Contract Details -->
      <section class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-info-circle"></i>
          {{ t('common.details') }}
        </h4>
        <div class="section-content grid grid-cols-2 gap-4">
          <div>
            <div class="label">{{ t('inventory.supplier') }}</div>
            <div class="value">{{ contract.supplier?.name || '-' }}</div>
          </div>
          <div>
            <div class="label">{{ t('contracts.annualCost') }}</div>
            <div class="value">{{ contract.annual_cost ? formatCurrency(contract.annual_cost) : '-' }}</div>
          </div>
          <div>
            <div class="label">{{ t('contracts.startDate') }}</div>
            <div class="value">{{ formatDate(contract.start_date) }}</div>
          </div>
          <div>
            <div class="label">{{ t('contracts.endDate') }}</div>
            <div class="value">{{ formatDate(contract.end_date) }}</div>
          </div>
          <div>
            <div class="label">{{ t('contracts.renewalType') }}</div>
            <div class="value">{{ contract.renewal_type || '-' }}</div>
          </div>
          <div>
            <div class="label">{{ t('contracts.renewalNoticeDays') }}</div>
            <div class="value">{{ contract.renewal_notice_days ? `${contract.renewal_notice_days} ${t('common.days')}` : '-' }}</div>
          </div>
        </div>
      </section>

      <!-- Covered Equipment -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-box"></i>
            {{ t('contracts.coveredEquipment') }}
          </span>
          <span class="text-sm font-normal text-muted">{{ linkedEquipment.length }}</span>
        </h4>
        <div class="section-content">
          <div v-if="linkedEquipment.length" class="space-y-2">
            <div
              v-for="eq in linkedEquipment"
              :key="eq.id"
              class="linked-item p-3 rounded-lg flex items-center justify-between cursor-pointer"
              @click="navigateTo('equipment', eq.id)"
            >
              <div class="flex items-center gap-3">
                <i class="pi pi-box"></i>
                <div>
                  <div class="font-medium">{{ eq.name }}</div>
                  <div class="text-sm">{{ eq.serial_number || eq.asset_tag || '-' }}</div>
                </div>
              </div>
              <Tag :value="eq.status" :severity="getEquipmentStatusSeverity(eq.status)" />
            </div>
          </div>
          <div v-else class="text-sm text-muted">{{ t('contracts.noEquipmentLinked') }}</div>
        </div>
      </section>

      <!-- Related Tickets -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-ticket"></i>
            {{ t('tickets.openTickets') }}
          </span>
          <span class="text-sm font-normal text-muted">{{ openTickets.length }}</span>
        </h4>
        <div class="section-content">
          <div v-if="openTickets.length" class="space-y-2">
            <div
              v-for="ticket in openTickets"
              :key="ticket.id"
              class="linked-item p-3 rounded-lg flex items-center justify-between cursor-pointer"
              @click="navigateTo('ticket', ticket.id)"
            >
              <div class="flex items-center gap-3">
                <Tag :value="ticket.status" :severity="getTicketStatusSeverity(ticket.status)" />
                <div>
                  <div class="font-medium">{{ ticket.title }}</div>
                  <div class="text-sm">{{ ticket.ticket_number }}</div>
                </div>
              </div>
              <Tag :value="ticket.priority" :severity="getPrioritySeverity(ticket.priority)" />
            </div>
          </div>
          <div v-else class="text-sm text-muted">{{ t('tickets.noOpenTickets') }}</div>
        </div>
      </section>

      <!-- Notes -->
      <section v-if="contract.notes" class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-comment"></i>
          {{ t('inventory.notes') }}
        </h4>
        <div class="section-content">
          <p class="text-sm whitespace-pre-wrap">{{ contract.notes }}</p>
        </div>
      </section>
    </div>

    <template #footer>
      <div class="flex items-center gap-3">
        <Button
          :label="t('common.edit')"
          icon="pi pi-pencil"
          @click="$emit('edit', contract)"
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
  contractId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'edit'])

const router = useRouter()
const { t } = useI18n()

// State
const contract = ref(null)
const linkedEquipment = ref([])
const openTickets = ref([])
const loading = ref(false)

// Computed
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Methods
const loadContractDetails = async () => {
  if (!props.contractId) return

  loading.value = true
  try {
    // Load contract details
    const contractResponse = await api.get(`/contracts/${props.contractId}`)
    contract.value = contractResponse.data

    // Load linked equipment
    try {
      const eqResponse = await api.get(`/contracts/${props.contractId}/equipment`)
      linkedEquipment.value = eqResponse.data || []
    } catch {
      linkedEquipment.value = []
    }

    // Load related tickets (for equipment under this contract)
    try {
      // Get tickets related to any equipment under this contract
      const equipmentIds = linkedEquipment.value.map(eq => eq.id)
      if (equipmentIds.length > 0) {
        const ticketsResponse = await api.get('/tickets/', {
          params: {
            status: ['new', 'open', 'pending']
          }
        })
        // Filter tickets that are related to covered equipment
        const allTickets = ticketsResponse.data?.items || ticketsResponse.data || []
        openTickets.value = allTickets.filter(t =>
          equipmentIds.includes(t.equipment_id)
        ).slice(0, 5)
      } else {
        openTickets.value = []
      }
    } catch {
      openTickets.value = []
    }
  } catch (error) {
    console.error('Failed to load contract details:', error)
  } finally {
    loading.value = false
  }
}

const navigateTo = (type, id) => {
  visible.value = false
  switch (type) {
    case 'equipment':
      router.push(`/inventory?id=${id}`)
      break
    case 'ticket':
      router.push(`/tickets?id=${id}`)
      break
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString()
}

const formatCurrency = (value) => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(value)
}

// Severity helpers
const getTypeSeverity = (type) => {
  const severities = {
    maintenance: 'info',
    insurance: 'warning',
    leasing: 'success',
    support: 'secondary'
  }
  return severities[type] || null
}

const getContractStatus = (contract) => {
  if (!contract.end_date) return 'active'
  const endDate = new Date(contract.end_date)
  const today = new Date()
  if (endDate < today) return 'expired'
  const daysRemaining = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24))
  if (daysRemaining <= 30) return 'expiring'
  return 'active'
}

const getStatusSeverity = (contract) => {
  const status = getContractStatus(contract)
  const severities = {
    active: 'success',
    expiring: 'warning',
    expired: 'danger'
  }
  return severities[status] || null
}

const getEquipmentStatusSeverity = (status) => {
  const severities = {
    in_service: 'success',
    in_stock: 'info',
    retired: 'secondary',
    maintenance: 'warning'
  }
  return severities[status] || null
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

// Watch for changes
watch(() => [props.modelValue, props.contractId], ([isVisible, id]) => {
  if (isVisible && id) {
    loadContractDetails()
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

.linked-item {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-default);
  transition: all 0.15s ease;
}

.linked-item:hover {
  transform: translateX(4px);
  background-color: var(--bg-hover);
  border-color: var(--primary);
}

.text-muted {
  color: var(--text-muted);
}

.font-medium {
  color: var(--text-primary);
}

.linked-item .font-medium {
  color: var(--text-primary);
}

.linked-item .text-sm {
  color: var(--text-secondary);
}

.section-content p {
  color: var(--text-secondary);
}
</style>
