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

    <!-- Alert Banner (if critical alerts exist) - Admin only -->
    <div v-if="isAdmin && criticalAlerts.length > 0" class="bg-red-50 dark:bg-gradient-to-r dark:from-red-900/40 dark:to-orange-900/40 border border-red-300 dark:border-red-500/30 rounded-xl p-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-red-100 dark:bg-red-500/20 flex items-center justify-center flex-shrink-0">
          <i class="pi pi-exclamation-triangle text-red-600 dark:text-red-400 text-xl"></i>
        </div>
        <div class="flex-1">
          <h3 class="font-semibold text-red-700 dark:text-red-300">{{ t('dashboard.attentionRequired') }}</h3>
          <p class="text-sm text-red-600/70 dark:text-red-200/70">{{ criticalAlerts.length }} {{ t('dashboard.criticalItems') }}</p>
        </div>
        <Button :label="t('dashboard.viewAlerts')" size="small" severity="danger" outlined @click="scrollToAlerts" />
      </div>
    </div>

    <!-- Main Stats Grid -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <!-- Tickets Stats - Always visible -->
      <router-link to="/tickets" class="stat-card group">
        <div class="stat-icon bg-red-500/20 text-red-400 group-hover:bg-red-500/30">
          <i class="pi pi-ticket text-xl"></i>
        </div>
        <div class="stat-value">{{ ticketStats.open + ticketStats.new }}<span class="stat-total">/{{ ticketStats.total }}</span></div>
        <div class="stat-label">{{ t('dashboard.openTickets') }}</div>
      </router-link>

      <!-- Network Stats - Admin only -->
      <router-link v-if="isAdmin" to="/ipam" class="stat-card group">
        <div class="stat-icon bg-blue-500/20 text-blue-400 group-hover:bg-blue-500/30">
          <i class="pi pi-sitemap text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.subnets }}</div>
        <div class="stat-label">{{ t('dashboard.subnets') }}</div>
      </router-link>

      <router-link v-if="isAdmin" to="/ipam" class="stat-card group">
        <div class="stat-icon bg-green-500/20 text-green-400 group-hover:bg-green-500/30">
          <i class="pi pi-wifi text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.ips_active }}<span class="stat-total">/{{ stats.ips_total }}</span></div>
        <div class="stat-label">{{ t('dashboard.activeIps') }}</div>
      </router-link>

      <!-- Equipment Stats - Admin only -->
      <router-link v-if="isAdmin" to="/inventory" class="stat-card group">
        <div class="stat-icon bg-cyan-500/20 text-cyan-400 group-hover:bg-cyan-500/30">
          <i class="pi pi-box text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.equipment }}</div>
        <div class="stat-label">{{ t('dashboard.equipment') }}</div>
      </router-link>

      <!-- Contracts Stats - Admin only -->
      <router-link v-if="isAdmin" to="/contracts" class="stat-card group">
        <div class="stat-icon bg-orange-500/20 text-orange-400 group-hover:bg-orange-500/30">
          <i class="pi pi-file-edit text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.contracts_active }}<span class="stat-total">/{{ stats.contracts_total }}</span></div>
        <div class="stat-label">{{ t('dashboard.contracts') }}</div>
      </router-link>

      <!-- DCIM Stats - Admin only -->
      <router-link v-if="isAdmin" to="/dcim" class="stat-card group">
        <div class="stat-icon bg-indigo-500/20 text-indigo-400 group-hover:bg-indigo-500/30">
          <i class="pi pi-server text-xl"></i>
        </div>
        <div class="stat-value">{{ stats.racks }}</div>
        <div class="stat-label">{{ t('dashboard.racks') }}</div>
      </router-link>
    </div>

    <!-- Ticket Section - Always visible -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Ticket Status Overview -->
      <div class="card">
        <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-ticket text-red-400"></i>
          {{ t('tickets.title') }}
        </h3>
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-blue-500"></div>
              <span class="text-sm">{{ t('tickets.statusNew') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-bold">{{ ticketStats.new }}</span>
              <div class="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-blue-500 rounded-full" :style="{ width: ticketPercent('new') + '%' }"></div>
              </div>
            </div>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
              <span class="text-sm">{{ t('tickets.statusOpen') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-bold">{{ ticketStats.open }}</span>
              <div class="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-yellow-500 rounded-full" :style="{ width: ticketPercent('open') + '%' }"></div>
              </div>
            </div>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-orange-500"></div>
              <span class="text-sm">{{ t('tickets.statusPending') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-bold">{{ ticketStats.pending }}</span>
              <div class="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-orange-500 rounded-full" :style="{ width: ticketPercent('pending') + '%' }"></div>
              </div>
            </div>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-green-500"></div>
              <span class="text-sm">{{ t('tickets.statusResolved') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-bold">{{ ticketStats.resolved }}</span>
              <div class="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-green-500 rounded-full" :style="{ width: ticketPercent('resolved') + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <router-link to="/tickets" class="text-sm text-sky-500 hover:text-sky-400 flex items-center gap-1">
            {{ t('tickets.viewAll') }}
            <i class="pi pi-arrow-right text-xs"></i>
          </router-link>
        </div>
      </div>

      <!-- Recent Tickets -->
      <div class="card">
        <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-clock text-yellow-400"></i>
          {{ t('dashboard.recentTickets') }}
        </h3>
        <div v-if="recentTickets.length > 0" class="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
          <router-link
            v-for="ticket in recentTickets"
            :key="ticket.id"
            :to="`/tickets?id=${ticket.id}`"
            class="flex items-center gap-3 p-3 rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-800/50"
          >
            <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
              :class="getTicketPriorityClass(ticket.priority)">
              <i class="pi pi-ticket text-sm"></i>
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-medium truncate text-sm">{{ ticket.title }}</div>
              <div class="text-xs opacity-60">{{ ticket.ticket_number }} - {{ getStatusLabel(ticket.status) }}</div>
            </div>
            <div class="text-xs opacity-40">
              {{ formatTicketTime(ticket.created_at) }}
            </div>
          </router-link>
        </div>
        <div v-else class="text-center py-8 opacity-50">
          <i class="pi pi-inbox text-4xl mb-3"></i>
          <p>{{ t('dashboard.noTickets') }}</p>
        </div>
      </div>
    </div>

    <!-- Admin Only Sections -->
    <template v-if="isAdmin">
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
                <div class="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
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
                <div class="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
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
                <div class="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
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
                <div class="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div class="h-full bg-gray-500 rounded-full" :style="{ width: equipmentPercent('retired') + '%' }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Ticket Priority Distribution -->
        <div class="card">
          <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
            <i class="pi pi-exclamation-triangle text-orange-400"></i>
            {{ t('dashboard.ticketsByPriority') }}
          </h3>
          <div class="flex items-center justify-center gap-4 py-4">
            <div class="text-center">
              <div class="text-3xl font-bold text-red-500">{{ ticketStats.by_priority?.critical || 0 }}</div>
              <div class="text-xs mt-1" style="color: var(--text-muted);">{{ t('tickets.priorityCritical') }}</div>
            </div>
            <div class="text-center">
              <div class="text-3xl font-bold text-orange-500">{{ ticketStats.by_priority?.high || 0 }}</div>
              <div class="text-xs mt-1" style="color: var(--text-muted);">{{ t('tickets.priorityHigh') }}</div>
            </div>
            <div class="text-center">
              <div class="text-3xl font-bold text-yellow-500">{{ ticketStats.by_priority?.medium || 0 }}</div>
              <div class="text-xs mt-1" style="color: var(--text-muted);">{{ t('tickets.priorityMedium') }}</div>
            </div>
            <div class="text-center">
              <div class="text-3xl font-bold text-green-500">{{ ticketStats.by_priority?.low || 0 }}</div>
              <div class="text-xs mt-1" style="color: var(--text-muted);">{{ t('tickets.priorityLow') }}</div>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div class="flex justify-between text-sm">
              <span style="color: var(--text-muted);">{{ t('dashboard.slaBreached') }}</span>
              <span class="font-bold" :class="ticketStats.sla_breached > 0 ? 'text-red-500' : 'text-green-500'">{{ ticketStats.sla_breached }}</span>
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
            <div class="p-3 rounded-lg bg-gray-100 dark:bg-gray-800/50">
              <div class="text-2xl font-bold">{{ stats.software }}</div>
              <div class="text-xs" style="color: var(--text-muted);">{{ t('dashboard.softwareItems') }}</div>
            </div>
            <div class="p-3 rounded-lg bg-gray-100 dark:bg-gray-800/50">
              <div class="text-2xl font-bold">{{ stats.licenses }}</div>
              <div class="text-xs" style="color: var(--text-muted);">{{ t('dashboard.licenses') }}</div>
            </div>
            <div class="p-3 rounded-lg bg-gray-100 dark:bg-gray-800/50">
              <div class="text-2xl font-bold">{{ stats.installations }}</div>
              <div class="text-xs" style="color: var(--text-muted);">{{ t('dashboard.installations') }}</div>
            </div>
            <div class="p-3 rounded-lg" :class="stats.license_violations > 0 ? 'bg-red-100 dark:bg-red-900/30' : 'bg-green-100 dark:bg-green-900/30'">
              <div class="text-2xl font-bold" :class="stats.license_violations > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'">
                {{ stats.license_violations }}
              </div>
              <div class="text-xs" style="color: var(--text-muted);">{{ t('dashboard.violations') }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Third Row - Admin only -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Alerts Panel -->
        <div ref="alertsSection" class="card">
          <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
            <i class="pi pi-bell text-orange-400"></i>
            {{ t('dashboard.alerts') }}
            <span v-if="alerts.length" class="ml-auto text-sm font-normal px-2 py-0.5 rounded-full bg-orange-100 dark:bg-orange-500/20 text-orange-600 dark:text-orange-400">
              {{ alerts.length }}
            </span>
          </h3>
          <div v-if="alerts.length > 0" class="space-y-2 max-h-80 overflow-y-auto custom-scrollbar">
            <router-link
              v-for="alert in alerts"
              :key="`${alert.type}-${alert.id}`"
              :to="alert.link"
              class="flex items-center gap-3 p-3 rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-800/50"
              :class="{
                'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-500/20': alert.severity === 'danger',
                'bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-500/20': alert.severity === 'warning',
                'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-500/20': alert.severity === 'info'
              }"
            >
              <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                :class="{
                  'bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400': alert.severity === 'danger',
                  'bg-orange-100 dark:bg-orange-500/20 text-orange-600 dark:text-orange-400': alert.severity === 'warning',
                  'bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400': alert.severity === 'info'
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
              class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors"
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

      <!-- Quick Actions & System Status - Admin only -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Quick Actions -->
        <div class="lg:col-span-2 card">
          <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
            <i class="pi pi-bolt text-yellow-400"></i>
            {{ t('dashboard.quickActions') }}
          </h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <router-link to="/tickets" class="action-btn">
              <i class="pi pi-ticket text-red-400"></i>
              <span>{{ t('dashboard.newTicket') }}</span>
            </router-link>
            <router-link to="/ipam" class="action-btn">
              <i class="pi pi-plus text-blue-400"></i>
              <span>{{ t('dashboard.newSubnet') }}</span>
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
            <div class="flex items-center justify-between p-2 rounded-lg bg-gray-100 dark:bg-gray-800/30">
              <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                <span class="text-sm">{{ t('dashboard.database') }}</span>
              </div>
              <span class="text-xs text-green-600 dark:text-green-400">{{ t('dashboard.online') }}</span>
            </div>
            <div class="flex items-center justify-between p-2 rounded-lg bg-gray-100 dark:bg-gray-800/30">
              <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                <span class="text-sm">{{ t('dashboard.worker') }}</span>
              </div>
              <span class="text-xs text-green-600 dark:text-green-400">{{ t('dashboard.online') }}</span>
            </div>
            <div class="flex items-center justify-between p-2 rounded-lg bg-gray-100 dark:bg-gray-800/30">
              <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                <span class="text-sm">Redis</span>
              </div>
              <span class="text-xs text-green-600 dark:text-green-400">{{ t('dashboard.online') }}</span>
            </div>
            <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div class="flex justify-between text-sm">
                <span style="color: var(--text-muted);">{{ t('dashboard.activeUsers') }}</span>
                <span class="font-bold">{{ stats.users }}</span>
              </div>
              <div class="flex justify-between text-sm mt-2">
                <span style="color: var(--text-muted);">{{ t('dashboard.totalLocations') }}</span>
                <span class="font-bold">{{ stats.locations }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- User Quick Actions (non-admin) -->
    <div v-if="!isAdmin" class="card">
      <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
        <i class="pi pi-bolt text-yellow-400"></i>
        {{ t('dashboard.quickActions') }}
      </h3>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
        <router-link to="/tickets" class="action-btn">
          <i class="pi pi-plus text-red-400"></i>
          <span>{{ t('dashboard.newTicket') }}</span>
        </router-link>
        <router-link to="/tickets" class="action-btn">
          <i class="pi pi-list text-blue-400"></i>
          <span>{{ t('tickets.myTickets') }}</span>
        </router-link>
        <router-link to="/knowledge" class="action-btn">
          <i class="pi pi-book text-green-400"></i>
          <span>{{ t('dashboard.knowledgeBase') }}</span>
        </router-link>
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

const ticketStats = ref({
  total: 0, new: 0, open: 0, pending: 0, resolved: 0, closed: 0,
  sla_breached: 0,
  by_priority: { critical: 0, high: 0, medium: 0, low: 0 },
  by_type: { incident: 0, request: 0, problem: 0, change: 0 }
});

const recentTickets = ref([]);
const alerts = ref([]);
const activities = ref([]);
const alertsSection = ref(null);
const lastRefresh = ref('');

const username = computed(() => localStorage.getItem('username') || 'User');

const isAdmin = computed(() => {
  const userStr = localStorage.getItem('user');
  if (userStr) {
    try {
      const user = JSON.parse(userStr);
      return user.role === 'admin';
    } catch (e) {
      return false;
    }
  }
  return false;
});

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

const ticketPercent = (status) => {
  const total = ticketStats.value.total || 1;
  return Math.round((ticketStats.value[status] / total) * 100);
};

const getTicketPriorityClass = (priority) => {
  const classes = {
    critical: 'bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400',
    high: 'bg-orange-100 dark:bg-orange-500/20 text-orange-600 dark:text-orange-400',
    medium: 'bg-yellow-100 dark:bg-yellow-500/20 text-yellow-600 dark:text-yellow-400',
    low: 'bg-green-100 dark:bg-green-500/20 text-green-600 dark:text-green-400'
  };
  return classes[priority] || classes.medium;
};

const getStatusLabel = (status) => {
  const labels = {
    new: t('tickets.statusNew'),
    open: t('tickets.statusOpen'),
    pending: t('tickets.statusPending'),
    resolved: t('tickets.statusResolved'),
    closed: t('tickets.statusClosed')
  };
  return labels[status] || status;
};

const getAlertIcon = (type) => {
  const icons = {
    contract: 'pi pi-file-edit',
    license: 'pi pi-key',
    warranty: 'pi pi-shield',
    violation: 'pi pi-exclamation-triangle',
    maintenance: 'pi pi-wrench',
    ticket: 'pi pi-ticket'
  };
  return icons[type] || 'pi pi-info-circle';
};

const getAlertTypeLabel = (type) => {
  const labels = {
    contract: t('dashboard.alertContract'),
    license: t('dashboard.alertLicense'),
    warranty: t('dashboard.alertWarranty'),
    violation: t('dashboard.alertViolation'),
    maintenance: t('dashboard.alertMaintenance'),
    ticket: t('dashboard.alertTicket')
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

const formatTicketTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return t('dashboard.justNow');
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}d`;
  return date.toLocaleDateString();
};

const scrollToAlerts = () => {
  alertsSection.value?.scrollIntoView({ behavior: 'smooth' });
};

const loadDashboard = async () => {
  try {
    // Load ticket stats for all users
    const ticketStatsRes = await api.get('/tickets/stats');
    ticketStats.value = ticketStatsRes.data;

    // Load recent tickets
    const ticketsRes = await api.get('/tickets/', { params: { limit: 5 } });
    recentTickets.value = ticketsRes.data;

    // Load admin-only data
    if (isAdmin.value) {
      const [statsRes, alertsRes, activitiesRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/dashboard/alerts'),
        api.get('/dashboard/recent-activity')
      ]);
      stats.value = statsRes.data;
      alerts.value = alertsRes.data;
      activities.value = activitiesRes.data;
    }

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
  @apply text-2xl font-bold;
  color: var(--text-main);
}

.stat-total {
  @apply text-sm font-normal opacity-50 ml-1;
}

.stat-label {
  @apply text-xs mt-1;
  color: var(--text-muted);
}

.action-btn {
  @apply flex flex-col items-center justify-center gap-2 p-4 rounded-xl border transition-all cursor-pointer text-center;
  background-color: var(--bg-secondary);
  border-color: var(--border-color);
}

.action-btn:hover {
  border-color: var(--primary);
  background-color: var(--bg-card);
}

.action-btn i {
  @apply text-xl;
}

.action-btn span {
  @apply text-xs;
  color: var(--text-main);
}
</style>
