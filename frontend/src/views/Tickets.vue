<template>
  <div class="flex gap-6 h-full">
    <!-- Sidebar with stats -->
    <div class="w-72 flex-shrink-0">
      <div class="card p-4 mb-4">
        <h3 class="font-bold text-lg mb-4">{{ t('tickets.title') }}</h3>

        <!-- Quick Stats -->
        <div class="space-y-3 mb-4">
          <div class="p-3 rounded-lg cursor-pointer transition-all hover:translate-x-1"
               :class="filters.status === null ? 'ring-2 ring-sky-500' : ''"
               style="background-color: var(--bg-app);"
               @click="setFilter('status', null)">
            <div class="flex justify-between items-center">
              <span>{{ t('tickets.allTickets') }}</span>
              <span class="font-bold">{{ stats.total }}</span>
            </div>
          </div>

          <div class="p-3 rounded-lg cursor-pointer transition-all hover:translate-x-1"
               :class="filters.status === 'new' ? 'ring-2 ring-sky-500' : ''"
               style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(59, 130, 246, 0.1) 100%);"
               @click="setFilter('status', 'new')">
            <div class="flex justify-between items-center">
              <span class="text-blue-400">{{ t('tickets.statusNew') }}</span>
              <span class="font-bold text-blue-400">{{ stats.new }}</span>
            </div>
          </div>

          <div class="p-3 rounded-lg cursor-pointer transition-all hover:translate-x-1"
               :class="filters.status === 'open' ? 'ring-2 ring-sky-500' : ''"
               style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, rgba(245, 158, 11, 0.1) 100%);"
               @click="setFilter('status', 'open')">
            <div class="flex justify-between items-center">
              <span class="text-yellow-400">{{ t('tickets.statusOpen') }}</span>
              <span class="font-bold text-yellow-400">{{ stats.open }}</span>
            </div>
          </div>

          <div class="p-3 rounded-lg cursor-pointer transition-all hover:translate-x-1"
               :class="filters.status === 'pending' ? 'ring-2 ring-sky-500' : ''"
               style="background: linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(168, 85, 247, 0.1) 100%);"
               @click="setFilter('status', 'pending')">
            <div class="flex justify-between items-center">
              <span class="text-purple-400">{{ t('tickets.statusPending') }}</span>
              <span class="font-bold text-purple-400">{{ stats.pending }}</span>
            </div>
          </div>

          <div class="p-3 rounded-lg cursor-pointer transition-all hover:translate-x-1"
               :class="filters.status === 'resolved' ? 'ring-2 ring-sky-500' : ''"
               style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.2) 0%, rgba(34, 197, 94, 0.1) 100%);"
               @click="setFilter('status', 'resolved')">
            <div class="flex justify-between items-center">
              <span class="text-green-400">{{ t('tickets.statusResolved') }}</span>
              <span class="font-bold text-green-400">{{ stats.resolved }}</span>
            </div>
          </div>
        </div>

        <!-- SLA Breached Alert -->
        <div v-if="stats.sla_breached > 0" class="p-3 rounded-lg bg-red-900/30 border border-red-500/50 mb-4">
          <div class="flex items-center gap-2 text-red-400">
            <i class="pi pi-exclamation-triangle"></i>
            <span class="font-semibold">{{ stats.sla_breached }} {{ t('tickets.slaBreached') }}</span>
          </div>
        </div>

        <!-- Filters -->
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('tickets.filterPriority') }}</label>
            <Dropdown v-model="filters.priority" :options="priorityOptions" optionLabel="label" optionValue="value"
                      :placeholder="t('tickets.allPriorities')" showClear class="w-full" @change="loadTickets" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('tickets.filterType') }}</label>
            <Dropdown v-model="filters.ticket_type" :options="typeOptions" optionLabel="label" optionValue="value"
                      :placeholder="t('tickets.allTypes')" showClear class="w-full" @change="loadTickets" />
          </div>
          <div v-if="isAdmin" class="flex items-center gap-2">
            <Checkbox v-model="filters.my_tickets" :binary="true" inputId="myTickets" @change="loadTickets" />
            <label for="myTickets" class="text-sm cursor-pointer">{{ t('tickets.myTickets') }}</label>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 overflow-hidden">
      <div class="card h-full flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <div class="flex items-center gap-4">
            <h3 class="text-lg font-bold">{{ t('tickets.ticketsList') }}</h3>
            <span class="p-input-icon-left">
              <i class="pi pi-search" />
              <InputText v-model="filters.search" :placeholder="t('tickets.search')" class="w-64"
                         @input="debouncedSearch" />
            </span>
          </div>
          <Button :label="t('tickets.newTicket')" icon="pi pi-plus" @click="openTicketDialog()" />
        </div>

        <div class="flex-1 overflow-auto">
          <DataTable :value="tickets" stripedRows paginator :rows="15" dataKey="id" :loading="loading"
                     class="text-sm" @row-click="openTicketDetail">
            <Column field="ticket_number" :header="t('tickets.ticketNumber')" sortable style="width: 140px">
              <template #body="slotProps">
                <span class="font-mono text-sky-400 cursor-pointer hover:underline">
                  {{ slotProps.data.ticket_number }}
                </span>
              </template>
            </Column>
            <Column field="title" :header="t('tickets.ticketTitle')" sortable>
              <template #body="slotProps">
                <div class="max-w-md truncate">{{ slotProps.data.title }}</div>
              </template>
            </Column>
            <Column field="status" :header="t('tickets.ticketStatus')" sortable style="width: 120px">
              <template #body="slotProps">
                <Tag :value="t(`tickets.status${capitalize(slotProps.data.status)}`)"
                     :severity="getStatusSeverity(slotProps.data.status)" />
              </template>
            </Column>
            <Column field="priority" :header="t('tickets.ticketPriority')" sortable style="width: 100px">
              <template #body="slotProps">
                <Tag :value="t(`tickets.priority${capitalize(slotProps.data.priority)}`)"
                     :severity="getPrioritySeverity(slotProps.data.priority)" />
              </template>
            </Column>
            <Column field="ticket_type" :header="t('tickets.ticketType')" sortable style="width: 100px">
              <template #body="slotProps">
                <span class="text-sm opacity-70">{{ t(`tickets.type${capitalize(slotProps.data.ticket_type)}`) }}</span>
              </template>
            </Column>
            <Column field="requester_name" :header="t('tickets.requester')" style="width: 120px">
              <template #body="slotProps">
                <span>{{ slotProps.data.requester_name || '-' }}</span>
              </template>
            </Column>
            <Column v-if="isAdmin" field="assigned_to_name" :header="t('tickets.assignedTo')" style="width: 120px">
              <template #body="slotProps">
                <span v-if="slotProps.data.assigned_to_name">{{ slotProps.data.assigned_to_name }}</span>
                <span v-else class="opacity-50 italic">{{ t('tickets.unassigned') }}</span>
              </template>
            </Column>
            <Column field="created_at" :header="t('tickets.createdAt')" sortable style="width: 140px">
              <template #body="slotProps">
                {{ formatDateTime(slotProps.data.created_at) }}
              </template>
            </Column>
          </DataTable>
        </div>
      </div>
    </div>

    <!-- Create/Edit Ticket Dialog -->
    <Dialog v-model:visible="showTicketDialog" modal :header="editingTicket ? t('tickets.editTicket') : t('tickets.newTicket')"
            :style="{ width: '700px' }" @keydown.enter="onTicketDialogEnter">
      <div class="grid grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="block text-sm font-medium mb-1">{{ t('tickets.ticketTitle') }} <span class="text-red-500">*</span></label>
          <InputText v-model="ticketForm.title" class="w-full" />
        </div>
        <div class="col-span-2">
          <label class="block text-sm font-medium mb-1">{{ t('tickets.description') }} <span class="text-red-500">*</span></label>
          <Textarea v-model="ticketForm.description" rows="4" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('tickets.ticketType') }}</label>
          <Dropdown v-model="ticketForm.ticket_type" :options="typeOptions" optionLabel="label" optionValue="value" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('tickets.category') }}</label>
          <Dropdown v-model="ticketForm.category" :options="categoryOptions" optionLabel="label" optionValue="value"
                    class="w-full" showClear />
        </div>
        <div v-if="isAdmin">
          <label class="block text-sm font-medium mb-1">{{ t('tickets.ticketPriority') }}</label>
          <Dropdown v-model="ticketForm.priority" :options="priorityOptions" optionLabel="label" optionValue="value" class="w-full" />
        </div>
        <div v-if="isAdmin">
          <label class="block text-sm font-medium mb-1">{{ t('tickets.assignTo') }}</label>
          <Dropdown v-model="ticketForm.assigned_to_id" :options="users" optionLabel="username" optionValue="id"
                    class="w-full" showClear :placeholder="t('tickets.selectUser')" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('tickets.relatedEquipment') }}</label>
          <Dropdown v-model="ticketForm.equipment_id" :options="equipment" optionLabel="name" optionValue="id"
                    class="w-full" showClear :placeholder="t('tickets.selectEquipment')" filter />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('tickets.impact') }}</label>
          <Dropdown v-model="ticketForm.impact" :options="impactOptions" optionLabel="label" optionValue="value" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showTicketDialog = false" />
          <Button :label="t('common.save')" icon="pi pi-check" @click="saveTicket" :loading="saving" />
        </div>
      </template>
    </Dialog>

    <!-- Ticket Detail Dialog -->
    <Dialog v-model:visible="showDetailDialog" modal :header="currentTicket?.ticket_number"
            :style="{ width: '900px', maxHeight: '90vh' }" class="ticket-detail-dialog">
      <div v-if="currentTicket" class="flex gap-6">
        <!-- Main Content -->
        <div class="flex-1">
          <div class="mb-4">
            <h2 class="text-xl font-bold mb-2">{{ currentTicket.title }}</h2>
            <div class="flex gap-2 mb-4">
              <Tag :value="t(`tickets.status${capitalize(currentTicket.status)}`)"
                   :severity="getStatusSeverity(currentTicket.status)" />
              <Tag :value="t(`tickets.priority${capitalize(currentTicket.priority)}`)"
                   :severity="getPrioritySeverity(currentTicket.priority)" />
              <Tag :value="t(`tickets.type${capitalize(currentTicket.ticket_type)}`)" severity="secondary" />
            </div>
          </div>

          <!-- Description -->
          <div class="mb-6">
            <h4 class="font-semibold mb-2 opacity-70">{{ t('tickets.description') }}</h4>
            <div class="p-4 rounded-lg whitespace-pre-wrap" style="background-color: var(--bg-app);">
              {{ currentTicket.description }}
            </div>
          </div>

          <!-- Resolution -->
          <div v-if="currentTicket.resolution" class="mb-6">
            <h4 class="font-semibold mb-2 text-green-400">{{ t('tickets.resolution') }}</h4>
            <div class="p-4 rounded-lg border border-green-500/30 whitespace-pre-wrap" style="background: rgba(34, 197, 94, 0.1);">
              {{ currentTicket.resolution }}
            </div>
          </div>

          <!-- Comments -->
          <div class="mb-6">
            <h4 class="font-semibold mb-3">{{ t('tickets.comments') }} ({{ currentTicket.comments?.length || 0 }})</h4>
            <div class="space-y-3 max-h-64 overflow-auto mb-4">
              <template v-for="comment in currentTicket.comments" :key="comment.id">
                <div v-if="isAdmin || !comment.is_internal"
                     class="p-3 rounded-lg" style="background-color: var(--bg-app);"
                     :class="{ 'border-l-4 border-yellow-500': comment.is_internal }">
                  <div class="flex gap-3">
                    <!-- User Avatar -->
                    <div class="w-8 h-8 rounded-full overflow-hidden flex-shrink-0">
                      <img v-if="comment.user_avatar" :src="`/api/v1/avatars/${comment.user_avatar}`"
                           class="w-full h-full object-cover" alt="">
                      <div v-else class="w-full h-full flex items-center justify-center bg-gradient-to-br from-sky-500 to-blue-600">
                        <span class="text-xs font-bold text-white">{{ getInitials(comment.username) }}</span>
                      </div>
                    </div>
                    <!-- Comment Content -->
                    <div class="flex-1 min-w-0">
                      <div class="flex justify-between items-start mb-1">
                        <span class="font-medium">{{ comment.username || 'System' }}</span>
                        <span class="text-xs opacity-50">{{ formatDateTime(comment.created_at) }}</span>
                      </div>
                      <p class="text-sm whitespace-pre-wrap">{{ comment.content }}</p>
                      <div v-if="comment.is_internal" class="mt-2">
                        <Tag value="Internal" severity="warning" class="text-xs" />
                      </div>
                    </div>
                  </div>
                </div>
              </template>
              <div v-if="!currentTicket.comments?.length || (!isAdmin && currentTicket.comments?.every(c => c.is_internal))" class="text-center py-4 opacity-50">
                {{ t('tickets.noComments') }}
              </div>
            </div>

            <!-- Add Comment -->
            <div class="border-t pt-4" style="border-color: var(--border-color);">
              <Textarea v-model="newComment" :placeholder="t('tickets.addComment')" rows="2" class="w-full mb-2" />
              <div class="flex justify-between items-center">
                <div v-if="isAdmin" class="flex items-center gap-2">
                  <Checkbox v-model="commentInternal" :binary="true" inputId="internal" />
                  <label for="internal" class="text-sm cursor-pointer">{{ t('tickets.internalNote') }}</label>
                </div>
                <div v-else></div>
                <Button :label="t('tickets.postComment')" icon="pi pi-send" size="small"
                        @click="postComment" :disabled="!newComment.trim()" />
              </div>
            </div>
          </div>

          <!-- History -->
          <div>
            <h4 class="font-semibold mb-3 opacity-70">{{ t('tickets.history') }}</h4>
            <div class="space-y-2 max-h-48 overflow-auto">
              <div v-for="item in currentTicket.history" :key="item.id"
                   class="flex items-center gap-3 text-sm py-2 border-b" style="border-color: var(--border-color);">
                <i class="pi pi-circle-fill text-xs text-sky-500"></i>
                <span class="opacity-50">{{ formatDateTime(item.created_at) }}</span>
                <span>{{ item.username || 'System' }}</span>
                <span class="opacity-70">{{ formatHistoryAction(item) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar Info -->
        <div class="w-64 flex-shrink-0">
          <div class="space-y-4">
            <!-- Status Actions (Admin only) -->
            <div v-if="isAdmin" class="p-4 rounded-lg" style="background-color: var(--bg-app);">
              <h4 class="font-semibold mb-3">{{ t('tickets.actions') }}</h4>
              <div class="space-y-2">
                <Button v-if="currentTicket.status === 'new' || currentTicket.status === 'pending'"
                        :label="t('tickets.markOpen')" icon="pi pi-play" class="w-full" size="small"
                        @click="updateStatus('open')" />
                <Button v-if="currentTicket.status !== 'resolved' && currentTicket.status !== 'closed'"
                        :label="t('tickets.markPending')" icon="pi pi-pause" class="w-full" size="small" severity="warning"
                        @click="updateStatus('pending')" />
                <Button v-if="currentTicket.status !== 'resolved' && currentTicket.status !== 'closed'"
                        :label="t('tickets.resolve')" icon="pi pi-check" class="w-full" size="small" severity="success"
                        @click="showResolveDialog = true" />
                <Button v-if="currentTicket.status === 'resolved'"
                        :label="t('tickets.close')" icon="pi pi-lock" class="w-full" size="small"
                        @click="closeCurrentTicket" />
                <Button v-if="currentTicket.status === 'resolved' || currentTicket.status === 'closed'"
                        :label="t('tickets.reopen')" icon="pi pi-refresh" class="w-full" size="small" severity="danger"
                        @click="reopenCurrentTicket" />
              </div>
            </div>

            <!-- Ticket Info -->
            <div class="p-4 rounded-lg space-y-3" style="background-color: var(--bg-app);">
              <div>
                <span class="text-xs opacity-50 block">{{ t('tickets.requester') }}</span>
                <span>{{ currentTicket.requester_name || '-' }}</span>
              </div>
              <div v-if="isAdmin">
                <span class="text-xs opacity-50 block">{{ t('tickets.assignedTo') }}</span>
                <div class="flex items-center gap-2">
                  <span>{{ currentTicket.assigned_to_name || t('tickets.unassigned') }}</span>
                  <Button icon="pi pi-pencil" text rounded size="small" @click="showAssignDialog = true" />
                </div>
              </div>
              <div v-if="currentTicket.equipment_name">
                <span class="text-xs opacity-50 block">{{ t('tickets.relatedEquipment') }}</span>
                <span>{{ currentTicket.equipment_name }}</span>
              </div>
              <div v-if="currentTicket.category">
                <span class="text-xs opacity-50 block">{{ t('tickets.category') }}</span>
                <span>{{ currentTicket.category }}</span>
              </div>
              <div>
                <span class="text-xs opacity-50 block">{{ t('tickets.createdAt') }}</span>
                <span>{{ formatDateTime(currentTicket.created_at) }}</span>
              </div>
              <div v-if="currentTicket.sla_due_date">
                <span class="text-xs opacity-50 block">{{ t('tickets.slaDue') }}</span>
                <span :class="{ 'text-red-400': new Date(currentTicket.sla_due_date) < new Date() }">
                  {{ formatDateTime(currentTicket.sla_due_date) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Dialog>

    <!-- Resolve Dialog -->
    <Dialog v-model:visible="showResolveDialog" modal :header="t('tickets.resolveTicket')" :style="{ width: '500px' }"
            @keydown.enter="resolveCurrentTicket">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('tickets.resolution') }} <span class="text-red-500">*</span></label>
          <Textarea v-model="resolutionText" rows="4" class="w-full" :placeholder="t('tickets.resolutionPlaceholder')" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('tickets.resolutionCode') }}</label>
          <Dropdown v-model="resolutionCode" :options="resolutionCodes" optionLabel="label" optionValue="value" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showResolveDialog = false" />
          <Button :label="t('tickets.resolve')" icon="pi pi-check" severity="success" @click="resolveCurrentTicket"
                  :disabled="!resolutionText.trim()" />
        </div>
      </template>
    </Dialog>

    <!-- Assign Dialog -->
    <Dialog v-model:visible="showAssignDialog" modal :header="t('tickets.assignTicket')" :style="{ width: '400px' }"
            @keydown.enter="assignCurrentTicket">
      <div>
        <label class="block text-sm font-medium mb-1">{{ t('tickets.assignTo') }}</label>
        <Dropdown v-model="assignToUserId" :options="users" optionLabel="username" optionValue="id"
                  class="w-full" :placeholder="t('tickets.selectUser')" />
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showAssignDialog = false" />
          <Button :label="t('tickets.assign')" icon="pi pi-user" @click="assignCurrentTicket" :disabled="!assignToUserId" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useI18n } from 'vue-i18n';
