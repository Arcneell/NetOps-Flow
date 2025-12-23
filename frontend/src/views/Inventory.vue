<template>
  <div>
    <TabView>
      <!-- Equipment Tab -->
      <TabPanel :header="t('equipment').value">
        <div class="flex justify-between items-center mb-4">
          <div class="flex gap-2">
            <Dropdown v-model="filterType" :options="typeOptions" optionLabel="name" optionValue="id" :placeholder="t('allTypes').value" showClear class="w-48" />
            <Dropdown v-model="filterStatus" :options="statusOptions" optionLabel="label" optionValue="value" :placeholder="t('allStatuses').value" showClear class="w-48" />
            <Dropdown v-model="filterLocation" :options="locationOptions" optionLabel="label" optionValue="id" :placeholder="t('allLocations').value" showClear class="w-48" />
          </div>
          <Button :label="t('newEquipment').value" icon="pi pi-plus" @click="openEquipmentDialog()" />
        </div>

        <DataTable :value="equipment" stripedRows paginator :rows="10" v-model:expandedRows="expandedRows" dataKey="id">
          <Column expander style="width: 3rem" />
          <Column field="name" :header="t('name').value" sortable></Column>
          <Column :header="t('equipmentType').value">
            <template #body="slotProps">
              <span v-if="slotProps.data.model?.equipment_type">
                <i :class="'pi ' + slotProps.data.model.equipment_type.icon + ' mr-2'"></i>
                {{ slotProps.data.model.equipment_type.name }}
              </span>
              <span v-else class="opacity-50">-</span>
            </template>
          </Column>
          <Column :header="t('equipmentModel').value">
            <template #body="slotProps">
              <span v-if="slotProps.data.model">
                {{ slotProps.data.model.manufacturer?.name }} {{ slotProps.data.model.name }}
              </span>
              <span v-else class="opacity-50">-</span>
            </template>
          </Column>
          <Column field="serial_number" :header="t('serialNumber').value"></Column>
          <Column :header="t('location').value">
            <template #body="slotProps">
              <span v-if="slotProps.data.location">
                {{ slotProps.data.location.site }}
                <span v-if="slotProps.data.location.building"> / {{ slotProps.data.location.building }}</span>
                <span v-if="slotProps.data.location.room"> / {{ slotProps.data.location.room }}</span>
              </span>
              <span v-else class="opacity-50">-</span>
            </template>
          </Column>
          <Column field="status" :header="t('status').value">
            <template #body="slotProps">
              <Tag :value="getStatusLabel(slotProps.data.status)" :severity="getStatusSeverity(slotProps.data.status)" />
            </template>
          </Column>
          <Column :header="t('linkedIps').value">
            <template #body="slotProps">
              <span v-if="slotProps.data.ip_addresses?.length">
                {{ slotProps.data.ip_addresses.map(ip => ip.address).join(', ') }}
              </span>
              <span v-else class="opacity-50 text-sm">{{ t('noIpLinked').value }}</span>
            </template>
          </Column>
          <Column :header="t('actions').value" style="width: 120px">
            <template #body="slotProps">
              <Button icon="pi pi-pencil" text rounded @click="openEquipmentDialog(slotProps.data)" />
              <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmDeleteEquipment(slotProps.data)" />
            </template>
          </Column>

          <template #expansion="slotProps">
            <div class="p-4 grid grid-cols-2 gap-4" style="background-color: rgba(0,0,0,0.02);">
              <div>
                <p><strong>{{ t('assetTag').value }}:</strong> {{ slotProps.data.asset_tag || '-' }}</p>
                <p><strong>{{ t('purchaseDate').value }}:</strong> {{ formatDate(slotProps.data.purchase_date) }}</p>
                <p><strong>{{ t('warrantyExpiry').value }}:</strong> {{ formatDate(slotProps.data.warranty_expiry) }}</p>
                <p><strong>{{ t('supplier').value }}:</strong> {{ slotProps.data.supplier?.name || '-' }}</p>
              </div>
              <div>
                <p><strong>{{ t('notes').value }}:</strong></p>
                <p class="text-sm opacity-70">{{ slotProps.data.notes || '-' }}</p>
                <div class="mt-4">
                  <Button :label="t('linkIp').value" icon="pi pi-link" size="small" @click="openLinkIpDialog(slotProps.data)" />
                </div>
              </div>
            </div>
          </template>
        </DataTable>
      </TabPanel>

      <!-- Manufacturers Tab -->
      <TabPanel :header="t('manufacturers').value">
        <div class="flex justify-end mb-4">
          <Button :label="t('newManufacturer').value" icon="pi pi-plus" @click="openManufacturerDialog()" />
        </div>
        <DataTable :value="manufacturers" stripedRows>
          <Column field="name" :header="t('name').value" sortable></Column>
          <Column field="website" :header="t('website').value"></Column>
          <Column field="notes" :header="t('notes').value"></Column>
          <Column :header="t('actions').value" style="width: 100px">
            <template #body="slotProps">
              <Button icon="pi pi-pencil" text rounded @click="openManufacturerDialog(slotProps.data)" />
              <Button icon="pi pi-trash" text rounded severity="danger" @click="deleteManufacturer(slotProps.data.id)" />
            </template>
          </Column>
        </DataTable>
      </TabPanel>

      <!-- Models Tab -->
      <TabPanel :header="t('equipmentModels').value">
        <div class="flex justify-end mb-4">
          <Button :label="t('newModel').value" icon="pi pi-plus" @click="openModelDialog()" />
        </div>
        <DataTable :value="models" stripedRows>
          <Column field="name" :header="t('name').value" sortable></Column>
          <Column :header="t('manufacturer').value">
            <template #body="slotProps">{{ slotProps.data.manufacturer?.name }}</template>
          </Column>
          <Column :header="t('equipmentType').value">
            <template #body="slotProps">
              <i :class="'pi ' + slotProps.data.equipment_type?.icon + ' mr-2'"></i>
              {{ slotProps.data.equipment_type?.name }}
            </template>
          </Column>
          <Column :header="t('actions').value" style="width: 100px">
            <template #body="slotProps">
              <Button icon="pi pi-pencil" text rounded @click="openModelDialog(slotProps.data)" />
              <Button icon="pi pi-trash" text rounded severity="danger" @click="deleteModel(slotProps.data.id)" />
            </template>
          </Column>
        </DataTable>
      </TabPanel>

      <!-- Types Tab -->
      <TabPanel :header="t('equipmentTypes').value">
        <div class="flex justify-end mb-4">
          <Button :label="t('newType').value" icon="pi pi-plus" @click="openTypeDialog()" />
        </div>
        <DataTable :value="types" stripedRows>
          <Column :header="t('icon').value" style="width: 60px">
            <template #body="slotProps">
              <i :class="'pi ' + slotProps.data.icon + ' text-xl'"></i>
            </template>
          </Column>
          <Column field="name" :header="t('name').value" sortable></Column>
          <Column :header="t('actions').value" style="width: 100px">
            <template #body="slotProps">
              <Button icon="pi pi-pencil" text rounded @click="openTypeDialog(slotProps.data)" />
              <Button icon="pi pi-trash" text rounded severity="danger" @click="deleteType(slotProps.data.id)" />
            </template>
          </Column>
        </DataTable>
      </TabPanel>

      <!-- Locations Tab -->
      <TabPanel :header="t('locations').value">
        <div class="flex justify-end mb-4">
          <Button :label="t('newLocation').value" icon="pi pi-plus" @click="openLocationDialog()" />
        </div>
        <DataTable :value="locations" stripedRows>
          <Column field="site" :header="t('site').value" sortable></Column>
          <Column field="building" :header="t('building').value"></Column>
          <Column field="room" :header="t('room').value"></Column>
          <Column :header="t('actions').value" style="width: 100px">
            <template #body="slotProps">
              <Button icon="pi pi-pencil" text rounded @click="openLocationDialog(slotProps.data)" />
              <Button icon="pi pi-trash" text rounded severity="danger" @click="deleteLocation(slotProps.data.id)" />
            </template>
          </Column>
        </DataTable>
      </TabPanel>

      <!-- Suppliers Tab -->
      <TabPanel :header="t('suppliers').value">
        <div class="flex justify-end mb-4">
          <Button :label="t('newSupplier').value" icon="pi pi-plus" @click="openSupplierDialog()" />
        </div>
        <DataTable :value="suppliers" stripedRows>
          <Column field="name" :header="t('name').value" sortable></Column>
          <Column field="contact_email" :header="t('contactEmail').value"></Column>
          <Column field="phone" :header="t('phone').value"></Column>
          <Column field="website" :header="t('website').value"></Column>
          <Column :header="t('actions').value" style="width: 100px">
            <template #body="slotProps">
              <Button icon="pi pi-pencil" text rounded @click="openSupplierDialog(slotProps.data)" />
              <Button icon="pi pi-trash" text rounded severity="danger" @click="deleteSupplier(slotProps.data.id)" />
            </template>
          </Column>
        </DataTable>
      </TabPanel>
    </TabView>

    <!-- Equipment Dialog -->
    <Dialog v-model:visible="showEquipmentDialog" modal :header="editingEquipment ? t('editEquipment').value : t('newEquipment').value" :style="{ width: '600px' }">
      <div class="grid grid-cols-2 gap-4 mt-2">
        <div class="col-span-2">
          <label class="text-sm font-medium">{{ t('name').value }} *</label>
          <InputText v-model="equipmentForm.name" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('equipmentModel').value }}</label>
          <Dropdown v-model="equipmentForm.model_id" :options="models" optionLabel="name" optionValue="id" :placeholder="t('equipmentModel').value" class="w-full" showClear>
            <template #option="slotProps">
              {{ slotProps.option.manufacturer?.name }} - {{ slotProps.option.name }}
            </template>
          </Dropdown>
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('status').value }}</label>
          <Dropdown v-model="equipmentForm.status" :options="statusOptions" optionLabel="label" optionValue="value" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('serialNumber').value }}</label>
          <InputText v-model="equipmentForm.serial_number" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('assetTag').value }}</label>
          <InputText v-model="equipmentForm.asset_tag" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('location').value }}</label>
          <Dropdown v-model="equipmentForm.location_id" :options="locationOptions" optionLabel="label" optionValue="id" :placeholder="t('location').value" class="w-full" showClear />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('supplier').value }}</label>
          <Dropdown v-model="equipmentForm.supplier_id" :options="suppliers" optionLabel="name" optionValue="id" :placeholder="t('supplier').value" class="w-full" showClear />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('purchaseDate').value }}</label>
          <Calendar v-model="equipmentForm.purchase_date" dateFormat="yy-mm-dd" class="w-full" showIcon />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('warrantyExpiry').value }}</label>
          <Calendar v-model="equipmentForm.warranty_expiry" dateFormat="yy-mm-dd" class="w-full" showIcon />
        </div>
        <div class="col-span-2">
          <label class="text-sm font-medium">{{ t('notes').value }}</label>
          <Textarea v-model="equipmentForm.notes" rows="3" class="w-full" />
        </div>
      </div>
      <template #footer>
        <Button :label="t('cancel').value" text @click="showEquipmentDialog = false" />
        <Button :label="t('save').value" icon="pi pi-check" @click="saveEquipment" />
      </template>
    </Dialog>

    <!-- Manufacturer Dialog -->
    <Dialog v-model:visible="showManufacturerDialog" modal :header="t('manufacturer').value" :style="{ width: '400px' }">
      <div class="flex flex-col gap-4 mt-2">
        <div>
          <label class="text-sm font-medium">{{ t('name').value }} *</label>
          <InputText v-model="manufacturerForm.name" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('website').value }}</label>
          <InputText v-model="manufacturerForm.website" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('notes').value }}</label>
          <Textarea v-model="manufacturerForm.notes" rows="2" class="w-full" />
        </div>
      </div>
      <template #footer>
        <Button :label="t('cancel').value" text @click="showManufacturerDialog = false" />
        <Button :label="t('save').value" icon="pi pi-check" @click="saveManufacturer" />
      </template>
    </Dialog>

    <!-- Model Dialog -->
    <Dialog v-model:visible="showModelDialog" modal :header="t('equipmentModel').value" :style="{ width: '400px' }">
      <div class="flex flex-col gap-4 mt-2">
        <div>
          <label class="text-sm font-medium">{{ t('name').value }} *</label>
          <InputText v-model="modelForm.name" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('manufacturer').value }} *</label>
          <Dropdown v-model="modelForm.manufacturer_id" :options="manufacturers" optionLabel="name" optionValue="id" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('equipmentType').value }} *</label>
          <Dropdown v-model="modelForm.equipment_type_id" :options="types" optionLabel="name" optionValue="id" class="w-full" />
        </div>
      </div>
      <template #footer>
        <Button :label="t('cancel').value" text @click="showModelDialog = false" />
        <Button :label="t('save').value" icon="pi pi-check" @click="saveModel" />
      </template>
    </Dialog>

    <!-- Type Dialog -->
    <Dialog v-model:visible="showTypeDialog" modal :header="t('equipmentType').value" :style="{ width: '400px' }">
      <div class="flex flex-col gap-4 mt-2">
        <div>
          <label class="text-sm font-medium">{{ t('name').value }} *</label>
          <InputText v-model="typeForm.name" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('icon').value }}</label>
          <Dropdown v-model="typeForm.icon" :options="iconOptions" class="w-full">
            <template #value="slotProps">
              <i :class="'pi ' + slotProps.value + ' mr-2'"></i> {{ slotProps.value }}
            </template>
            <template #option="slotProps">
              <i :class="'pi ' + slotProps.option + ' mr-2'"></i> {{ slotProps.option }}
            </template>
          </Dropdown>
        </div>
      </div>
      <template #footer>
        <Button :label="t('cancel').value" text @click="showTypeDialog = false" />
        <Button :label="t('save').value" icon="pi pi-check" @click="saveType" />
      </template>
    </Dialog>

    <!-- Location Dialog -->
    <Dialog v-model:visible="showLocationDialog" modal :header="t('location').value" :style="{ width: '400px' }">
      <div class="flex flex-col gap-4 mt-2">
        <div>
          <label class="text-sm font-medium">{{ t('site').value }} *</label>
          <InputText v-model="locationForm.site" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('building').value }}</label>
          <InputText v-model="locationForm.building" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('room').value }}</label>
          <InputText v-model="locationForm.room" class="w-full" />
        </div>
      </div>
      <template #footer>
        <Button :label="t('cancel').value" text @click="showLocationDialog = false" />
        <Button :label="t('save').value" icon="pi pi-check" @click="saveLocation" />
      </template>
    </Dialog>

    <!-- Supplier Dialog -->
    <Dialog v-model:visible="showSupplierDialog" modal :header="t('supplier').value" :style="{ width: '400px' }">
      <div class="flex flex-col gap-4 mt-2">
        <div>
          <label class="text-sm font-medium">{{ t('name').value }} *</label>
          <InputText v-model="supplierForm.name" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('contactEmail').value }}</label>
          <InputText v-model="supplierForm.contact_email" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('phone').value }}</label>
          <InputText v-model="supplierForm.phone" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('website').value }}</label>
          <InputText v-model="supplierForm.website" class="w-full" />
        </div>
        <div>
          <label class="text-sm font-medium">{{ t('notes').value }}</label>
          <Textarea v-model="supplierForm.notes" rows="2" class="w-full" />
        </div>
      </div>
      <template #footer>
        <Button :label="t('cancel').value" text @click="showSupplierDialog = false" />
        <Button :label="t('save').value" icon="pi pi-check" @click="saveSupplier" />
      </template>
    </Dialog>

    <!-- Link IP Dialog -->
    <Dialog v-model:visible="showLinkIpDialog" modal :header="t('linkIp').value" :style="{ width: '400px' }">
      <div class="flex flex-col gap-4 mt-2">
        <div v-if="linkingEquipment">
          <p class="mb-4">{{ t('equipment').value }}: <strong>{{ linkingEquipment.name }}</strong></p>

          <div v-if="linkingEquipment.ip_addresses?.length" class="mb-4">
            <label class="text-sm font-medium block mb-2">{{ t('linkedIps').value }}</label>
            <div v-for="ip in linkingEquipment.ip_addresses" :key="ip.id" class="flex items-center justify-between p-2 border rounded mb-1">
              <span class="font-mono">{{ ip.address }}</span>
              <Button icon="pi pi-times" text rounded severity="danger" size="small" @click="unlinkIp(ip.id)" />
            </div>
          </div>

          <div>
            <label class="text-sm font-medium">{{ t('availableIps').value }}</label>
            <Dropdown v-model="selectedIpToLink" :options="availableIps" optionLabel="address" optionValue="id" :placeholder="t('selectIp').value" class="w-full" showClear />
          </div>
        </div>
      </div>
      <template #footer>
        <Button :label="t('cancel').value" text @click="showLinkIpDialog = false" />
        <Button :label="t('linkIp').value" icon="pi pi-link" @click="linkIp" :disabled="!selectedIpToLink" />
      </template>
    </Dialog>

    <!-- Delete Equipment Confirmation -->
    <Dialog v-model:visible="showDeleteEquipmentDialog" modal :header="t('deleted').value" :style="{ width: '400px' }">
      <div class="flex items-center gap-3">
        <i class="pi pi-exclamation-triangle text-red-500 text-2xl"></i>
        <span>{{ t('confirmDeleteScript').value }} <b>{{ deletingEquipment?.name }}</b>?</span>
      </div>
      <template #footer>
        <Button :label="t('cancel').value" text @click="showDeleteEquipmentDialog = false" />
        <Button :label="t('deleted').value" icon="pi pi-trash" severity="danger" @click="deleteEquipment" />
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
const equipment = ref([]);
const manufacturers = ref([]);
const models = ref([]);
const types = ref([]);
const locations = ref([]);
const suppliers = ref([]);
const availableIps = ref([]);
const expandedRows = ref({});

