<template>
  <div class="flex flex-col h-full">
    <!-- Breadcrumbs -->
    <Breadcrumbs :items="breadcrumbItems" />

    <div class="flex justify-end mb-6">
      <Button :label="t('dashboard.newSubnet')" icon="pi pi-plus" @click="showSubnetDialog = true" />
    </div>

    <div class="card">
      <DataTable :value="subnets" v-model:expandedRows="expandedRows" dataKey="id" showGridlines @rowExpand="onRowExpand">
        <Column expander style="width: 3rem" />
        <Column field="cidr" :header="t('ipam.cidr')" sortable class="font-mono font-bold text-blue-600 dark:text-blue-400"></Column>
        <Column field="name" :header="t('common.name')" sortable></Column>
        <Column field="description" :header="t('ipam.description')"></Column>
        <Column :header="t('ipam.ips')" style="width: 8rem; text-align: center">
          <template #body="slotProps">
            <span class="font-medium">{{ slotProps.data.ip_count }}</span>
          </template>
        </Column>
        <Column :header="t('common.actions')" style="width: 12rem; text-align: center">
          <template #body="slotProps">
             <div class="flex gap-2 justify-center">
                 <Button icon="pi pi-plus" class="p-button-text p-button-sm" v-tooltip.top="t('ipam.addIp')" @click="openIpDialog(slotProps.data)" />
                 <Button icon="pi pi-search" class="p-button-text p-button-sm p-button-secondary" v-tooltip.top="t('ipam.scanSubnet')" @click="scanSubnet(slotProps.data)" />
             </div>
          </template>
        </Column>

        <template #expansion="slotProps">
          <div class="p-4" style="background-color: rgba(0,0,0,0.02);">
            <div class="flex justify-between items-center mb-3">
                 <h3 class="font-semibold text-sm opacity-70">{{ t('ipam.allocatedIps') }} {{ slotProps.data.cidr }}</h3>
                 <span class="text-xs opacity-50" v-if="subnetIps[slotProps.data.id]?.total > 0">
                    {{ subnetIps[slotProps.data.id].total }} {{ t('ipam.addressesFound') }}
                 </span>
            </div>

            <!-- Loading state -->
            <div v-if="loadingIps[slotProps.data.id]" class="flex justify-center py-8">
              <i class="pi pi-spin pi-spinner text-2xl opacity-50"></i>
            </div>

            <!-- IP Table with pagination and scroll -->
            <template v-else-if="subnetIps[slotProps.data.id]?.items?.length > 0">
              <DataTable
                :value="subnetIps[slotProps.data.id].items"
                size="small"
                stripedRows
                lazy
                paginator
                :rows="50"
                :totalRecords="subnetIps[slotProps.data.id].total"
                :first="subnetIps[slotProps.data.id].skip || 0"
                @page="(e) => onIpPage(e, slotProps.data.id)"
                :rowsPerPageOptions="[25, 50, 100]"
                scrollable
                scrollHeight="400px"
              >
                <Column field="address" :header="t('ipam.address')" sortable class="font-mono text-sm"></Column>
                <Column field="hostname" :header="t('ipam.hostname')" class="text-sm"></Column>
                <Column field="mac_address" :header="t('ipam.mac')" class="font-mono text-xs opacity-70"></Column>
                <Column :header="t('ip.linkedEquipment')" class="text-sm">
                   <template #body="ipSlot">
                      <span v-if="ipSlot.data.equipment" class="flex items-center gap-2">
                         <i class="pi pi-box text-blue-500"></i>
                         <span class="font-medium">{{ ipSlot.data.equipment.name }}</span>
                      </span>
                      <span v-else class="opacity-50">-</span>
                   </template>
                </Column>
                <Column field="last_scanned_at" :header="t('ipam.lastScan')" class="text-xs opacity-70">
                   <template #body="ip">
                      {{ ip.data.last_scanned_at ? new Date(ip.data.last_scanned_at).toLocaleString() : '-' }}
                   </template>
                </Column>
                <Column field="status" :header="t('ipam.status')">
                   <template #body="ipSlot">
                      <Tag :value="ipSlot.data.status" :severity="getStatusSeverity(ipSlot.data.status)" />
                   </template>
                </Column>
              </DataTable>
            </template>

            <div v-else class="opacity-50 text-sm italic py-4 text-center">{{ t('ipam.noIps') }}</div>
          </div>
        </template>
      </DataTable>
    </div>

    <!-- Create Subnet Dialog -->
    <Dialog v-model:visible="showSubnetDialog" modal :header="t('dashboard.newSubnet')" :style="{ width: '400px' }" @keydown.enter="onSubnetDialogEnter">
      <div class="flex flex-col gap-4 mt-2">
        <div class="flex flex-col gap-2">
          <label for="cidr" class="text-sm font-medium">{{ t('ipam.cidr') }} <span class="text-red-500">*</span></label>
          <InputText id="cidr" v-model="newSubnet.cidr" placeholder="192.168.1.0/24" />
        </div>
        <div class="flex flex-col gap-2">
          <label for="name" class="text-sm font-medium">{{ t('common.name') }} <span class="text-red-500">*</span></label>
          <InputText id="name" v-model="newSubnet.name" placeholder="Management LAN" />
        </div>
        <div class="flex flex-col gap-2">
          <label for="desc" class="text-sm font-medium">{{ t('ipam.description') }}</label>
          <InputText id="desc" v-model="newSubnet.description" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showSubnetDialog = false" />
          <Button :label="t('common.save')" icon="pi pi-check" @click="createSubnet" />
        </div>
      </template>
    </Dialog>

    <!-- Create IP Dialog -->
    <Dialog v-model:visible="showIpDialog" modal :header="t('ipam.manualIpAllocation')" :style="{ width: '400px' }" @keydown.enter="onIpDialogEnter">
      <div class="flex flex-col gap-4 mt-2" v-if="selectedSubnet">
        <div class="flex flex-col gap-2">
          <label for="ipaddr" class="text-sm font-medium">{{ t('ipam.ipAddress') }} <span class="text-red-500">*</span></label>
          <InputText id="ipaddr" v-model="newIp.address" />
        </div>
        <div class="flex flex-col gap-2">
          <label for="hostname" class="text-sm font-medium">{{ t('ipam.hostname') }}</label>
          <InputText id="hostname" v-model="newIp.hostname" />
        </div>
        <div class="flex flex-col gap-2">
          <label for="status" class="text-sm font-medium">{{ t('ipam.status') }}</label>
          <Dropdown id="status" v-model="newIp.status" :options="['available', 'active', 'reserved']" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showIpDialog = false" />
          <Button :label="t('common.add')" icon="pi pi-check" @click="createIp" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useI18n } from 'vue-i18n';