import { useTicketsStore } from '../stores/tickets';
import api from '../api';

const route = useRoute();
const router = useRouter();

const { t } = useI18n();
const toast = useToast();
const ticketsStore = useTicketsStore();

// User info for permission checks
const currentUser = computed(() => {
  const userStr = localStorage.getItem('user');
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch (e) {
      return null;
    }
  }
  return null;
});

const isAdmin = computed(() => currentUser.value?.role === 'admin');

// State
const tickets = ref([]);
const stats = ref({ total: 0, new: 0, open: 0, pending: 0, resolved: 0, closed: 0, sla_breached: 0 });
const currentTicket = ref(null);
const users = ref([]);
const equipment = ref([]);
const loading = ref(false);
const saving = ref(false);

// Filters
const filters = ref({
  status: null,
  priority: null,
  ticket_type: null,
  category: null,
  search: '',
  my_tickets: false
});

// Dialogs
const showTicketDialog = ref(false);
const showDetailDialog = ref(false);
const showResolveDialog = ref(false);
const showAssignDialog = ref(false);

// Forms
const editingTicket = ref(null);
const ticketForm = ref({
  title: '',
  description: '',
  ticket_type: 'incident',
  category: null,
  priority: 'medium',
  impact: 'medium',
  urgency: 'medium',
  assigned_to_id: null,
  equipment_id: null
});

