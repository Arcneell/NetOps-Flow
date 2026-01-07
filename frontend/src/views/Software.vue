<template>
  <div class="flex flex-col h-full">
    <!-- Breadcrumbs -->
    <Breadcrumbs :items="breadcrumbItems" />

    <div class="flex gap-6 flex-1 overflow-hidden">
    <!-- Sidebar with compliance -->
    <div class="w-72 flex-shrink-0">
      <div class="card p-4 mb-4">
        <h3 class="font-bold text-lg mb-4">{{ t('software.title') }}</h3>

        <!-- Compliance Overview -->
        <div v-if="complianceOverview" class="mb-4">
          <h4 class="text-sm font-semibold opacity-70 mb-3">{{ t('software.licenseCompliance') }}</h4>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="p-2 rounded bg-green-100 dark:bg-green-900">
              <div class="text-xl font-bold text-green-600 dark:text-green-400">{{ complianceOverview.compliant }}</div>
              <div class="text-xs opacity-70">{{ t('software.compliant') }}</div>
            </div>
            <div class="p-2 rounded bg-yellow-100 dark:bg-yellow-900">
              <div class="text-xl font-bold text-yellow-600 dark:text-yellow-400">{{ complianceOverview.warning }}</div>
              <div class="text-xs opacity-70">{{ t('status.warning') }}</div>
            </div>
            <div class="p-2 rounded bg-red-100 dark:bg-red-900">
              <div class="text-xl font-bold text-red-600 dark:text-red-400">{{ complianceOverview.violation }}</div>
              <div class="text-xs opacity-70">{{ t('software.violation') }}</div>
            </div>
          </div>
        </div>

        <!-- Violations List -->
        <div v-if="complianceOverview?.violations?.length" class="mb-4">
          <h4 class="text-sm font-semibold opacity-70 mb-2">{{ t('software.violations') }}</h4>
          <div v-for="v in complianceOverview.violations" :key="v.software_id"
               class="p-2 rounded-lg mb-2 text-sm bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200">
            <div class="font-medium">{{ v.software_name }}</div>
            <div class="opacity-70">{{ v.installed }}/{{ v.licensed }} (+{{ v.over_by }})</div>
          </div>
        </div>

        <!-- Filter by Category -->
        <div>
          <label class="block text-sm font-medium mb-2">{{ t('software.filterByCategory') }}</label>
          <Dropdown v-model="filterCategory" :options="categoryOptions" :placeholder="t('software.allCategories')" showClear class="w-full" />
        </div>
      </div>

      <!-- Expiring Licenses -->
      <div v-if="expiringLicenses.length" class="card p-4">
        <h4 class="text-sm font-semibold opacity-70 mb-3">{{ t('software.expiringLicenses') }}</h4>
        <div v-for="alert in expiringLicenses" :key="alert.item_id"
             class="p-2 rounded-lg mb-2 text-sm"
             :class="[
               alert.severity === 'critical' ? 'bg-red-100 dark:bg-red-900' :
               alert.severity === 'warning' ? 'bg-yellow-100 dark:bg-yellow-900' :
               'bg-blue-100 dark:bg-blue-900'
             ]">
          <div class="font-medium">{{ alert.item_name }}</div>
          <div class="opacity-70">{{ alert.days_remaining }} {{ t('contracts.daysRemaining') }}</div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 overflow-hidden">
      <div class="card h-full flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('software.softwareCatalog') }}</h3>
          <Button :label="t('software.newSoftware')" icon="pi pi-plus" @click="openSoftwareDialog()" />
        </div>

        <div class="flex-1 overflow-auto">
          <DataTable :value="filteredSoftware" stripedRows paginator :rows="10" v-model:expandedRows="expandedRows" dataKey="id" class="text-sm">
            <Column expander style="width: 3rem" />
            <Column field="name" :header="t('common.name')" sortable>
              <template #body="slotProps">
                <span
                  class="font-medium text-blue-500 hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer transition-colors hover:underline"
                  @click.stop="openSoftwareDetail(slotProps.data)"
                >
                  {{ slotProps.data.name }}
                </span>
              </template>
            </Column>
            <Column field="publisher" :header="t('software.publisher')"></Column>
            <Column field="version" :header="t('software.version')" style="width: 100px"></Column>
            <Column field="category" :header="t('software.category')">
              <template #body="slotProps">
                <Tag v-if="slotProps.data.category" :value="slotProps.data.category" />
                <span v-else class="opacity-50">-</span>
              </template>
            </Column>
            <Column :header="t('software.licenses')" style="width: 100px">
              <template #body="slotProps">{{ slotProps.data.total_licenses }}</template>
            </Column>
            <Column :header="t('software.installations')" style="width: 100px">
              <template #body="slotProps">{{ slotProps.data.total_installations }}</template>
            </Column>
            <Column :header="t('software.compliance')" style="width: 120px">
              <template #body="slotProps">
                <Tag :value="slotProps.data.compliance_status" :severity="getComplianceSeverity(slotProps.data.compliance_status)" />
              </template>
            </Column>
            <Column :header="t('common.actions')" style="width: 120px">
              <template #body="slotProps">
                <div class="flex gap-1">
                  <Button icon="pi pi-key" text rounded size="small" @click="openLicensesDialog(slotProps.data)" v-tooltip.top="t('software.manageLicenses')" />
                  <Button icon="pi pi-pencil" text rounded size="small" @click="openSoftwareDialog(slotProps.data)" />
                  <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="confirmDeleteSoftware(slotProps.data)" />
                </div>
              </template>
            </Column>

            <template #expansion="slotProps">
              <div class="p-4 grid grid-cols-2 gap-6" style="background-color: var(--bg-app);">
                <div>
                  <h4 class="font-semibold mb-3 text-blue-500">{{ t('common.details') }}</h4>
                  <p class="mb-2"><span class="opacity-60">{{ t('software.publisher') }}:</span> {{ slotProps.data.publisher || '-' }}</p>
                  <p class="mb-2"><span class="opacity-60">{{ t('software.category') }}:</span> {{ slotProps.data.category || '-' }}</p>
                  <p><span class="opacity-60">{{ t('inventory.notes') }}:</span> {{ slotProps.data.notes || '-' }}</p>
                </div>
                <div>
                  <h4 class="font-semibold mb-3 text-blue-500">{{ t('software.installations') }}</h4>
                  <Button :label="t('software.viewInstallations')" icon="pi pi-desktop" size="small" @click="openInstallationsDialog(slotProps.data)" />
                </div>
              </div>
            </template>
          </DataTable>
        </div>
      </div>
    </div>

    <!-- Software Dialog -->
    <Dialog v-model:visible="showSoftwareDialog" modal :header="editingSoftware ? t('software.editSoftware') : t('software.newSoftware')" :style="{ width: '500px' }" @keydown.enter="onSoftwareDialogEnter">
      <div class="flex flex-col gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('common.name') }} <span class="text-red-500">*</span></label>
          <InputText v-model="softwareForm.name" class="w-full" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('software.publisher') }}</label>
            <InputText v-model="softwareForm.publisher" class="w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('software.version') }}</label>
            <InputText v-model="softwareForm.version" class="w-full" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('software.category') }}</label>
          <Dropdown v-model="softwareForm.category" :options="categoryOptions" class="w-full" showClear />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('inventory.notes') }}</label>
          <Textarea v-model="softwareForm.notes" rows="2" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showSoftwareDialog = false" />
          <Button :label="t('common.save')" icon="pi pi-check" @click="saveSoftware" />
        </div>
      </template>
    </Dialog>

    <!-- Licenses Dialog -->
    <Dialog v-model:visible="showLicensesDialog" modal :header="t('software.manageLicenses')" :style="{ width: '700px' }" @keydown.enter="onLicenseDialogEnter">
      <div v-if="selectedSoftware">
        <div class="p-3 rounded-lg mb-4 flex justify-between items-center" style="background-color: var(--bg-app);">
          <div>
            <span class="opacity-60">{{ t('software.title') }}:</span>
            <strong class="ml-2">{{ selectedSoftware.name }}</strong>
          </div>
          <Button :label="t('software.addLicense')" icon="pi pi-plus" size="small" @click="openLicenseForm()" />
        </div>

        <DataTable :value="licenses" class="text-sm" stripedRows>
          <Column field="license_type" :header="t('inventory.type')">
            <template #body="slotProps">
              <Tag :value="slotProps.data.license_type" />
            </template>
          </Column>
          <Column field="quantity" :header="t('software.quantity')" style="width: 100px"></Column>
          <Column :header="t('software.purchaseDate')">
            <template #body="slotProps">{{ formatDate(slotProps.data.purchase_date) }}</template>
          </Column>
          <Column :header="t('software.expiryDate')">
            <template #body="slotProps">{{ formatDate(slotProps.data.expiry_date) }}</template>
          </Column>
          <Column field="purchase_price" :header="t('software.price')">
            <template #body="slotProps">{{ slotProps.data.purchase_price ? formatCurrency(slotProps.data.purchase_price) : '-' }}</template>
          </Column>
          <Column :header="t('common.actions')" style="width: 80px">
            <template #body="slotProps">
              <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="deleteLicense(slotProps.data.id)" />
            </template>
          </Column>
        </DataTable>

        <!-- Add License Form -->
        <div v-if="showLicenseForm" class="mt-4 p-4 border rounded-lg" style="border-color: var(--border-color);">
          <h4 class="font-semibold mb-3">{{ t('software.addLicense') }}</h4>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('inventory.type') }}</label>
              <Dropdown v-model="licenseForm.license_type" :options="licenseTypeOptions" class="w-full" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('software.quantity') }}</label>
              <InputNumber v-model="licenseForm.quantity" class="w-full" :min="1" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('software.purchaseDate') }}</label>
              <Calendar v-model="licenseForm.purchase_date" dateFormat="yy-mm-dd" class="w-full" showIcon />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('software.expiryDate') }}</label>
              <Calendar v-model="licenseForm.expiry_date" dateFormat="yy-mm-dd" class="w-full" showIcon />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('software.licenseKey') }}</label>
              <InputText v-model="licenseForm.license_key" class="w-full" type="password" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('software.price') }}</label>
              <InputNumber v-model="licenseForm.purchase_price" class="w-full" mode="currency" currency="EUR" locale="fr-FR" />
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <Button :label="t('common.cancel')" severity="secondary" outlined size="small" @click="showLicenseForm = false" />
            <Button :label="t('common.add')" icon="pi pi-check" size="small" @click="addLicense" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button :label="t('common.close')" @click="showLicensesDialog = false" />
      </template>
    </Dialog>

    <!-- Installations Dialog -->
    <Dialog v-model:visible="showInstallationsDialog" modal :header="t('software.installations')" :style="{ width: '700px' }" @keydown.enter="onInstallationDialogEnter">
      <div v-if="selectedSoftware">
        <div class="p-3 rounded-lg mb-4 flex justify-between items-center" style="background-color: var(--bg-app);">
          <div>
            <span class="opacity-60">{{ t('software.title') }}:</span>
            <strong class="ml-2">{{ selectedSoftware.name }}</strong>
          </div>
          <Button :label="t('software.addInstallation')" icon="pi pi-plus" size="small" @click="openInstallationForm()" />
        </div>

        <DataTable :value="installations" class="text-sm" stripedRows>
          <Column :header="t('inventory.equipment')">
            <template #body="slotProps">{{ getEquipmentName(slotProps.data.equipment_id) }}</template>
          </Column>
          <Column field="installed_version" :header="t('software.version')" style="width: 120px"></Column>
          <Column :header="t('software.installDate')">
            <template #body="slotProps">{{ formatDate(slotProps.data.installation_date) }}</template>
          </Column>
          <Column :header="t('software.discoveredAt')">
            <template #body="slotProps">{{ formatDate(slotProps.data.discovered_at) }}</template>
          </Column>
          <Column :header="t('common.actions')" style="width: 80px">
            <template #body="slotProps">
              <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="deleteInstallation(slotProps.data.id)" />
            </template>
          </Column>
        </DataTable>

        <!-- Add Installation Form -->
        <div v-if="showInstallationForm" class="mt-4 p-4 border rounded-lg" style="border-color: var(--border-color);">
          <h4 class="font-semibold mb-3">{{ t('software.addInstallation') }}</h4>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('inventory.equipment') }} <span class="text-red-500">*</span></label>
              <Dropdown v-model="installationForm.equipment_id" :options="equipment" optionLabel="name" optionValue="id" class="w-full" filter />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('software.version') }}</label>
              <InputText v-model="installationForm.installed_version" class="w-full" />
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-4">
            <Button :label="t('common.cancel')" severity="secondary" outlined size="small" @click="showInstallationForm = false" />
            <Button :label="t('common.add')" icon="pi pi-check" size="small" @click="addInstallation" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button :label="t('common.close')" @click="showInstallationsDialog = false" />
      </template>
    </Dialog>

    <!-- Software Detail SlideOver -->
    <SoftwareDetailSlideOver
      v-model="showDetailSlideOver"
      :softwareId="selectedSoftwareId"
      @edit="handleEditFromSlideOver"
      @manage-licenses="handleManageLicensesFromSlideOver"
    />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useI18n } from 'vue-i18n';