// Filters
const filterType = ref(null);
const filterStatus = ref(null);
const filterLocation = ref(null);

// Dialogs
const showEquipmentDialog = ref(false);
const showManufacturerDialog = ref(false);
const showModelDialog = ref(false);
const showTypeDialog = ref(false);
const showLocationDialog = ref(false);
const showSupplierDialog = ref(false);
const showLinkIpDialog = ref(false);
const showDeleteEquipmentDialog = ref(false);

// Forms
const editingEquipment = ref(null);
const editingManufacturer = ref(null);
const editingModel = ref(null);
const editingType = ref(null);
const editingLocation = ref(null);
const editingSupplier = ref(null);
const linkingEquipment = ref(null);
const deletingEquipment = ref(null);
const selectedIpToLink = ref(null);

const equipmentForm = ref({
  name: '', serial_number: '', asset_tag: '', status: 'in_service',
  purchase_date: null, warranty_expiry: null, notes: '',
  model_id: null, location_id: null, supplier_id: null
});

const manufacturerForm = ref({ name: '', website: '', notes: '' });
const modelForm = ref({ name: '', manufacturer_id: null, equipment_type_id: null });
const typeForm = ref({ name: '', icon: 'pi-box' });
const locationForm = ref({ site: '', building: '', room: '' });
const supplierForm = ref({ name: '', contact_email: '', phone: '', website: '', notes: '' });