const newComment = ref('');
const commentInternal = ref(false);
const resolutionText = ref('');
const resolutionCode = ref('fixed');
const assignToUserId = ref(null);

// Options
const priorityOptions = [
  { label: t('tickets.priorityCritical'), value: 'critical' },
  { label: t('tickets.priorityHigh'), value: 'high' },
  { label: t('tickets.priorityMedium'), value: 'medium' },
  { label: t('tickets.priorityLow'), value: 'low' }
];

const typeOptions = [
  { label: t('tickets.typeIncident'), value: 'incident' },
  { label: t('tickets.typeRequest'), value: 'request' },
  { label: t('tickets.typeProblem'), value: 'problem' },
  { label: t('tickets.typeChange'), value: 'change' }
];

const categoryOptions = [
  { label: t('tickets.categoryHardware'), value: 'hardware' },
  { label: t('tickets.categorySoftware'), value: 'software' },
  { label: t('tickets.categoryNetwork'), value: 'network' },
  { label: t('tickets.categoryAccess'), value: 'access' },
  { label: t('tickets.categoryOther'), value: 'other' }
];

const impactOptions = [
  { label: t('tickets.impactHigh'), value: 'high' },
  { label: t('tickets.impactMedium'), value: 'medium' },
  { label: t('tickets.impactLow'), value: 'low' }
];

