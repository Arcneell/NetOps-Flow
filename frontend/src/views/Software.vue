<template>
  <div class="flex gap-6 h-full">
    <!-- Sidebar with compliance -->
    <div class="w-72 flex-shrink-0">
      <div class="card p-4 mb-4">
        <h3 class="font-bold text-lg mb-4">{{ t('software').value }}</h3>

        <!-- Compliance Overview -->
        <div v-if="complianceOverview" class="mb-4">
          <h4 class="text-sm font-semibold opacity-70 mb-3">{{ t('licenseCompliance').value }}</h4>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="p-2 rounded bg-green-100 dark:bg-green-900">
              <div class="text-xl font-bold text-green-600 dark:text-green-400">{{ complianceOverview.compliant }}</div>
              <div class="text-xs opacity-70">{{ t('compliant').value }}</div>
            </div>
            <div class="p-2 rounded bg-yellow-100 dark:bg-yellow-900">
              <div class="text-xl font-bold text-yellow-600 dark:text-yellow-400">{{ complianceOverview.warning }}</div>
              <div class="text-xs opacity-70">{{ t('warning').value }}</div>
            </div>
            <div class="p-2 rounded bg-red-100 dark:bg-red-900">
              <div class="text-xl font-bold text-red-600 dark:text-red-400">{{ complianceOverview.violation }}</div>
              <div class="text-xs opacity-70">{{ t('violation').value }}</div>
            </div>
          </div>
        </div>

        <!-- Violations List -->
        <div v-if="complianceOverview?.violations?.length" class="mb-4">
          <h4 class="text-sm font-semibold opacity-70 mb-2">{{ t('violations').value }}</h4>
          <div v-for="v in complianceOverview.violations" :key="v.software_id"
               class="p-2 rounded-lg mb-2 text-sm bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200">
            <div class="font-medium">{{ v.software_name }}</div>
            <div class="opacity-70">{{ v.installed }}/{{ v.licensed }} (+{{ v.over_by }})</div>
          </div>
        </div>

        <!-- Filter by Category -->
        <div>
          <label class="block text-sm font-medium mb-2">{{ t('filterByCategory').value }}</label>
          <Dropdown v-model="filterCategory" :options="categoryOptions" :placeholder="t('allCategories').value" showClear class="w-full" />
        </div>
      </div>

      <!-- Expiring Licenses -->
      <div v-if="expiringLicenses.length" class="card p-4">
        <h4 class="text-sm font-semibold opacity-70 mb-3">{{ t('expiringLicenses').value }}</h4>
        <div v-for="alert in expiringLicenses" :key="alert.item_id"
             class="p-2 rounded-lg mb-2 text-sm"
             :class="[
               alert.severity === 'critical' ? 'bg-red-100 dark:bg-red-900' :
               alert.severity === 'warning' ? 'bg-yellow-100 dark:bg-yellow-900' :
               'bg-blue-100 dark:bg-blue-900'
             ]">
          <div class="font-medium">{{ alert.item_name }}</div>
          <div class="opacity-70">{{ alert.days_remaining }} {{ t('daysRemaining').value }}</div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 overflow-hidden">
      <div class="card h-full flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('softwareCatalog').value }}</h3>
          <Button :label="t('newSoftware').value" icon="pi pi-plus" @click="openSoftwareDialog()" />
        </div>

        <div class="flex-1 overflow-auto">
          <DataTable :value="filteredSoftware" stripedRows paginator :rows="10" v-model:expandedRows="expandedRows" dataKey="id" class="text-sm">
            <Column expander style="width: 3rem" />
            <Column field="name" :header="t('name').value" sortable></Column>
            <Column field="publisher" :header="t('publisher').value"></Column>
            <Column field="version" :header="t('version').value" style="width: 100px"></Column>
            <Column field="category" :header="t('category').value">
              <template #body="slotProps">
                <Tag v-if="slotProps.data.category" :value="slotProps.data.category" />
                <span v-else class="opacity-50">-</span>
              </template>
            </Column>
            <Column :header="t('licenses').value" style="width: 100px">
              <template #body="slotProps">{{ slotProps.data.total_licenses }}</template>
            </Column>
            <Column :header="t('installations').value" style="width: 100px">
              <template #body="slotProps">{{ slotProps.data.total_installations }}</template>
            </Column>
            <Column :header="t('compliance').value" style="width: 120px">
              <template #body="slotProps">
                <Tag :value="slotProps.data.compliance_status" :severity="getComplianceSeverity(slotProps.data.compliance_status)" />
              </template>
            </Column>
            <Column :header="t('actions').value" style="width: 120px">
              <template #body="slotProps">
                <div class="flex gap-1">
                  <Button icon="pi pi-key" text rounded size="small" @click="openLicensesDialog(slotProps.data)" v-tooltip.top="t('manageLicenses').value" />
                  <Button icon="pi pi-pencil" text rounded size="small" @click="openSoftwareDialog(slotProps.data)" />
                  <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="confirmDeleteSoftware(slotProps.data)" />
                </div>
              </template>
            </Column>

            <template #expansion="slotProps">
              <div class="p-4 grid grid-cols-2 gap-6" style="background-color: var(--bg-app);">
                <div>
                  <h4 class="font-semibold mb-3 text-blue-500">{{ t('details').value }}</h4>
                  <p class="mb-2"><span class="opacity-60">{{ t('publisher').value }}:</span> {{ slotProps.data.publisher || '-' }}</p>
                  <p class="mb-2"><span class="opacity-60">{{ t('category').value }}:</span> {{ slotProps.data.category || '-' }}</p>
                  <p><span class="opacity-60">{{ t('notes').value }}:</span> {{ slotProps.data.notes || '-' }}</p>
                </div>
                <div>
                  <h4 class="font-semibold mb-3 text-blue-500">{{ t('installations').value }}</h4>
                  <Button :label="t('viewInstallations').value" icon="pi pi-desktop" size="small" @click="openInstallationsDialog(slotProps.data)" />
                </div>
              </div>
            </template>
          </DataTable>
        </div>
      </div>
    </div>

    <!-- Software Dialog -->
    <Dialog v-model:visible="showSoftwareDialog" modal :header="editingSoftware ? t('editSoftware').value : t('newSoftware').value" :style="{ width: '500px' }">
      <div class="flex flex-col gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('name').value }} <span class="text-red-500">*</span></label>
          <InputText v-model="softwareForm.name" class="w-full" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('publisher').value }}</label>
            <InputText v-model="softwareForm.publisher" class="w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('version').value }}</label>
            <InputText v-model="softwareForm.version" class="w-full" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('category').value }}</label>
          <Dropdown v-model="softwareForm.category" :options="categoryOptions" class="w-full" showClear />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('notes').value }}</label>
          <Textarea v-model="softwareForm.notes" rows="2" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('cancel').value" severity="secondary" outlined @click="showSoftwareDialog = false" />
          <Button :label="t('save').value" icon="pi pi-check" @click="saveSoftware" />
        </div>
      </template>
    </Dialog>

    <!-- Licenses Dialog -->
    <Dialog v-model:visible="showLicensesDialog" modal :header="t('manageLicenses').value" :style="{ width: '700px' }">
      <div v-if="selectedSoftware">
        <div class="p-3 rounded-lg mb-4 flex justify-between items-center" style="background-color: var(--bg-app);">
          <div>
            <span class="opacity-60">{{ t('software').value }}:</span>
            <strong class="ml-2">{{ selectedSoftware.name }}</strong>
          </div>
          <Button :label="t('addLicense').value" icon="pi pi-plus" size="small" @click="openLicenseForm()" />
        </div>

        <DataTable :value="licenses" class="text-sm" stripedRows>
          <Column field="license_type" :header="t('type').value">
            <template #body="slotProps">
              <Tag :value="slotProps.data.license_type" />
            </template>
          </Column>
          <Column field="quantity" :header="t('quantity').value" style="width: 100px"></Column>
          <Column :header="t('purchaseDate').value">
            <template #body="slotProps">{{ formatDate(slotProps.data.purchase_date) }}</template>
          </Column>
          <Column :header="t('expiryDate').value">
            <template #body="slotProps">{{ formatDate(slotProps.data.expiry_date) }}</template>
          </Column>
          <Column field="purchase_price" :header="t('price').value">
            <template #body="slotProps">{{ slotProps.data.purchase_price ? formatCurrency(slotProps.data.purchase_price) : '-' }}</template>
          </Column>
          <Column :header="t('actions').value" style="width: 80px">
            <template #body="slotProps">
              <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="deleteLicense(slotProps.data.id)" />
            </template>
          </Column>
        </DataTable>

        <!-- Add License Form -->
        <div v-if="showLicenseForm" class="mt-4 p-4 border rounded-lg" style="border-color: var(--border-color);">
          <h4 class="font-semibold mb-3">{{ t('addLicense').value }}</h4>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('type').value }}</label>
              <Dropdown v-model="licenseForm.license_type" :options="licenseTypeOptions" class="w-full" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('quantity').value }}</label>
              <InputNumber v-model="licenseForm.quantity" class="w-full" :min="1" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('purchaseDate').value }}</label>
              <Calendar v-model="licenseForm.purchase_date" dateFormat="yy-mm-dd" class="w-full" showIcon />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('expiryDate').value }}</label>
              <Calendar v-model="licenseForm.expiry_date" dateFormat="yy-mm-dd" class="w-full" showIcon />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('licenseKey').value }}</label>
              <InputText v-model="licenseForm.license_key" class="w-full" type="password" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('price').value }}</label>
              <InputNumber v-model="licenseForm.purchase_price" class="w-full" mode="currency" currency="EUR" locale="fr-FR" />
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <Button :label="t('cancel').value" severity="secondary" outlined size="small" @click="showLicenseForm = false" />
            <Button :label="t('add').value" icon="pi pi-check" size="small" @click="addLicense" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button :label="t('close').value" @click="showLicensesDialog = false" />
      </template>
    </Dialog>

    <!-- Installations Dialog -->
    <Dialog v-model:visible="showInstallationsDialog" modal :header="t('installations').value" :style="{ width: '700px' }">
      <div v-if="selectedSoftware">
        <div class="p-3 rounded-lg mb-4 flex justify-between items-center" style="background-color: var(--bg-app);">
          <div>
            <span class="opacity-60">{{ t('software').value }}:</span>
            <strong class="ml-2">{{ selectedSoftware.name }}</strong>
          </div>
          <Button :label="t('addInstallation').value" icon="pi pi-plus" size="small" @click="openInstallationForm()" />
        </div>

        <DataTable :value="installations" class="text-sm" stripedRows>
          <Column :header="t('equipment').value">
            <template #body="slotProps">{{ getEquipmentName(slotProps.data.equipment_id) }}</template>
          </Column>
          <Column field="installed_version" :header="t('version').value" style="width: 120px"></Column>
          <Column :header="t('installDate').value">
            <template #body="slotProps">{{ formatDate(slotProps.data.installation_date) }}</template>
          </Column>
          <Column :header="t('discoveredAt').value">
            <template #body="slotProps">{{ formatDate(slotProps.data.discovered_at) }}</template>
          </Column>
          <Column :header="t('actions').value" style="width: 80px">
            <template #body="slotProps">
              <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="deleteInstallation(slotProps.data.id)" />
            </template>
          </Column>
        </DataTable>

        <!-- Add Installation Form -->
        <div v-if="showInstallationForm" class="mt-4 p-4 border rounded-lg" style="border-color: var(--border-color);">
          <h4 class="font-semibold mb-3">{{ t('addInstallation').value }}</h4>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('equipment').value }} <span class="text-red-500">*</span></label>
              <Dropdown v-model="installationForm.equipment_id" :options="equipment" optionLabel="name" optionValue="id" class="w-full" filter />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('version').value }}</label>
              <InputText v-model="installationForm.installed_version" class="w-full" />
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <Button :label="t('cancel').value" severity="secondary" outlined size="small" @click="showInstallationForm = false" />
            <Button :label="t('add').value" icon="pi pi-check" size="small" @click="addInstallation" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button :label="t('close').value" @click="showInstallationsDialog = false" />
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
const software = ref([]);
const licenses = ref([]);
const installations = ref([]);
const equipment = ref([]);
const complianceOverview = ref(null);
const expiringLicenses = ref([]);
const expandedRows = ref({});