// Options
const statusOptions = computed(() => [
  { label: t('inService').value, value: 'in_service' },
  { label: t('inStock').value, value: 'in_stock' },
  { label: t('retired').value, value: 'retired' },
  { label: t('maintenance').value, value: 'maintenance' }
]);

const typeOptions = computed(() => types.value.map(t => ({ id: t.id, name: t.name })));

const locationOptions = computed(() => locations.value.map(l => ({
  id: l.id,
  label: `${l.site}${l.building ? ' / ' + l.building : ''}${l.room ? ' / ' + l.room : ''}`
})));

const iconOptions = ['pi-server', 'pi-desktop', 'pi-mobile', 'pi-box', 'pi-database', 'pi-wifi', 'pi-globe', 'pi-print', 'pi-shield', 'pi-bolt'];

// Helpers
const getStatusSeverity = (status) => {
  switch (status) {
    case 'in_service': return 'success';
    case 'in_stock': return 'info';
    case 'retired': return 'secondary';
    case 'maintenance': return 'warning';
    default: return null;
  }
};

const getStatusLabel = (status) => {
  const opt = statusOptions.value.find(o => o.value === status);
  return opt ? opt.label : status;
};

const formatDate = (date) => {
  if (!date) return '-';
  return new Date(date).toLocaleDateString();
};