const resolutionCodes = [
  { label: t('tickets.codeFixed'), value: 'fixed' },
  { label: t('tickets.codeWorkaround'), value: 'workaround' },
  { label: t('tickets.codeCannotReproduce'), value: 'cannot_reproduce' },
  { label: t('tickets.codeDuplicate'), value: 'duplicate' },
  { label: t('tickets.codeUserError'), value: 'user_error' }
];

// Helpers
const capitalize = (str) => str ? str.charAt(0).toUpperCase() + str.slice(1) : '';

const getInitials = (name) => {
  if (!name) return '?';
  return name.substring(0, 2).toUpperCase();
};

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString();
};

const getStatusSeverity = (status) => {
  switch (status) {
    case 'new': return 'info';
    case 'open': return 'warning';
    case 'pending': return 'secondary';
    case 'resolved': return 'success';
    case 'closed': return 'contrast';
    default: return null;
  }
};

const getPrioritySeverity = (priority) => {
  switch (priority) {
    case 'critical': return 'danger';
    case 'high': return 'warning';
    case 'medium': return 'info';
    case 'low': return 'success';
    default: return null;
  }
};

const formatHistoryAction = (item) => {
  if (item.action === 'created') return t('tickets.historyCreated');
  if (item.action === 'commented') return t('tickets.historyCommented');
  if (item.action === 'resolved') return t('tickets.historyResolved');
  if (item.action === 'closed') return t('tickets.historyClosed');
  if (item.action === 'reopened') return t('tickets.historyReopened');
  if (item.action === 'assigned') return `${t('tickets.historyAssigned')} ${item.new_value || ''}`;
  if (item.action === 'status_changed') return `${t('tickets.historyStatusChanged')} ${item.old_value} → ${item.new_value}`;
  if (item.action === 'updated') return `${t('tickets.historyUpdated')} ${item.field_name}`;
  return item.action;
};

