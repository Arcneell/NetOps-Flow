<template>
  <div class="flex gap-6 h-full">
    <!-- Sidebar with alerts -->
    <div class="w-72 flex-shrink-0">
      <div class="card p-4 mb-4">
        <h3 class="font-bold text-lg mb-4">{{ t('contracts').value }}</h3>

        <!-- Expiring Alerts -->
        <div v-if="expiringAlerts.length" class="mb-4">
          <h4 class="text-sm font-semibold opacity-70 mb-2">{{ t('expiringContracts').value }}</h4>
          <div v-for="alert in expiringAlerts" :key="alert.item_id"
               class="p-3 rounded-lg mb-2 text-sm"
               :class="[
                 alert.severity === 'critical' ? 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200' :
                 alert.severity === 'warning' ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200' :
                 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200'
               ]">
            <div class="font-medium">{{ alert.item_name }}</div>
            <div class="opacity-70">{{ alert.days_remaining }} {{ t('daysRemaining').value }}</div>
          </div>
        </div>

        <!-- Filter by Type -->
        <div>
          <label class="block text-sm font-medium mb-2">{{ t('filterByType').value }}</label>
          <Dropdown v-model="filterType" :options="contractTypeOptions" optionLabel="label" optionValue="value" :placeholder="t('allTypes').value" showClear class="w-full" />
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="card p-4">
        <h4 class="text-sm font-semibold opacity-70 mb-3">{{ t('overview').value }}</h4>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span>{{ t('totalContracts').value }}</span>
            <span class="font-bold">{{ contracts.length }}</span>
          </div>
          <div class="flex justify-between">
            <span>{{ t('activeContracts').value }}</span>
            <span class="font-bold text-green-500">{{ activeContracts.length }}</span>
          </div>
          <div class="flex justify-between">
            <span>{{ t('expiringSoon').value }}</span>
            <span class="font-bold text-yellow-500">{{ expiringAlerts.length }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 overflow-hidden">
      <div class="card h-full flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('contractsList').value }}</h3>
          <Button :label="t('newContract').value" icon="pi pi-plus" @click="openContractDialog()" />
        </div>

        <div class="flex-1 overflow-auto">
          <DataTable :value="filteredContracts" stripedRows paginator :rows="10" v-model:expandedRows="expandedRows" dataKey="id" class="text-sm">
            <Column expander style="width: 3rem" />
            <Column field="name" :header="t('name').value" sortable></Column>
            <Column field="contract_type" :header="t('type').value">
              <template #body="slotProps">
                <Tag :value="slotProps.data.contract_type" :severity="getTypeSeverity(slotProps.data.contract_type)" />
              </template>
            </Column>
            <Column field="contract_number" :header="t('contractNumber').value"></Column>
            <Column :header="t('supplier').value">
              <template #body="slotProps">{{ slotProps.data.supplier?.name || '-' }}</template>
            </Column>
            <Column :header="t('period').value">
              <template #body="slotProps">
                {{ formatDate(slotProps.data.start_date) }} - {{ formatDate(slotProps.data.end_date) }}
              </template>
            </Column>
            <Column field="annual_cost" :header="t('annualCost').value">
              <template #body="slotProps">
                {{ slotProps.data.annual_cost ? formatCurrency(slotProps.data.annual_cost) : '-' }}
              </template>
            </Column>
            <Column :header="t('status').value">
              <template #body="slotProps">
                <Tag :value="getContractStatus(slotProps.data)" :severity="getStatusSeverity(slotProps.data)" />
              </template>
            </Column>
            <Column :header="t('actions').value" style="width: 100px">
              <template #body="slotProps">
                <div class="flex gap-1">
                  <Button icon="pi pi-pencil" text rounded size="small" @click="openContractDialog(slotProps.data)" />
                  <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="confirmDeleteContract(slotProps.data)" />
                </div>
              </template>
            </Column>

            <template #expansion="slotProps">
              <div class="p-4 grid grid-cols-2 gap-6" style="background-color: var(--bg-app);">
                <div>
                  <h4 class="font-semibold mb-3 text-blue-500">{{ t('details').value }}</h4>
                  <p class="mb-2"><span class="opacity-60">{{ t('renewalType').value }}:</span> {{ slotProps.data.renewal_type }}</p>
                  <p class="mb-2"><span class="opacity-60">{{ t('renewalNotice').value }}:</span> {{ slotProps.data.renewal_notice_days }} {{ t('days').value }}</p>
                  <p><span class="opacity-60">{{ t('notes').value }}:</span> {{ slotProps.data.notes || '-' }}</p>
                </div>
                <div>
                  <h4 class="font-semibold mb-3 text-blue-500">{{ t('coveredEquipment').value }}</h4>
                  <Button :label="t('manageEquipment').value" icon="pi pi-link" size="small" @click="openEquipmentDialog(slotProps.data)" />
                </div>
              </div>
            </template>
          </DataTable>
        </div>
      </div>
    </div>

    <!-- Contract Dialog -->
    <Dialog v-model:visible="showContractDialog" modal :header="editingContract ? t('editContract').value : t('newContract').value" :style="{ width: '600px' }">
      <div class="grid grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="block text-sm font-medium mb-1">{{ t('name').value }} <span class="text-red-500">*</span></label>
          <InputText v-model="contractForm.name" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('type').value }} <span class="text-red-500">*</span></label>
          <Dropdown v-model="contractForm.contract_type" :options="contractTypeOptions" optionLabel="label" optionValue="value" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('contractNumber').value }}</label>
          <InputText v-model="contractForm.contract_number" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('supplier').value }}</label>
          <Dropdown v-model="contractForm.supplier_id" :options="suppliers" optionLabel="name" optionValue="id" class="w-full" showClear />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('annualCost').value }}</label>
          <InputNumber v-model="contractForm.annual_cost" class="w-full" mode="currency" currency="EUR" locale="fr-FR" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('startDate').value }} <span class="text-red-500">*</span></label>
          <Calendar v-model="contractForm.start_date" dateFormat="yy-mm-dd" class="w-full" showIcon />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('endDate').value }} <span class="text-red-500">*</span></label>
          <Calendar v-model="contractForm.end_date" dateFormat="yy-mm-dd" class="w-full" showIcon />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('renewalType').value }}</label>
          <Dropdown v-model="contractForm.renewal_type" :options="renewalOptions" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('renewalNoticeDays').value }}</label>
          <InputNumber v-model="contractForm.renewal_notice_days" class="w-full" :min="0" suffix=" days" />
        </div>
        <div class="col-span-2">
          <label class="block text-sm font-medium mb-1">{{ t('notes').value }}</label>
          <Textarea v-model="contractForm.notes" rows="2" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('cancel').value" severity="secondary" outlined @click="showContractDialog = false" />
          <Button :label="t('save').value" icon="pi pi-check" @click="saveContract" />
        </div>
      </template>
    </Dialog>

    <!-- Equipment Linking Dialog -->
    <Dialog v-model:visible="showEquipmentDialog" modal :header="t('manageEquipment').value" :style="{ width: '600px' }">
      <div v-if="selectedContract">
        <div class="p-3 rounded-lg mb-4" style="background-color: var(--bg-app);">
          <span class="opacity-60">{{ t('contract').value }}:</span>
          <strong class="ml-2">{{ selectedContract.name }}</strong>
        </div>

        <div v-if="contractEquipment.length" class="mb-4">
          <h4 class="font-semibold mb-2">{{ t('linkedEquipment').value }}</h4>
          <div v-for="eq in contractEquipment" :key="eq.id" class="flex items-center justify-between p-3 rounded-lg mb-2" style="background-color: var(--bg-app);">
            <div>
              <span class="font-medium">{{ eq.name }}</span>
              <span v-if="eq.serial_number" class="ml-2 opacity-60 text-sm">({{ eq.serial_number }})</span>
            </div>
            <Button icon="pi pi-times" text rounded size="small" severity="danger" @click="unlinkEquipment(eq.id)" />
          </div>
        </div>

        <div>
          <h4 class="font-semibold mb-2">{{ t('addEquipment').value }}</h4>
          <div class="flex gap-2">
            <Dropdown v-model="selectedEquipmentToLink" :options="availableEquipment" optionLabel="name" optionValue="id" :placeholder="t('selectEquipment').value" class="flex-1" showClear />
            <Button icon="pi pi-plus" @click="linkEquipment" :disabled="!selectedEquipmentToLink" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button :label="t('close').value" @click="showEquipmentDialog = false" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '../api';