// Data loading
const loadData = async () => {
  try {
    const [eqRes, mfRes, mdRes, tpRes, lcRes, spRes] = await Promise.all([
      api.get('/inventory/equipment/'),
      api.get('/inventory/manufacturers/'),
      api.get('/inventory/models/'),
      api.get('/inventory/types/'),
      api.get('/inventory/locations/'),
      api.get('/inventory/suppliers/')
    ]);
    equipment.value = eqRes.data;
    manufacturers.value = mfRes.data;
    models.value = mdRes.data;
    types.value = tpRes.data;
    locations.value = lcRes.data;
    suppliers.value = spRes.data;
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || 'Failed to load data' });
  }
};

const loadAvailableIps = async () => {
  try {
    const res = await api.get('/inventory/available-ips/');
    availableIps.value = res.data;
  } catch (e) {
    console.error(e);
  }
};

// Equipment CRUD
const openEquipmentDialog = (eq = null) => {
  editingEquipment.value = eq;
  if (eq) {
    equipmentForm.value = {
      name: eq.name,
      serial_number: eq.serial_number || '',
      asset_tag: eq.asset_tag || '',
      status: eq.status,
      purchase_date: eq.purchase_date ? new Date(eq.purchase_date) : null,
      warranty_expiry: eq.warranty_expiry ? new Date(eq.warranty_expiry) : null,
      notes: eq.notes || '',
      model_id: eq.model_id,
      location_id: eq.location_id,
      supplier_id: eq.supplier_id
    };
  } else {
    equipmentForm.value = {
      name: '', serial_number: '', asset_tag: '', status: 'in_service',
      purchase_date: null, warranty_expiry: null, notes: '',
      model_id: null, location_id: null, supplier_id: null
    };
  }
  showEquipmentDialog.value = true;
};

