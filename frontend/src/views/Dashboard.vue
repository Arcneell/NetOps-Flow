<template>
  <div class="space-y-6">
    <!-- Welcome Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">{{ t('dashboard.welcome') }}, {{ username }}</h1>
        <p class="text-sm opacity-60 mt-1">{{ t('dashboard.welcomeSubtitle') }}</p>
      </div>
      <div class="text-right text-sm opacity-60">
        <div>{{ currentDate }}</div>
        <div class="text-xs">{{ t('dashboard.lastRefresh') }}: {{ lastRefresh }}</div>
      </div>
    </div>

    <!-- Alert Banner (if critical alerts exist) -->
    <div v-if="criticalAlerts.length > 0" class="bg-gradient-to-r from-red-900/40 to-orange-900/40 border border-red-500/30 rounded-xl p-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0">
          <i class="pi pi-exclamation-triangle text-red-400 text-xl"></i>
        </div>
        <div class="flex-1">
          <h3 class="font-semibold text-red-300">{{ t('dashboard.attentionRequired') }}</h3>
          <p class="text-sm text-red-200/70">{{ criticalAlerts.length }} {{ t('dashboard.criticalItems') }}</p>
        </div>
        <Button :label="t('dashboard.viewAlerts')" size="small" severity="danger" outlined @click="scrollToAlerts" />
      </div>
    </div>

    <!-- Main Stats Grid -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <!-- Network Stats -->
      <router-link to="/ipam" class="stat-card group">
        <div class="stat-icon bg-blue-500/20 text-blue-400 group-hover:bg-blue-500/30">
          <i class="pi pi-sitemap text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.subnets }}</div>
        <div class="stat-label">{{ t('dashboard.subnets') }}</div>
      </router-link>

      <router-link to="/ipam" class="stat-card group">
        <div class="stat-icon bg-green-500/20 text-green-400 group-hover:bg-green-500/30">
          <i class="pi pi-wifi text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.ips_active }}<span class="stat-total">/{{ stats.ips_total }}</span></div>
        <div class="stat-label">{{ t('dashboard.activeIps') }}</div>
      </router-link>

      <!-- Equipment Stats -->
      <router-link to="/inventory" class="stat-card group">
        <div class="stat-icon bg-cyan-500/20 text-cyan-400 group-hover:bg-cyan-500/30">
          <i class="pi pi-box text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.equipment }}</div>
        <div class="stat-label">{{ t('dashboard.equipment') }}</div>
      </router-link>

      <!-- Scripts Stats -->
      <router-link to="/scripts" class="stat-card group">
        <div class="stat-icon bg-purple-500/20 text-purple-400 group-hover:bg-purple-500/30">
          <i class="pi pi-code text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.scripts }}</div>
        <div class="stat-label">{{ t('dashboard.scripts') }}</div>
      </router-link>

      <!-- Contracts Stats -->
      <router-link to="/contracts" class="stat-card group">
        <div class="stat-icon bg-orange-500/20 text-orange-400 group-hover:bg-orange-500/30">
          <i class="pi pi-file-edit text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.contracts_active }}<span class="stat-total">/{{ stats.contracts_total }}</span></div>
        <div class="stat-label">{{ t('dashboard.contracts') }}</div>
      </router-link>

      <!-- DCIM Stats -->
      <router-link to="/dcim" class="stat-card group">
        <div class="stat-icon bg-indigo-500/20 text-indigo-400 group-hover:bg-indigo-500/30">
          <i class="pi pi-server text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.racks }}</div>
        <div class="stat-label">{{ t('dashboard.racks') }}</div>
      </router-link>
    </div>

    <!-- Secondary Row -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Equipment Status Distribution -->
      <div class="card">
        <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-chart-pie text-cyan-400"></i>
          {{ t('dashboard.equipmentStatus') }}
        </h3>
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-green-500"></div>
              <span class="text-sm">{{ t('status.inService') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-bold">{{ stats.equipment_in_service }}</span>
              <div class="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-green-500 rounded-full" :style="{ width: equipmentPercent('in_service') + '%' }"></div>
              </div>
            </div>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-blue-500"></div>
              <span class="text-sm">{{ t('status.inStock') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-bold">{{ stats.equipment_in_stock }}</span>
              <div class="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-blue-500 rounded-full" :style="{ width: equipmentPercent('in_stock') + '%' }"></div>
              </div>
            </div>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
              <span class="text-sm">{{ t('status.maintenance') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-bold">{{ stats.equipment_maintenance }}</span>
              <div class="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-yellow-500 rounded-full" :style="{ width: equipmentPercent('maintenance') + '%' }"></div>
              </div>
            </div>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-gray-500"></div>
              <span class="text-sm">{{ t('status.retired') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-bold">{{ stats.equipment_retired }}</span>
              <div class="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-gray-500 rounded-full" :style="{ width: equipmentPercent('retired') + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Script Executions (Last 7 days) -->
      <div class="card">
        <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-bolt text-purple-400"></i>
          {{ t('dashboard.recentExecutions') }}
        </h3>
        <div class="flex items-center justify-center gap-8 py-4">
          <div class="text-center">
            <div class="text-4xl font-bold text-white">{{ stats.recent_executions }}</div>
            <div class="text-xs opacity-60 mt-1">{{ t('dashboard.last7Days') }}</div>
          </div>
          <div class="h-16 w-px bg-gray-700"></div>
          <div class="space-y-2">
            <div class="flex items-center gap-2">
              <i class="pi pi-check-circle text-green-500"></i>
              <span class="text-sm">{{ stats.executions_success }} {{ t('dashboard.success') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <i class="pi pi-times-circle text-red-500"></i>
              <span class="text-sm">{{ stats.executions_failed }} {{ t('dashboard.failed') }}</span>
            </div>
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-gray-700">
          <div class="flex justify-between text-sm">
            <span class="opacity-60">{{ t('dashboard.totalExecutions') }}</span>
            <span class="font-bold">{{ stats.executions }}</span>
          </div>
        </div>
      </div>

      <!-- Software & License Compliance -->
      <div class="card">
        <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-desktop text-blue-400"></i>
          {{ t('dashboard.softwareLicenses') }}
        </h3>
        <div class="grid grid-cols-2 gap-4">
          <div class="p-3 rounded-lg bg-gray-800/50">
            <div class="text-2xl font-bold">{{ stats.software }}</div>
            <div class="text-xs opacity-60">{{ t('dashboard.softwareItems') }}</div>
          </div>
          <div class="p-3 rounded-lg bg-gray-800/50">
            <div class="text-2xl font-bold">{{ stats.licenses }}</div>
            <div class="text-xs opacity-60">{{ t('dashboard.licenses') }}</div>
          </div>
          <div class="p-3 rounded-lg bg-gray-800/50">
            <div class="text-2xl font-bold">{{ stats.installations }}</div>
            <div class="text-xs opacity-60">{{ t('dashboard.installations') }}</div>
          </div>
          <div class="p-3 rounded-lg" :class="stats.license_violations > 0 ? 'bg-red-900/30' : 'bg-green-900/30'">
            <div class="text-2xl font-bold" :class="stats.license_violations > 0 ? 'text-red-400' : 'text-green-400'">
              {{ stats.license_violations }}
            </div>
            <div class="text-xs opacity-60">{{ t('dashboard.violations') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Third Row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Alerts Panel -->
      <div ref="alertsSection" class="card">
        <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-bell text-orange-400"></i>
          {{ t('dashboard.alerts') }}
          <span v-if="alerts.length" class="ml-auto text-sm font-normal px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400">
            {{ alerts.length }}
          </span>
        </h3>
        <div v-if="alerts.length > 0" class="space-y-2 max-h-80 overflow-y-auto custom-scrollbar">
          <router-link
            v-for="alert in alerts"
            :key="`${alert.type}-${alert.id}`"
            :to="alert.link"
            class="flex items-center gap-3 p-3 rounded-lg transition-colors hover:bg-gray-800/50"
            :class="{
              'bg-red-900/20 border border-red-500/20': alert.severity === 'danger',
              'bg-orange-900/20 border border-orange-500/20': alert.severity === 'warning',
              'bg-blue-900/20 border border-blue-500/20': alert.severity === 'info'
            }"
          >
            <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
              :class="{
                'bg-red-500/20 text-red-400': alert.severity === 'danger',
                'bg-orange-500/20 text-orange-400': alert.severity === 'warning',
                'bg-blue-500/20 text-blue-400': alert.severity === 'info'
              }">
              <i :class="getAlertIcon(alert.type)"></i>
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-medium truncate">{{ alert.title }}</div>
              <div class="text-xs opacity-60">{{ getAlertTypeLabel(alert.type) }} - {{ alert.message }}</div>
            </div>
            <i class="pi pi-chevron-right text-gray-500"></i>
          </router-link>
        </div>
        <div v-else class="text-center py-8 opacity-50">
          <i class="pi pi-check-circle text-4xl text-green-500 mb-3"></i>
          <p>{{ t('dashboard.noAlerts') }}</p>
        </div>
      </div>

      <!-- Recent Activity -->
      <div class="card">
        <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-history text-blue-400"></i>
          {{ t('dashboard.recentActivity') }}
        </h3>
        <div v-if="activities.length > 0" class="space-y-3 max-h-80 overflow-y-auto custom-scrollbar">
          <router-link
            v-for="(activity, index) in activities"
            :key="index"
            :to="activity.link"
            class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-800/50 transition-colors"
          >
            <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
              :class="`bg-${activity.color}-500/20 text-${activity.color}-400`"
              :style="{ backgroundColor: `var(--${activity.color}-100)`, color: `var(--${activity.color}-500)` }">
              <i :class="'pi ' + activity.icon"></i>
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-medium truncate">{{ activity.title }}</div>
              <div class="text-xs opacity-60">{{ activity.description }}</div>
            </div>
            <div class="text-xs opacity-40 flex-shrink-0">
              {{ formatTime(activity.timestamp) }}
            </div>
          </router-link>
        </div>
        <div v-else class="text-center py-8 opacity-50">
          <i class="pi pi-inbox text-4xl mb-3"></i>
          <p>{{ t('dashboard.noActivity') }}</p>
        </div>
      </div>
    </div>

    <!-- Quick Actions & System Status -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Quick Actions -->
      <div class="lg:col-span-2 card">
        <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-bolt text-yellow-400"></i>
          {{ t('dashboard.quickActions') }}
        </h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <router-link to="/ipam" class="action-btn">
            <i class="pi pi-plus text-blue-400"></i>
            <span>{{ t('dashboard.newSubnet') }}</span>
          </router-link>
          <router-link to="/scripts" class="action-btn">
            <i class="pi pi-upload text-purple-400"></i>
            <span>{{ t('dashboard.uploadScript') }}</span>
          </router-link>
          <router-link to="/inventory" class="action-btn">
            <i class="pi pi-box text-cyan-400"></i>
            <span>{{ t('dashboard.addEquipment') }}</span>
          </router-link>
          <router-link to="/topology" class="action-btn">
            <i class="pi pi-share-alt text-green-400"></i>
            <span>{{ t('dashboard.viewTopology') }}</span>
          </router-link>
          <router-link to="/dcim" class="action-btn">
            <i class="pi pi-server text-indigo-400"></i>
            <span>{{ t('dashboard.manageRacks') }}</span>
          </router-link>
          <router-link to="/contracts" class="action-btn">
            <i class="pi pi-file-edit text-orange-400"></i>
            <span>{{ t('dashboard.newContract') }}</span>
          </router-link>
          <router-link to="/software" class="action-btn">
            <i class="pi pi-desktop text-pink-400"></i>
            <span>{{ t('dashboard.manageSoftware') }}</span>
          </router-link>
          <router-link to="/settings" class="action-btn">
            <i class="pi pi-cog text-gray-400"></i>
            <span>{{ t('nav.settings') }}</span>
          </router-link>
        </div>
      </div>

      <!-- System Status -->
      <div class="card">
        <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-server text-green-400"></i>
          {{ t('dashboard.systemStatus') }}
        </h3>
        <div class="space-y-3">
          <div class="flex items-center justify-between p-2 rounded-lg bg-gray-800/30">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              <span class="text-sm">{{ t('dashboard.database') }}</span>
            </div>
            <span class="text-xs text-green-400">{{ t('dashboard.online') }}</span>
          </div>
          <div class="flex items-center justify-between p-2 rounded-lg bg-gray-800/30">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              <span class="text-sm">{{ t('dashboard.worker') }}</span>
            </div>
            <span class="text-xs text-green-400">{{ t('dashboard.online') }}</span>
          </div>
          <div class="flex items-center justify-between p-2 rounded-lg bg-gray-800/30">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              <span class="text-sm">Redis</span>
            </div>
            <span class="text-xs text-green-400">{{ t('dashboard.online') }}</span>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-700">
            <div class="flex justify-between text-sm">
              <span class="opacity-60">{{ t('dashboard.activeUsers') }}</span>
              <span class="font-bold">{{ stats.users }}</span>
            </div>
            <div class="flex justify-between text-sm mt-2">
              <span class="opacity-60">{{ t('dashboard.totalLocations') }}</span>
              <span class="font-bold">{{ stats.locations }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '../api';

const { t } = useI18n();

const stats = ref({
  subnets: 0, ips_total: 0, ips_active: 0,
  scripts: 0, executions: 0, recent_executions: 0, executions_success: 0, executions_failed: 0,
  equipment: 0, equipment_in_service: 0, equipment_in_stock: 0, equipment_maintenance: 0, equipment_retired: 0,
  racks: 0, pdus: 0,
  contracts_total: 0, contracts_active: 0, contracts_expiring: 0,
  software: 0, licenses: 0, installations: 0, license_violations: 0,
  network_ports: 0, ports_connected: 0,
  locations: 0, suppliers: 0, manufacturers: 0, users: 0
});

const alerts = ref([]);
const activities = ref([]);
const alertsSection = ref(null);
const lastRefresh = ref('');

const username = computed(() => localStorage.getItem('username') || 'User');

const currentDate = computed(() => {
  return new Date().toLocaleDateString(undefined, {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });
});

const criticalAlerts = computed(() => alerts.value.filter(a => a.severity === 'danger'));

const equipmentPercent = (status) => {
  const total = stats.value.equipment || 1;
  const map = {
    'in_service': stats.value.equipment_in_service,
    'in_stock': stats.value.equipment_in_stock,
    'maintenance': stats.value.equipment_maintenance,
    'retired': stats.value.equipment_retired
  };
  return Math.round((map[status] / total) * 100);
};

const getAlertIcon = (type) => {
  const icons = {
    contract: 'pi pi-file-edit',
    license: 'pi pi-key',
    warranty: 'pi pi-shield',
    violation: 'pi pi-exclamation-triangle',
    maintenance: 'pi pi-wrench'
  };
  return icons[type] || 'pi pi-info-circle';
};

const getAlertTypeLabel = (type) => {
  const labels = {
    contract: t('dashboard.alertContract'),
    license: t('dashboard.alertLicense'),
    warranty: t('dashboard.alertWarranty'),
    violation: t('dashboard.alertViolation'),
    maintenance: t('dashboard.alertMaintenance')
  };
  return labels[type] || type;
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return t('dashboard.justNow');
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
  return date.toLocaleDateString();
};

const scrollToAlerts = () => {
  alertsSection.value?.scrollIntoView({ behavior: 'smooth' });
};

const loadDashboard = async () => {
  try {
    const [statsRes, alertsRes, activitiesRes] = await Promise.all([
      api.get('/dashboard/stats'),
      api.get('/dashboard/alerts'),
      api.get('/dashboard/recent-activity')
    ]);
    stats.value = statsRes.data;
    alerts.value = alertsRes.data;
    activities.value = activitiesRes.data;
    lastRefresh.value = new Date().toLocaleTimeString();
  } catch (e) {
    console.error("Failed to fetch dashboard data", e);
  }
};

onMounted(loadDashboard);
</script>

<style scoped>
.stat-card {
  @apply card p-4 flex flex-col items-center text-center cursor-pointer transition-all hover:scale-105 hover:border-blue-500/50;
}

.stat-icon {
  @apply w-12 h-12 rounded-xl flex items-center justify-center mb-3 transition-colors;
}

.stat-value {
  @apply text-2xl font-bold text-white;
}

.stat-total {
  @apply text-sm font-normal opacity-50 ml-1;
}

.stat-label {
  @apply text-xs opacity-60 mt-1;
}

.action-btn {
  @apply flex flex-col items-center justify-center gap-2 p-4 rounded-xl bg-gray-800/30 border border-gray-700/50 hover:border-blue-500/50 hover:bg-gray-800/50 transition-all cursor-pointer text-center;
}

.action-btn i {
  @apply text-xl;
}

.action-btn span {
  @apply text-xs;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.2);
}
</style>
