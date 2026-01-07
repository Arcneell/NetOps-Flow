<template>
  <SlideOver
    v-model="visible"
    :title="rack?.name || ''"
    :subtitle="rack?.location ? `${rack.location.site}${rack.location.building ? ' / ' + rack.location.building : ''}${rack.location.room ? ' / ' + rack.location.room : ''}` : ''"
    icon="pi-server"
    size="xl"
  >
    <div v-if="loading" class="flex justify-center py-12">
      <i class="pi pi-spinner pi-spin text-3xl"></i>
    </div>

    <div v-else-if="rack" class="space-y-6">
      <!-- Quick Stats -->
      <div class="grid grid-cols-4 gap-3">
        <div class="stat-card p-3 rounded-lg text-center">
          <div class="text-xs mb-1">{{ t('dcim.heightU') }}</div>
          <div class="text-xl font-bold" style="color: var(--primary)">{{ rack.height_u }}U</div>
        </div>
        <div class="stat-card p-3 rounded-lg text-center">
          <div class="text-xs mb-1">{{ t('dcim.usedU') }}</div>
          <div class="text-xl font-bold" style="color: var(--info)">{{ usedUnits }}U</div>
        </div>
        <div class="stat-card p-3 rounded-lg text-center">
          <div class="text-xs mb-1">{{ t('dcim.freeU') }}</div>
          <div class="text-xl font-bold" style="color: var(--success)">{{ freeUnits }}U</div>
        </div>
        <div class="stat-card p-3 rounded-lg text-center">
          <div class="text-xs mb-1">{{ t('dcim.utilization') }}</div>
          <div class="text-xl font-bold" :style="{ color: utilizationColor }">{{ utilizationPercent }}%</div>
        </div>
      </div>

      <!-- Utilization Bar -->
      <div class="p-4 rounded-lg stat-card">
        <div class="flex justify-between text-sm mb-2">
          <span>{{ t('dcim.rackUtilization') }}</span>
          <span class="font-medium">{{ usedUnits }} / {{ rack.height_u }} U</span>
        </div>
        <div class="h-3 rounded-full overflow-hidden" style="background-color: var(--bg-tertiary)">
          <div
            class="h-full rounded-full transition-all duration-500"
            :style="{ width: `${utilizationPercent}%`, backgroundColor: utilizationColor }"
          ></div>
        </div>
      </div>

      <!-- Rack Specs -->
      <section class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-cog"></i>
          {{ t('dcim.specifications') }}
        </h4>
        <div class="section-content grid grid-cols-2 gap-4">
          <div>
            <div class="label">{{ t('dcim.dimensions') }}</div>
            <div class="value">{{ rack.width_mm }} x {{ rack.depth_mm }} mm</div>
          </div>
          <div>
            <div class="label">{{ t('dcim.maxPower') }}</div>
            <div class="value">{{ rack.max_power_kw ? `${rack.max_power_kw} kW` : '-' }}</div>
          </div>
          <div>
            <div class="label">{{ t('dcim.maxWeight') }}</div>
            <div class="value">{{ rack.max_weight_kg ? `${rack.max_weight_kg} kg` : '-' }}</div>
          </div>
          <div>
            <div class="label">{{ t('inventory.location') }}</div>
            <div class="value">
              <span v-if="rack.location">
                {{ rack.location.site }}
                <span v-if="rack.location.building"> / {{ rack.location.building }}</span>
                <span v-if="rack.location.room"> / {{ rack.location.room }}</span>
              </span>
              <span v-else class="text-muted">-</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Equipment in Rack -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-box"></i>
            {{ t('dcim.installedEquipment') }}
          </span>
          <span class="text-sm font-normal text-muted">{{ equipmentInRack.length }}</span>
        </h4>
        <div class="section-content">
          <div v-if="equipmentInRack.length" class="space-y-2">
            <div
              v-for="eq in equipmentInRack"
              :key="eq.id"
              class="linked-item p-3 rounded-lg flex items-center justify-between cursor-pointer"
              @click="navigateTo('equipment', eq.id)"
            >
              <div class="flex items-center gap-3">
                <div
                  class="w-10 h-10 rounded-lg flex items-center justify-center"
                  :style="{ backgroundColor: getStatusColor(eq.status) + '20', color: getStatusColor(eq.status) }"
                >
                  <i class="pi pi-box"></i>
                </div>
                <div>
                  <div class="font-medium">{{ eq.name }}</div>
                  <div class="text-sm flex items-center gap-2">
                    <span>U{{ eq.position_u }} - U{{ eq.position_u + (eq.height_u || 1) - 1 }}</span>
                    <span class="opacity-50">|</span>
                    <span>{{ eq.height_u || 1 }}U</span>
                  </div>
                </div>
              </div>
              <Tag :value="eq.status" :severity="getStatusSeverity(eq.status)" />
            </div>
          </div>
          <div v-else class="text-sm text-muted">{{ t('dcim.noEquipmentInRack') }}</div>
        </div>
      </section>

      <!-- PDUs -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-bolt"></i>
            {{ t('dcim.pdus') }}
          </span>
          <span class="text-sm font-normal text-muted">{{ pdusInRack.length }}</span>
        </h4>
        <div class="section-content">
          <div v-if="pdusInRack.length" class="space-y-2">
            <div
              v-for="pdu in pdusInRack"
              :key="pdu.id"
              class="linked-item p-3 rounded-lg flex items-center justify-between"
            >
              <div class="flex items-center gap-3">
                <i class="pi pi-bolt" style="color: var(--warning)"></i>
                <div>
                  <div class="font-medium">{{ pdu.name }}</div>
                  <div class="text-sm">{{ pdu.manufacturer }} | {{ pdu.total_ports }} {{ t('dcim.ports') }}</div>
                </div>
              </div>
              <span class="text-sm" style="color: var(--text-secondary)">{{ pdu.power_capacity_kw }} kW</span>
            </div>
          </div>
          <div v-else class="text-sm text-muted">{{ t('dcim.noPdusInRack') }}</div>
        </div>
      </section>

      <!-- Notes -->
      <section v-if="rack.notes" class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-comment"></i>
          {{ t('inventory.notes') }}
        </h4>
        <div class="section-content">
          <p class="text-sm whitespace-pre-wrap">{{ rack.notes }}</p>
        </div>
      </section>
    </div>

    <template #footer>
      <div class="flex items-center gap-3">
        <Button
          :label="t('dcim.viewLayout')"
          icon="pi pi-th-large"
          severity="secondary"
          outlined
          @click="$emit('view-layout', rack)"
        />
        <Button
          :label="t('common.edit')"
          icon="pi pi-pencil"
          @click="$emit('edit', rack)"
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
  rackId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'edit', 'view-layout'])