const saveEquipment = async () => {
  if (!equipmentForm.value.name) {
    toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('fillRequiredFields').value });
    return;
  }
  try {
    const data = { ...equipmentForm.value };
    if (data.purchase_date) data.purchase_date = data.purchase_date.toISOString();
    if (data.warranty_expiry) data.warranty_expiry = data.warranty_expiry.toISOString();

    if (editingEquipment.value) {
      await api.put(`/inventory/equipment/${editingEquipment.value.id}`, data);
      toast.add({ severity: 'success', summary: t('success').value, detail: t('equipmentUpdated').value });
    } else {
      await api.post('/inventory/equipment/', data);
      toast.add({ severity: 'success', summary: t('success').value, detail: t('equipmentCreated').value });
    }
    showEquipmentDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const confirmDeleteEquipment = (eq) => {
  deletingEquipment.value = eq;
  showDeleteEquipmentDialog.value = true;
};

const deleteEquipment = async () => {
  try {
    await api.delete(`/inventory/equipment/${deletingEquipment.value.id}`);
    toast.add({ severity: 'success', summary: t('deleted').value, detail: t('equipmentDeleted').value });
    showDeleteEquipmentDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

// IP Linking
const openLinkIpDialog = async (eq) => {
  linkingEquipment.value = eq;
  selectedIpToLink.value = null;
  await loadAvailableIps();
  showLinkIpDialog.value = true;
};

const linkIp = async () => {
  if (!selectedIpToLink.value) return;
  try {
    await api.post(`/inventory/equipment/${linkingEquipment.value.id}/link-ip`, { ip_address_id: selectedIpToLink.value });
    toast.add({ severity: 'success', summary: t('success').value, detail: t('ipLinked').value });
    showLinkIpDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const unlinkIp = async (ipId) => {
  try {
    await api.delete(`/inventory/equipment/${linkingEquipment.value.id}/unlink-ip/${ipId}`);
    toast.add({ severity: 'success', summary: t('success').value, detail: t('ipUnlinked').value });
    loadData();
    // Refresh the linking equipment data
    const res = await api.get(`/inventory/equipment/${linkingEquipment.value.id}`);
    linkingEquipment.value = res.data;
    await loadAvailableIps();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

// Manufacturer CRUD
const openManufacturerDialog = (mf = null) => {
  editingManufacturer.value = mf;
  manufacturerForm.value = mf ? { ...mf } : { name: '', website: '', notes: '' };
  showManufacturerDialog.value = true;
};

const saveManufacturer = async () => {
  if (!manufacturerForm.value.name) {
    toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('fillRequiredFields').value });
    return;
  }
  try {
    if (editingManufacturer.value) {
      await api.put(`/inventory/manufacturers/${editingManufacturer.value.id}`, manufacturerForm.value);
    } else {
      await api.post('/inventory/manufacturers/', manufacturerForm.value);
    }
    toast.add({ severity: 'success', summary: t('success').value, detail: t('manufacturerCreated').value });
    showManufacturerDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const deleteManufacturer = async (id) => {
  if (!confirm('Delete this manufacturer?')) return;
  try {
    await api.delete(`/inventory/manufacturers/${id}`);
    toast.add({ severity: 'success', summary: t('deleted').value, detail: t('manufacturerDeleted').value });
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('cannotDeleteHasItems').value });
  }
};

// Model CRUD
const openModelDialog = (md = null) => {
  editingModel.value = md;
  modelForm.value = md ? { name: md.name, manufacturer_id: md.manufacturer_id, equipment_type_id: md.equipment_type_id } : { name: '', manufacturer_id: null, equipment_type_id: null };
  showModelDialog.value = true;
};

const saveModel = async () => {
  if (!modelForm.value.name || !modelForm.value.manufacturer_id || !modelForm.value.equipment_type_id) {
    toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('fillRequiredFields').value });
    return;
  }
  try {
    if (editingModel.value) {
      await api.put(`/inventory/models/${editingModel.value.id}`, modelForm.value);
    } else {
      await api.post('/inventory/models/', modelForm.value);
    }
    toast.add({ severity: 'success', summary: t('success').value, detail: t('modelCreated').value });
    showModelDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const deleteModel = async (id) => {
  if (!confirm('Delete this model?')) return;
  try {
    await api.delete(`/inventory/models/${id}`);
    toast.add({ severity: 'success', summary: t('deleted').value, detail: t('modelDeleted').value });
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('cannotDeleteHasItems').value });
  }
};

// Type CRUD
const openTypeDialog = (tp = null) => {
  editingType.value = tp;
  typeForm.value = tp ? { ...tp } : { name: '', icon: 'pi-box' };
  showTypeDialog.value = true;
};

const saveType = async () => {
  if (!typeForm.value.name) {
    toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('fillRequiredFields').value });
    return;
  }
  try {
    if (editingType.value) {
      await api.put(`/inventory/types/${editingType.value.id}`, typeForm.value);
    } else {
      await api.post('/inventory/types/', typeForm.value);
    }
    toast.add({ severity: 'success', summary: t('success').value, detail: t('typeCreated').value });
    showTypeDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const deleteType = async (id) => {
  if (!confirm('Delete this type?')) return;
  try {
    await api.delete(`/inventory/types/${id}`);
    toast.add({ severity: 'success', summary: t('deleted').value, detail: t('typeDeleted').value });
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('cannotDeleteHasItems').value });
  }
};

// Location CRUD
const openLocationDialog = (lc = null) => {
  editingLocation.value = lc;
  locationForm.value = lc ? { ...lc } : { site: '', building: '', room: '' };
  showLocationDialog.value = true;
};

const saveLocation = async () => {
  if (!locationForm.value.site) {
    toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('fillRequiredFields').value });
    return;
  }
  try {
    if (editingLocation.value) {
      await api.put(`/inventory/locations/${editingLocation.value.id}`, locationForm.value);
    } else {
      await api.post('/inventory/locations/', locationForm.value);
    }
    toast.add({ severity: 'success', summary: t('success').value, detail: t('locationCreated').value });
    showLocationDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const deleteLocation = async (id) => {
  if (!confirm('Delete this location?')) return;
  try {
    await api.delete(`/inventory/locations/${id}`);
    toast.add({ severity: 'success', summary: t('deleted').value, detail: t('locationDeleted').value });
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('cannotDeleteHasItems').value });
  }
};

// Supplier CRUD
const openSupplierDialog = (sp = null) => {
  editingSupplier.value = sp;
  supplierForm.value = sp ? { ...sp } : { name: '', contact_email: '', phone: '', website: '', notes: '' };
  showSupplierDialog.value = true;
};

const saveSupplier = async () => {
  if (!supplierForm.value.name) {
    toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('fillRequiredFields').value });
    return;
  }
  try {
    if (editingSupplier.value) {
      await api.put(`/inventory/suppliers/${editingSupplier.value.id}`, supplierForm.value);
    } else {
      await api.post('/inventory/suppliers/', supplierForm.value);
    }
    toast.add({ severity: 'success', summary: t('success').value, detail: t('supplierCreated').value });
    showSupplierDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const deleteSupplier = async (id) => {
  if (!confirm('Delete this supplier?')) return;
  try {
    await api.delete(`/inventory/suppliers/${id}`);
    toast.add({ severity: 'success', summary: t('deleted').value, detail: t('supplierDeleted').value });
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('cannotDeleteHasItems').value });
  }
};

onMounted(loadData);
</script>