// Filters
const filterCategory = ref(null);

// Dialogs
const showSoftwareDialog = ref(false);
const showLicensesDialog = ref(false);
const showInstallationsDialog = ref(false);
const showLicenseForm = ref(false);
const showInstallationForm = ref(false);

// Editing states
const editingSoftware = ref(null);
const selectedSoftware = ref(null);

// Forms
const softwareForm = ref({ name: '', publisher: '', version: '', category: null, notes: '' });
const licenseForm = ref({ license_type: 'perpetual', quantity: 1, purchase_date: null, expiry_date: null, license_key: '', purchase_price: null });
const installationForm = ref({ equipment_id: null, installed_version: '' });

// Options
const categoryOptions = ['os', 'database', 'middleware', 'application', 'utility', 'security'];
const licenseTypeOptions = ['perpetual', 'subscription', 'oem', 'volume'];

// Computed
const filteredSoftware = computed(() => {
  if (!filterCategory.value) return software.value;
  return software.value.filter(s => s.category === filterCategory.value);
});

// Helpers
const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString();
};

const formatCurrency = (value) => {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(value);
};

const getComplianceSeverity = (status) => {
  switch (status) {
    case 'compliant': return 'success';
    case 'warning': return 'warning';
    case 'violation': return 'danger';
    default: return 'secondary';
  }
};

