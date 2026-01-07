<template>
  <SlideOver
    v-model="visible"
    :title="subnet?.name || subnet?.cidr || ''"
    :subtitle="subnet?.cidr || ''"
    icon="pi-sitemap"
    size="lg"
  >
    <div v-if="loading" class="flex justify-center py-12">
      <i class="pi pi-spinner pi-spin text-3xl"></i>
    </div>

    <div v-else-if="subnet" class="space-y-6">
      <!-- Quick Stats -->
      <div class="grid grid-cols-4 gap-3">
        <div class="stat-card p-3 rounded-lg text-center">
          <div class="text-xs mb-1">{{ t('ipam.totalIps') }}</div>
          <div class="text-xl font-bold" style="color: var(--primary)">{{ totalIps }}</div>
        </div>
        <div class="stat-card p-3 rounded-lg text-center">
          <div class="text-xs mb-1">{{ t('ipam.usedIps') }}</div>
          <div class="text-xl font-bold" style="color: var(--warning)">{{ usedIps }}</div>
        </div>
        <div class="stat-card p-3 rounded-lg text-center">
          <div class="text-xs mb-1">{{ t('ipam.available') }}</div>
          <div class="text-xl font-bold" style="color: var(--success)">{{ availableIps }}</div>
        </div>
        <div class="stat-card p-3 rounded-lg text-center">
          <div class="text-xs mb-1">{{ t('ipam.utilization') }}</div>
          <div class="text-xl font-bold" :style="{ color: utilizationColor }">{{ utilizationPercent }}%</div>
        </div>
      </div>

      <!-- Utilization Bar -->
      <div class="p-4 rounded-lg stat-card">
        <div class="flex justify-between text-sm mb-2">
          <span>{{ t('ipam.subnetUtilization') }}</span>
          <span class="font-medium">{{ usedIps }} / {{ totalIps }}</span>
        </div>
        <div class="h-3 rounded-full overflow-hidden" style="background-color: var(--bg-tertiary)">
          <div
            class="h-full rounded-full transition-all duration-500"
            :style="{ width: `${utilizationPercent}%`, backgroundColor: utilizationColor }"
          ></div>
        </div>
      </div>

      <!-- Subnet Info -->
      <section class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-info-circle"></i>
          {{ t('common.details') }}
        </h4>
        <div class="section-content grid grid-cols-2 gap-4">
          <div>
            <div class="label">{{ t('ipam.cidr') }}</div>
            <div class="value font-mono">{{ subnet.cidr }}</div>
          </div>
          <div>
            <div class="label">{{ t('ipam.vlan') }}</div>
            <div class="value">{{ subnet.vlan_id || '-' }}</div>
          </div>
          <div>
            <div class="label">{{ t('ipam.gateway') }}</div>
            <div class="value font-mono">{{ subnet.gateway || '-' }}</div>
          </div>
          <div>
            <div class="label">{{ t('ipam.dns') }}</div>
            <div class="value font-mono">{{ subnet.dns_servers || '-' }}</div>
          </div>
        </div>
      </section>

      <!-- IP Addresses -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-list"></i>
            {{ t('ipam.ipAddresses') }}
          </span>
          <span class="text-sm font-normal text-muted">{{ ipAddresses.length }}</span>
        </h4>
        <div class="section-content">
          <div v-if="ipAddresses.length" class="space-y-2 max-h-80 overflow-auto">
            <div
              v-for="ip in ipAddresses"
              :key="ip.id"
              class="linked-item p-3 rounded-lg flex items-center justify-between"
              :class="{ 'cursor-pointer': ip.equipment_id }"
              @click="ip.equipment_id && navigateTo('equipment', ip.equipment_id)"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-3 h-3 rounded-full"
                  :style="{ backgroundColor: getIpStatusColor(ip.status) }"
                ></div>
                <div>
                  <div class="font-mono font-medium">{{ ip.address }}</div>
                  <div class="text-sm">{{ ip.hostname || '-' }}</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span v-if="ip.equipment_name" class="text-sm" style="color: var(--text-secondary)">
                  {{ ip.equipment_name }}
                </span>
                <Tag :value="ip.status" :severity="getIpStatusSeverity(ip.status)" />
              </div>
            </div>
          </div>
          <div v-else class="text-sm text-muted">{{ t('ipam.noIpAddresses') }}</div>
        </div>
      </section>

      <!-- Linked Equipment Summary -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-box"></i>
            {{ t('ipam.linkedEquipment') }}
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
                  <div class="text-sm">{{ eq.ip_count }} {{ t('ipam.ipAddresses') }}</div>
                </div>
              </div>
              <i class="pi pi-chevron-right"></i>
            </div>
          </div>
          <div v-else class="text-sm text-muted">{{ t('ipam.noLinkedEquipment') }}</div>
        </div>
      </section>

      <!-- Description -->
      <section v-if="subnet.description" class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-comment"></i>
          {{ t('common.description') }}
        </h4>
        <div class="section-content">
          <p class="text-sm whitespace-pre-wrap">{{ subnet.description }}</p>
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
          @click="$emit('scan', subnet)"
        />
        <Button
          :label="t('common.edit')"
          icon="pi pi-pencil"
          @click="$emit('edit', subnet)"
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

