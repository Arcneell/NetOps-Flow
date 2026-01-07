<template>
  <SlideOver
    v-model="visible"
    :title="software?.name || ''"
    :subtitle="software?.publisher || ''"
    icon="pi-box"
    size="lg"
  >
    <div v-if="loading" class="flex justify-center py-12">
      <i class="pi pi-spinner pi-spin text-3xl"></i>
    </div>

    <div v-else-if="software" class="space-y-6">
      <!-- Quick Stats -->
      <div class="grid grid-cols-3 gap-4">
        <div class="stat-card p-4 rounded-lg">
          <div class="text-sm mb-1">{{ t('software.version') }}</div>
          <div class="font-medium">{{ software.version || '-' }}</div>
        </div>
        <div class="stat-card p-4 rounded-lg">
          <div class="text-sm mb-1">{{ t('software.category') }}</div>
          <Tag v-if="software.category" :value="software.category" />
          <span v-else class="text-muted">-</span>
        </div>
        <div class="stat-card p-4 rounded-lg">
          <div class="text-sm mb-1">{{ t('software.compliance') }}</div>
          <Tag :value="software.compliance_status || 'N/A'" :severity="getComplianceSeverity(software.compliance_status)" />
        </div>
      </div>

      <!-- License Overview -->
      <section class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-key"></i>
          {{ t('software.licenseOverview') }}
        </h4>
        <div class="section-content">
          <div class="grid grid-cols-3 gap-4 mb-4">
            <div class="text-center p-3 rounded-lg stat-card">
              <div class="text-2xl font-bold" style="color: var(--primary)">{{ software.total_licenses || 0 }}</div>
              <div class="text-sm">{{ t('software.totalLicenses') }}</div>
            </div>
            <div class="text-center p-3 rounded-lg stat-card">
              <div class="text-2xl font-bold" style="color: var(--info)">{{ software.total_installations || 0 }}</div>
              <div class="text-sm">{{ t('software.installations') }}</div>
            </div>
            <div class="text-center p-3 rounded-lg stat-card">
              <div class="text-2xl font-bold" :style="{ color: availableLicenses >= 0 ? 'var(--success)' : 'var(--danger)' }">
                {{ availableLicenses }}
              </div>
              <div class="text-sm">{{ t('software.available') }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Licenses List -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-key"></i>
            {{ t('software.licenses') }}
          </span>
          <span class="text-sm font-normal text-muted">{{ licenses.length }}</span>
        </h4>
        <div class="section-content">
          <div v-if="licenses.length" class="space-y-2">
            <div
              v-for="license in licenses"
              :key="license.id"
              class="linked-item p-3 rounded-lg"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="font-medium">{{ license.license_key || t('software.noKey') }}</div>
                <Tag :value="`${license.quantity} ${t('software.seats')}`" severity="info" />
              </div>
              <div class="flex items-center justify-between text-sm">
                <span class="text-secondary">{{ license.license_type || '-' }}</span>
                <ExpiryBadge v-if="license.expiry_date" :date="license.expiry_date" compact />
              </div>
            </div>
          </div>
          <div v-else class="text-sm text-muted">{{ t('software.noLicenses') }}</div>
        </div>
      </section>

      <!-- Installations -->
      <section class="detail-section">
        <h4 class="section-title flex items-center justify-between">
          <span class="flex items-center gap-2">
            <i class="pi pi-desktop"></i>
            {{ t('software.installations') }}
          </span>
          <span class="text-sm font-normal text-muted">{{ installations.length }}</span>
        </h4>
        <div class="section-content">
          <div v-if="installations.length" class="space-y-2">
            <div
              v-for="install in installations"
              :key="install.id"
              class="linked-item p-3 rounded-lg flex items-center justify-between cursor-pointer"
              @click="navigateTo('equipment', install.equipment_id)"
            >
              <div class="flex items-center gap-3">
                <i class="pi pi-box"></i>
                <div>
                  <div class="font-medium">{{ install.equipment?.name || `Equipment #${install.equipment_id}` }}</div>
                  <div class="text-sm">{{ t('software.installedOn') }}: {{ formatDate(install.installed_at) }}</div>
                </div>
              </div>
              <span class="text-sm" style="color: var(--text-secondary)">{{ install.installed_version || software.version }}</span>
            </div>
          </div>
          <div v-else class="text-sm text-muted">{{ t('software.noInstallations') }}</div>
        </div>
      </section>

      <!-- Notes -->
      <section v-if="software.notes" class="detail-section">
        <h4 class="section-title">
          <i class="pi pi-comment"></i>
          {{ t('inventory.notes') }}
        </h4>
        <div class="section-content">
          <p class="text-sm whitespace-pre-wrap">{{ software.notes }}</p>
        </div>
      </section>
    </div>

    <template #footer>
      <div class="flex items-center gap-3">
        <Button
          :label="t('software.manageLicenses')"
          icon="pi pi-key"
          severity="secondary"
          outlined
          @click="$emit('manage-licenses', software)"
        />
        <Button
          :label="t('common.edit')"
          icon="pi pi-pencil"
          @click="$emit('edit', software)"
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
  softwareId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'edit', 'manage-licenses'])

const router = useRouter()
const { t } = useI18n()

// State
const software = ref(null)
const licenses = ref([])
const installations = ref([])
const loading = ref(false)

// Computed
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const availableLicenses = computed(() => {
  return (software.value?.total_licenses || 0) - (software.value?.total_installations || 0)
})

// Methods
const loadSoftwareDetails = async () => {
  if (!props.softwareId) return

  loading.value = true
  try {
    // Load software details
    const swResponse = await api.get(`/software/${props.softwareId}`)
    software.value = swResponse.data

    // Load licenses
    try {
      const licensesResponse = await api.get(`/software/${props.softwareId}/licenses`)
      licenses.value = licensesResponse.data || []
    } catch {
      licenses.value = []
    }

    // Load installations
    try {
      const installsResponse = await api.get(`/software/${props.softwareId}/installations`)
      installations.value = installsResponse.data || []
    } catch {
      installations.value = []
    }
  } catch (error) {
    console.error('Failed to load software details:', error)
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

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString()
}

// Severity helpers
const getComplianceSeverity = (status) => {
  const severities = {
    compliant: 'success',
    warning: 'warning',
    violation: 'danger',
    unknown: 'secondary'
  }
  return severities[status] || 'secondary'
}

// Watch for changes
watch(() => [props.modelValue, props.softwareId], ([isVisible, id]) => {
  if (isVisible && id) {
    loadSoftwareDetails()
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

.text-secondary {
  color: var(--text-secondary);
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