import { t } from '../i18n';

const toast = useToast();

// Data
const contracts = ref([]);
const suppliers = ref([]);
const equipment = ref([]);
const expiringAlerts = ref([]);
const contractEquipment = ref([]);
const expandedRows = ref({});

// Filters
const filterType = ref(null);

// Dialogs
const showContractDialog = ref(false);
const showEquipmentDialog = ref(false);

// Editing states
const editingContract = ref(null);
const selectedContract = ref(null);
const selectedEquipmentToLink = ref(null);

// Forms
const contractForm = ref({
  name: '', contract_type: 'maintenance', contract_number: '', supplier_id: null,
  start_date: null, end_date: null, annual_cost: null, renewal_type: 'manual',
  renewal_notice_days: 30, notes: ''
});

// Options
const contractTypeOptions = [
  { label: 'Maintenance', value: 'maintenance' },
  { label: 'Assurance', value: 'insurance' },
  { label: 'Leasing', value: 'leasing' },
  { label: 'Support', value: 'support' }
];

const renewalOptions = ['auto', 'manual', 'none'];

// Computed
const activeContracts = computed(() => {
  const today = new Date().toISOString().split('T')[0];
  return contracts.value.filter(c => c.start_date <= today && c.end_date >= today);
});

const filteredContracts = computed(() => {
  if (!filterType.value) return contracts.value;
  return contracts.value.filter(c => c.contract_type === filterType.value);
});