import api from '../api';
import Breadcrumbs from '../components/shared/Breadcrumbs.vue';

const { t } = useI18n();
const toast = useToast();

// Breadcrumbs
const breadcrumbItems = computed(() => [
  { label: t('ipam.title'), icon: 'pi-sitemap' }
]);

const subnets = ref([]);
const expandedRows = ref({});
const showSubnetDialog = ref(false);
const showIpDialog = ref(false);
const selectedSubnet = ref(null);

// IP pagination state per subnet
const subnetIps = reactive({});
const loadingIps = reactive({});

const newSubnet = ref({ cidr: '', name: '', description: '' });
const newIp = ref({ address: '', hostname: '', status: 'active' });

const fetchSubnets = async () => {
  try {
    const res = await api.get('/subnets/');
    subnets.value = res.data;
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: 'Could not load subnets', life: 3000 });
  }
};

// Load IPs for a specific subnet with pagination
const loadSubnetIps = async (subnetId, skip = 0, limit = 50) => {
  loadingIps[subnetId] = true;
  try {
    const res = await api.get(`/subnets/${subnetId}/ips/`, {
      params: { skip, limit }
    });
    subnetIps[subnetId] = {
      items: res.data.items,
      total: res.data.total,
      skip: res.data.skip,
      limit: res.data.limit
    };
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: 'Could not load IPs', life: 3000 });
    subnetIps[subnetId] = { items: [], total: 0, skip: 0, limit };
  } finally {
    loadingIps[subnetId] = false;
  }
};

// Handler for row expansion - load IPs on demand
const onRowExpand = (event) => {
  const subnetId = event.data.id;
  // Only load if not already loaded
  if (!subnetIps[subnetId]) {
    loadSubnetIps(subnetId);
  }
};

// Handler for IP pagination
const onIpPage = (event, subnetId) => {
  const skip = event.first;
  const limit = event.rows;
  loadSubnetIps(subnetId, skip, limit);
};

const createSubnet = async () => {
  if (!newSubnet.value.cidr || !newSubnet.value.name) {
      toast.add({ severity: 'warn', summary: t('common.error'), detail: t('validation.fillRequiredFields') });
      return;
  }
  try {
    await api.post('/subnets/', newSubnet.value);
    showSubnetDialog.value = false;
    newSubnet.value = { cidr: '', name: '', description: '' };
    fetchSubnets();
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('ipam.subnetCreated'), life: 3000 });
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: error.response?.data?.detail || t('ipam.failedCreateSubnet'), life: 3000 });
  }
};

const openIpDialog = (subnet) => {
  selectedSubnet.value = subnet;
  newIp.value = { address: '', hostname: '', status: 'active' };
  showIpDialog.value = true;
};

const createIp = async () => {
  if (!selectedSubnet.value) return;
  if (!newIp.value.address) {
      toast.add({ severity: 'warn', summary: t('common.error'), detail: t('validation.fillRequiredFields') });
      return;
  }
  try {
    const subnetId = selectedSubnet.value.id;
    await api.post(`/subnets/${subnetId}/ips/`, newIp.value);
    showIpDialog.value = false;
    // Refresh subnets (for IP count) and IPs for this subnet
    fetchSubnets();
    // Clear cached IPs to force reload on next expand
    delete subnetIps[subnetId];
    // If subnet is already expanded, reload IPs
    if (expandedRows.value[subnetId]) {
      loadSubnetIps(subnetId);
    }
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('ipam.ipAllocated'), life: 3000 });
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: error.response?.data?.detail || t('ipam.failedAllocateIp'), life: 3000 });
  }
};

const scanSubnet = async (subnet) => {
    try {
        await api.post(`/subnets/${subnet.id}/scan`);
        toast.add({ severity: 'info', summary: t('ipam.scanStarted'), detail: `${t('ipam.scanningBackground')} ${subnet.cidr}`, life: 5000 });
    } catch (e) {
        toast.add({ severity: 'error', summary: t('common.error'), detail: t('ipam.failedStartScan'), life: 3000 });
    }
};

const getStatusSeverity = (status) => {
    switch (status) {
        case 'active': return 'success';
        case 'reserved': return 'warning';
        case 'available': return 'info';
        default: return null;
    }
};

// Enter key handlers for dialogs
const onSubnetDialogEnter = (event) => {
    if (event.target.tagName !== 'TEXTAREA') {
        event.preventDefault();
        createSubnet();
    }
};

const onIpDialogEnter = (event) => {
    if (event.target.tagName !== 'TEXTAREA') {
        event.preventDefault();
        createIp();
    }
};

onMounted(fetchSubnets);
</script>