const router = useRouter()
const { t } = useI18n()

// State
const rack = ref(null)
const equipmentInRack = ref([])
const pdusInRack = ref([])
const loading = ref(false)

// Computed
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const usedUnits = computed(() => {
  return equipmentInRack.value.reduce((total, eq) => total + (eq.height_u || 1), 0)
})

const freeUnits = computed(() => {
  return (rack.value?.height_u || 0) - usedUnits.value
})

const utilizationPercent = computed(() => {
  if (!rack.value?.height_u) return 0
  return Math.round((usedUnits.value / rack.value.height_u) * 100)
})

const utilizationColor = computed(() => {
  const percent = utilizationPercent.value
  if (percent >= 90) return 'var(--danger)'
  if (percent >= 70) return 'var(--warning)'
  return 'var(--success)'
})

// Methods
const loadRackDetails = async () => {
  if (!props.rackId) return

  loading.value = true
  try {
    // Load rack layout which includes equipment and PDUs
    const layoutResponse = await api.get(`/dcim/racks/${props.rackId}/layout`)
    const layoutData = layoutResponse.data

    rack.value = {
      id: layoutData.rack_id,
      name: layoutData.rack_name,
      height_u: layoutData.height_u,
      width_mm: layoutData.width_mm,
      depth_mm: layoutData.depth_mm,
      max_power_kw: layoutData.max_power_kw,
      max_weight_kg: layoutData.max_weight_kg,
      location: layoutData.location,
      notes: layoutData.notes
    }

    equipmentInRack.value = layoutData.equipment || []
    pdusInRack.value = layoutData.pdus || []
  } catch (error) {
    console.error('Failed to load rack details:', error)
    // Fallback: try to load basic rack info
    try {
      const rackResponse = await api.get(`/dcim/racks/${props.rackId}`)
      rack.value = rackResponse.data
      equipmentInRack.value = []
      pdusInRack.value = []
    } catch {
      rack.value = null
    }
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

const getStatusColor = (status) => {
  const colors = {
    in_service: 'var(--success)',
    in_stock: 'var(--info)',
    retired: 'var(--text-muted)',
    maintenance: 'var(--warning)'
  }
  return colors[status] || 'var(--text-secondary)'
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

// Watch for changes
watch(() => [props.modelValue, props.rackId], ([isVisible, id]) => {
  if (isVisible && id) {
    loadRackDetails()
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