import api from '../api';
import Breadcrumbs from '../components/shared/Breadcrumbs.vue';
import SoftwareDetailSlideOver from '../components/shared/SoftwareDetailSlideOver.vue';

const route = useRoute();
const router = useRouter();

const { t } = useI18n();
const toast = useToast();

// Breadcrumbs
const breadcrumbItems = computed(() => [
  { label: t('software.title'), icon: 'pi-desktop' }
]);

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
const showDetailSlideOver = ref(false);
const selectedSoftwareId = ref(null);

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
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || 'Failed to load data' });
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
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.fillRequiredFields') });
    return;
  }
  try {
    if (editingSoftware.value) {
      await api.put(`/software/${editingSoftware.value.id}`, softwareForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('software.softwareUpdated') });
    } else {
      await api.post('/software/', softwareForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('software.softwareCreated') });
    }
    showSoftwareDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }
};

const confirmDeleteSoftware = async (sw) => {
  if (!confirm(t('common.confirmDeleteItem'))) return;
  try {
    await api.delete(`/software/${sw.id}`);
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('software.softwareDeleted') });
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
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
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('software.licenseAdded') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }
};

const deleteLicense = async (licenseId) => {
  if (!confirm(t('common.confirmDeleteItem'))) return;
  try {
    await api.delete(`/software/licenses/${licenseId}`);
    licenses.value = licenses.value.filter(l => l.id !== licenseId);
    loadData();
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('software.licenseDeleted') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
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
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.fillRequiredFields') });
    return;
  }
  try {
    const data = { ...installationForm.value, software_id: selectedSoftware.value.id };
    await api.post(`/software/${selectedSoftware.value.id}/installations`, data);
    const response = await api.get(`/software/${selectedSoftware.value.id}/installations`);
    installations.value = response.data;
    showInstallationForm.value = false;
    loadData();
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('software.installationAdded') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }
};