const availableEquipment = computed(() => {
  const linkedIds = contractEquipment.value.map(e => e.id);
  return equipment.value.filter(e => !linkedIds.includes(e.id));
});

// Helpers
const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString();
};

const formatCurrency = (value) => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(value);
};

const getTypeSeverity = (type) => {
  switch (type) {
    case 'maintenance': return 'info';
    case 'insurance': return 'warning';
    case 'leasing': return 'success';
    case 'support': return 'secondary';
    default: return null;
  }
};

const getContractStatus = (contract) => {
  const today = new Date().toISOString().split('T')[0];
  if (contract.end_date < today) return 'expired';
  if (contract.start_date > today) return 'future';
  return 'active';
};

const getStatusSeverity = (contract) => {
  const status = getContractStatus(contract);
  switch (status) {
    case 'active': return 'success';
    case 'expired': return 'danger';
    case 'future': return 'info';
    default: return null;
  }
};

// Data loading
const loadData = async () => {
  try {
    const [contractsRes, suppliersRes, equipmentRes, alertsRes] = await Promise.all([
      api.get('/contracts/', { params: { active_only: false } }),
      api.get('/inventory/suppliers/'),
      api.get('/inventory/equipment/'),
      api.get('/contracts/expiring', { params: { days: 30 } })
    ]);
    contracts.value = contractsRes.data;
    suppliers.value = suppliersRes.data;
    equipment.value = equipmentRes.data;
    expiringAlerts.value = alertsRes.data;
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || 'Failed to load data' });
  }
};

// Contract CRUD
const openContractDialog = (contract = null) => {
  editingContract.value = contract;
  if (contract) {
    contractForm.value = {
      ...contract,
      start_date: contract.start_date ? new Date(contract.start_date) : null,
      end_date: contract.end_date ? new Date(contract.end_date) : null
    };
  } else {
    contractForm.value = {
      name: '', contract_type: 'maintenance', contract_number: '', supplier_id: null,
      start_date: null, end_date: null, annual_cost: null, renewal_type: 'manual',
      renewal_notice_days: 30, notes: ''
    };
  }
  showContractDialog.value = true;
};

const saveContract = async () => {
  if (!contractForm.value.name || !contractForm.value.contract_type || !contractForm.value.start_date || !contractForm.value.end_date) {
    toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('fillRequiredFields').value });
    return;
  }
  try {
    const data = {
      ...contractForm.value,
      start_date: contractForm.value.start_date instanceof Date ? contractForm.value.start_date.toISOString().split('T')[0] : contractForm.value.start_date,
      end_date: contractForm.value.end_date instanceof Date ? contractForm.value.end_date.toISOString().split('T')[0] : contractForm.value.end_date
    };

    if (editingContract.value) {
      await api.put(`/contracts/${editingContract.value.id}`, data);
      toast.add({ severity: 'success', summary: t('success').value, detail: t('contractUpdated').value });
    } else {
      await api.post('/contracts/', data);
      toast.add({ severity: 'success', summary: t('success').value, detail: t('contractCreated').value });
    }
    showContractDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const confirmDeleteContract = async (contract) => {
  if (!confirm(t('confirmDeleteItem').value)) return;
  try {
    await api.delete(`/contracts/${contract.id}`);
    toast.add({ severity: 'success', summary: t('deleted').value, detail: t('contractDeleted').value });
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

// Equipment linking
const openEquipmentDialog = async (contract) => {
  selectedContract.value = contract;
  selectedEquipmentToLink.value = null;
  try {
    const response = await api.get(`/contracts/${contract.id}/equipment`);
    contractEquipment.value = response.data.equipment;
  } catch (e) {
    contractEquipment.value = [];
  }
  showEquipmentDialog.value = true;
};

const linkEquipment = async () => {
  if (!selectedEquipmentToLink.value) return;
  try {
    await api.post(`/contracts/${selectedContract.value.id}/equipment/${selectedEquipmentToLink.value}`);
    const response = await api.get(`/contracts/${selectedContract.value.id}/equipment`);
    contractEquipment.value = response.data.equipment;
    selectedEquipmentToLink.value = null;
    toast.add({ severity: 'success', summary: t('success').value, detail: t('equipmentLinked').value });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const unlinkEquipment = async (equipmentId) => {
  try {
    await api.delete(`/contracts/${selectedContract.value.id}/equipment/${equipmentId}`);
    contractEquipment.value = contractEquipment.value.filter(e => e.id !== equipmentId);
    toast.add({ severity: 'success', summary: t('success').value, detail: t('equipmentUnlinked').value });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

onMounted(loadData);
</script>