const props = defineProps({
  modelValue: Boolean,
  subnetId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'edit', 'scan'])

const router = useRouter()
const { t } = useI18n()

// State
const subnet = ref(null)
const ipAddresses = ref([])
const loading = ref(false)

// Computed
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const totalIps = computed(() => {
  if (!subnet.value?.cidr) return 0
  const prefix = parseInt(subnet.value.cidr.split('/')[1])
  return Math.pow(2, 32 - prefix) - 2 // Exclude network and broadcast
})

const usedIps = computed(() => {
  return ipAddresses.value.filter(ip => ip.status === 'active' || ip.status === 'reserved').length
})

const availableIps = computed(() => {
  return totalIps.value - usedIps.value
})

const utilizationPercent = computed(() => {
  if (totalIps.value === 0) return 0
  return Math.round((usedIps.value / totalIps.value) * 100)
})

const utilizationColor = computed(() => {
  const percent = utilizationPercent.value
  if (percent >= 90) return 'var(--danger)'
  if (percent >= 70) return 'var(--warning)'
  return 'var(--success)'
})

const linkedEquipment = computed(() => {
  const equipmentMap = new Map()
  ipAddresses.value
    .filter(ip => ip.equipment_id && ip.equipment_name)
    .forEach(ip => {
      if (!equipmentMap.has(ip.equipment_id)) {
        equipmentMap.set(ip.equipment_id, {
          id: ip.equipment_id,
          name: ip.equipment_name,
          ip_count: 0
        })
      }
      equipmentMap.get(ip.equipment_id).ip_count++
    })
  return Array.from(equipmentMap.values())
})

// Methods
const loadSubnetDetails = async () => {
  if (!props.subnetId) return

  loading.value = true
  try {
    // Load subnet details
    const subnetResponse = await api.get(`/subnets/${props.subnetId}`)
    subnet.value = subnetResponse.data

    // Load IP addresses
    try {
      const ipsResponse = await api.get(`/subnets/${props.subnetId}/ips`)
      ipAddresses.value = ipsResponse.data || []
    } catch {
      ipAddresses.value = []
    }
  } catch (error) {
    console.error('Failed to load subnet details:', error)
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
  }
}

const getIpStatusColor = (status) => {
  const colors = {
    active: 'var(--success)',
    reserved: 'var(--warning)',
    available: 'var(--text-muted)'
  }
  return colors[status] || 'var(--text-muted)'
}

const getIpStatusSeverity = (status) => {
  const severities = {
    active: 'success',
    reserved: 'warning',
    available: 'secondary'
  }
  return severities[status] || 'secondary'
}

// Watch for changes
watch(() => [props.modelValue, props.subnetId], ([isVisible, id]) => {
  if (isVisible && id) {
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

.stat-card .text-xs {
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

.font-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.linked-item .font-medium,
.linked-item .font-mono {
  color: var(--text-primary);
}

.linked-item .text-sm {
  color: var(--text-secondary);
}

.section-content p {
  color: var(--text-secondary);
}
</style>