// Debounced search
let searchTimeout = null;
const debouncedSearch = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => loadTickets(), 300);
};

// Data loading
const loadTickets = async () => {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    if (filters.value.status) params.append('status', filters.value.status);
    if (filters.value.priority) params.append('priority', filters.value.priority);
    if (filters.value.ticket_type) params.append('ticket_type', filters.value.ticket_type);
    if (filters.value.search) params.append('search', filters.value.search);
    if (filters.value.my_tickets) params.append('my_tickets', 'true');

    const [ticketsRes, statsRes] = await Promise.all([
      api.get(`/tickets/?${params}`),
      api.get('/tickets/stats')
    ]);
    tickets.value = ticketsRes.data;
    stats.value = statsRes.data;
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || 'Failed to load tickets' });
  } finally {
    loading.value = false;
  }
};

const loadReferenceData = async () => {
  try {
    const [usersRes, equipmentRes] = await Promise.all([
      api.get('/users/'),
      api.get('/inventory/equipment/')
    ]);
    users.value = usersRes.data;
    equipment.value = equipmentRes.data;
  } catch (e) {
    console.error('Failed to load reference data:', e);
  }
};

const setFilter = (key, value) => {
  filters.value[key] = value;
  loadTickets();
};

// Ticket CRUD
const openTicketDialog = (ticket = null) => {
  editingTicket.value = ticket;
  if (ticket) {
    ticketForm.value = { ...ticket };
  } else {
    ticketForm.value = {
      title: '',
      description: '',
      ticket_type: 'incident',
      category: null,
      priority: 'medium',
      impact: 'medium',
      urgency: 'medium',
      assigned_to_id: null,
      equipment_id: null
    };
  }
  showTicketDialog.value = true;
};