const getEquipmentName = (id) => {
  const eq = equipment.value.find(e => e.id === id);
  return eq?.name || `Equipment #${id}`;
};

// Data loading
const loadData = async () => {
  try {
    const [softwareRes, equipmentRes, complianceRes, expiringRes] = await Promise.all([
      api.get('/software/'),
      api.get('/inventory/equipment/'),
      api.get('/software/compliance'),
      api.get('/software/licenses/expiring', { params: { days: 30 } })
    ]);
    software.value = softwareRes.data;
    equipment.value = equipmentRes.data;
    complianceOverview.value = complianceRes.data;
    expiringLicenses.value = expiringRes.data;
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || 'Failed to load data' });
  }
};

// Software CRUD
const openSoftwareDialog = (sw = null) => {
  editingSoftware.value = sw;
  softwareForm.value = sw ? { ...sw } : { name: '', publisher: '', version: '', category: null, notes: '' };
  showSoftwareDialog.value = true;
};

const saveSoftware = async () => {
  if (!softwareForm.value.name) {
    toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('fillRequiredFields').value });
    return;
  }
  try {
    if (editingSoftware.value) {
      await api.put(`/software/${editingSoftware.value.id}`, softwareForm.value);
      toast.add({ severity: 'success', summary: t('success').value, detail: t('softwareUpdated').value });
    } else {
      await api.post('/software/', softwareForm.value);
      toast.add({ severity: 'success', summary: t('success').value, detail: t('softwareCreated').value });
    }
    showSoftwareDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const confirmDeleteSoftware = async (sw) => {
  if (!confirm(t('confirmDeleteItem').value)) return;
  try {
    await api.delete(`/software/${sw.id}`);
    toast.add({ severity: 'success', summary: t('deleted').value, detail: t('softwareDeleted').value });
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

// Licenses
const openLicensesDialog = async (sw) => {
  selectedSoftware.value = sw;
  showLicenseForm.value = false;
  try {
    const response = await api.get(`/software/${sw.id}/licenses`);
    licenses.value = response.data;
  } catch (e) {
    licenses.value = [];
  }
  showLicensesDialog.value = true;
};

const openLicenseForm = () => {
  licenseForm.value = { license_type: 'perpetual', quantity: 1, purchase_date: null, expiry_date: null, license_key: '', purchase_price: null };
  showLicenseForm.value = true;
};

const addLicense = async () => {
  try {
    const data = {
      ...licenseForm.value,
      software_id: selectedSoftware.value.id,
      purchase_date: licenseForm.value.purchase_date instanceof Date ? licenseForm.value.purchase_date.toISOString().split('T')[0] : licenseForm.value.purchase_date,
      expiry_date: licenseForm.value.expiry_date instanceof Date ? licenseForm.value.expiry_date.toISOString().split('T')[0] : licenseForm.value.expiry_date
    };
    await api.post(`/software/${selectedSoftware.value.id}/licenses`, data);
    const response = await api.get(`/software/${selectedSoftware.value.id}/licenses`);
    licenses.value = response.data;
    showLicenseForm.value = false;
    loadData();
    toast.add({ severity: 'success', summary: t('success').value, detail: t('licenseAdded').value });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const deleteLicense = async (licenseId) => {
  if (!confirm(t('confirmDeleteItem').value)) return;
  try {
    await api.delete(`/software/licenses/${licenseId}`);
    licenses.value = licenses.value.filter(l => l.id !== licenseId);
    loadData();
    toast.add({ severity: 'success', summary: t('deleted').value, detail: t('licenseDeleted').value });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

// Installations
const openInstallationsDialog = async (sw) => {
  selectedSoftware.value = sw;
  showInstallationForm.value = false;
  try {
    const response = await api.get(`/software/${sw.id}/installations`);
    installations.value = response.data;
  } catch (e) {
    installations.value = [];
  }
  showInstallationsDialog.value = true;
};

const openInstallationForm = () => {
  installationForm.value = { equipment_id: null, installed_version: '' };
  showInstallationForm.value = true;
};

const addInstallation = async () => {
  if (!installationForm.value.equipment_id) {
    toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('fillRequiredFields').value });
    return;
  }
  try {
    const data = { ...installationForm.value, software_id: selectedSoftware.value.id };
    await api.post(`/software/${selectedSoftware.value.id}/installations`, data);
    const response = await api.get(`/software/${selectedSoftware.value.id}/installations`);
    installations.value = response.data;
    showInstallationForm.value = false;
    loadData();
    toast.add({ severity: 'success', summary: t('success').value, detail: t('installationAdded').value });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const deleteInstallation = async (installationId) => {
  if (!confirm(t('confirmDeleteItem').value)) return;
  try {
    await api.delete(`/software/installations/${installationId}`);
    installations.value = installations.value.filter(i => i.id !== installationId);
    loadData();
    toast.add({ severity: 'success', summary: t('deleted').value, detail: t('installationDeleted').value });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

onMounted(loadData);
</script>