const deleteInstallation = async (installationId) => {
  if (!confirm(t('common.confirmDeleteItem'))) return;
  try {
    await api.delete(`/software/installations/${installationId}`);
    installations.value = installations.value.filter(i => i.id !== installationId);
    loadData();
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('software.installationDeleted') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }
};

// Enter key handlers for dialogs
const onSoftwareDialogEnter = (event) => {
  if (event.target.tagName !== 'TEXTAREA') {
    event.preventDefault();
    saveSoftware();
  }
};

const onLicenseDialogEnter = (event) => {
  if (event.target.tagName !== 'TEXTAREA' && showLicenseForm.value) {
    event.preventDefault();
    addLicense();
  }
};

const onInstallationDialogEnter = (event) => {
  if (event.target.tagName !== 'TEXTAREA' && showInstallationForm.value) {
    event.preventDefault();
    addInstallation();
  }
};

// Open software detail slide-over
const openSoftwareDetail = (sw) => {
  selectedSoftwareId.value = sw.id;
  showDetailSlideOver.value = true;
};

// Handle edit from slide-over
const handleEditFromSlideOver = (sw) => {
  showDetailSlideOver.value = false;
  openSoftwareDialog(sw);
};

// Handle manage licenses from slide-over
const handleManageLicensesFromSlideOver = (sw) => {
  showDetailSlideOver.value = false;
  openLicensesDialog(sw);
};

// Open software from URL parameter
const openSoftwareFromUrl = () => {
  const softwareId = route.query.id;
  if (softwareId && software.value.length > 0) {
    const sw = software.value.find(s => s.id === parseInt(softwareId));
    if (sw) {
      openSoftwareDetail(sw);
      // Clear the query parameter after opening
      router.replace({ path: route.path });
    }
  }
};

// Watch for route changes
watch(() => route.query.id, (newVal) => {
  if (newVal) {
    openSoftwareFromUrl();
  }
});

onMounted(async () => {
  await loadData();
  // Check if we need to open a software from URL
  openSoftwareFromUrl();
});
</script>