const saveTicket = async () => {
  if (!ticketForm.value.title || !ticketForm.value.description) {
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.fillRequiredFields') });
    return;
  }
  saving.value = true;
  try {
    if (editingTicket.value) {
      await api.put(`/tickets/${editingTicket.value.id}`, ticketForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('tickets.ticketUpdated') });
    } else {
      await api.post('/tickets/', ticketForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('tickets.ticketCreated') });
    }
    showTicketDialog.value = false;
    loadTickets();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  } finally {
    saving.value = false;
  }
};

const onTicketDialogEnter = (event) => {
  if (event.target.tagName !== 'TEXTAREA') {
    event.preventDefault();
    saveTicket();
  }
};

// Ticket detail
const openTicketDetail = async (event) => {
  try {
    const response = await api.get(`/tickets/${event.data.id}`);
    currentTicket.value = response.data;
    showDetailDialog.value = true;
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || 'Failed to load ticket' });
  }
};

// Open ticket by ID (used when coming from notifications)
const openTicketById = async (ticketId) => {
  try {
    const response = await api.get(`/tickets/${ticketId}`);
    currentTicket.value = response.data;
    showDetailDialog.value = true;
    // Clear the query param after opening
    router.replace({ path: '/tickets', query: {} });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || 'Failed to load ticket' });
  }
};

const refreshCurrentTicket = async () => {
  if (currentTicket.value) {
    const response = await api.get(`/tickets/${currentTicket.value.id}`);
    currentTicket.value = response.data;
  }
};

// Actions
const updateStatus = async (newStatus) => {
  try {
    await api.put(`/tickets/${currentTicket.value.id}`, { status: newStatus });
    await refreshCurrentTicket();
    loadTickets();
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('tickets.statusUpdated') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail });
  }
};

const postComment = async () => {
  if (!newComment.value.trim()) return;
  try {
    await api.post(`/tickets/${currentTicket.value.id}/comments`, {
      content: newComment.value,
      is_internal: commentInternal.value
    });
    newComment.value = '';
    commentInternal.value = false;
    await refreshCurrentTicket();
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('tickets.commentAdded') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail });
  }
};

const resolveCurrentTicket = async () => {
  if (!resolutionText.value.trim()) return;
  try {
    await api.post(`/tickets/${currentTicket.value.id}/resolve?resolution=${encodeURIComponent(resolutionText.value)}&resolution_code=${resolutionCode.value}`);
    showResolveDialog.value = false;
    resolutionText.value = '';
    resolutionCode.value = 'fixed';
    await refreshCurrentTicket();
    loadTickets();
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('tickets.ticketResolved') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail });
  }
};

const closeCurrentTicket = async () => {
  try {
    await api.post(`/tickets/${currentTicket.value.id}/close`);
    await refreshCurrentTicket();
    loadTickets();
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('tickets.ticketClosed') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail });
  }
};

const reopenCurrentTicket = async () => {
  try {
    await api.post(`/tickets/${currentTicket.value.id}/reopen`);
    await refreshCurrentTicket();
    loadTickets();
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('tickets.ticketReopened') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail });
  }
};

const assignCurrentTicket = async () => {
  if (!assignToUserId.value) return;
  try {
    await api.post(`/tickets/${currentTicket.value.id}/assign?user_id=${assignToUserId.value}`);
    showAssignDialog.value = false;
    assignToUserId.value = null;
    await refreshCurrentTicket();
    loadTickets();
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('tickets.ticketAssigned') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail });
  }
};

onMounted(async () => {
  await loadTickets();
  loadReferenceData();

  // Check if there's a ticket ID in the URL query params (from notification click)
  const ticketId = route.query.id;
  if (ticketId) {
    openTicketById(ticketId);
  }
});
</script>

<style scoped>
.ticket-detail-dialog :deep(.p-dialog-content) {
  overflow-y: auto;
}
</style>
