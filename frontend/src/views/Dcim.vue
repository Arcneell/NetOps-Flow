<template>
  <div class="flex gap-6 h-full">
    <!-- Sidebar Menu -->
    <div class="w-64 flex-shrink-0">
      <div class="card p-0 overflow-hidden">
        <div class="p-4 border-b" style="border-color: var(--border-color);">
          <h3 class="font-bold text-lg">{{ t('dcim.title') }}</h3>
        </div>
        <nav class="p-2">
          <div
            @click="activeSection = 'racks'"
            :class="['flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-colors', activeSection === 'racks' ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800']"
          >
            <i class="pi pi-server"></i>
            <span class="font-medium">{{ t('dcim.racks') }}</span>
          </div>

          <div
            @click="activeSection = 'pdus'"
            :class="['flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-colors', activeSection === 'pdus' ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800']"
          >
            <i class="pi pi-bolt"></i>
            <span class="font-medium">{{ t('dcim.pdus') }}</span>
          </div>

          <div
            @click="activeSection = 'rackView'"
            :class="['flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-colors', activeSection === 'rackView' ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800']"
          >
            <i class="pi pi-th-large"></i>
            <span class="font-medium">{{ t('dcim.rackView') }}</span>
          </div>
        </nav>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 overflow-hidden">
      <!-- Racks Section -->
      <div v-if="activeSection === 'racks'" class="card h-full flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('dcim.racks') }}</h3>
          <Button :label="t('dcim.newRack')" icon="pi pi-plus" @click="openRackDialog()" />
        </div>

        <div class="flex gap-3 mb-4">
          <Dropdown v-model="filterLocation" :options="locationOptions" optionLabel="label" optionValue="id" :placeholder="t('filters.allLocations')" showClear class="w-64" />
        </div>

        <div class="flex-1 overflow-auto">
          <DataTable :value="filteredRacks" stripedRows paginator :rows="10" class="text-sm">
            <Column field="name" :header="t('common.name')" sortable></Column>
            <Column :header="t('inventory.location')">
              <template #body="slotProps">
                <span v-if="slotProps.data.location">
                  {{ slotProps.data.location.site }}
                  <span v-if="slotProps.data.location.building"> / {{ slotProps.data.location.building }}</span>
                  <span v-if="slotProps.data.location.room"> / {{ slotProps.data.location.room }}</span>
                </span>
              </template>
            </Column>
            <Column field="height_u" :header="t('dcim.heightU')" style="width: 100px">
              <template #body="slotProps">{{ slotProps.data.height_u }}U</template>
            </Column>
            <Column :header="t('dcim.dimensions')" style="width: 150px">
              <template #body="slotProps">{{ slotProps.data.width_mm }} x {{ slotProps.data.depth_mm }} mm</template>
            </Column>
            <Column field="max_power_kw" :header="t('dcim.maxPower')" style="width: 120px">
              <template #body="slotProps">{{ slotProps.data.max_power_kw ? slotProps.data.max_power_kw + ' kW' : '-' }}</template>
            </Column>
            <Column :header="t('common.actions')" style="width: 120px">
              <template #body="slotProps">
                <div class="flex gap-1">
                  <Button icon="pi pi-eye" text rounded size="small" @click="viewRackLayout(slotProps.data)" v-tooltip.top="t('dcim.viewLayout')" />
                  <Button icon="pi pi-pencil" text rounded size="small" @click="openRackDialog(slotProps.data)" v-tooltip.top="t('common.edit')" />
                  <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="confirmDeleteRack(slotProps.data)" v-tooltip.top="t('common.delete')" />
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
      </div>

      <!-- PDUs Section -->
      <div v-if="activeSection === 'pdus'" class="card h-full flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('dcim.pdus') }}</h3>
          <Button :label="t('dcim.newPdu')" icon="pi pi-plus" @click="openPduDialog()" />
        </div>

        <div class="flex-1 overflow-auto">
          <DataTable :value="pdus" stripedRows paginator :rows="10" class="text-sm">
            <Column field="name" :header="t('common.name')" sortable></Column>
            <Column :header="t('dcim.racks')">
              <template #body="slotProps">
                {{ getRackName(slotProps.data.rack_id) || '-' }}
              </template>
            </Column>
            <Column field="pdu_type" :header="t('inventory.type')">
              <template #body="slotProps">
                <Tag :value="slotProps.data.pdu_type" />
              </template>
            </Column>
            <Column field="total_ports" :header="t('dcim.ports')" style="width: 100px"></Column>
            <Column :header="t('dcim.maxPower')" style="width: 150px">
              <template #body="slotProps">
                {{ slotProps.data.max_amps ? slotProps.data.max_amps + 'A' : '-' }} / {{ slotProps.data.voltage }}V
              </template>
            </Column>
            <Column field="phase" :header="t('dcim.phase')" style="width: 100px"></Column>
            <Column :header="t('common.actions')" style="width: 100px">
              <template #body="slotProps">
                <div class="flex gap-1">
                  <Button icon="pi pi-pencil" text rounded size="small" @click="openPduDialog(slotProps.data)" />
                  <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="confirmDeletePdu(slotProps.data)" />
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
      </div>

      <!-- Rack View Section -->
      <div v-if="activeSection === 'rackView'" class="card h-full flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('dcim.rackView') }}</h3>
          <Dropdown v-model="selectedRackId" :options="racks" optionLabel="name" optionValue="id" :placeholder="t('dcim.selectRack')" class="w-64" @change="loadRackLayout" />
        </div>

        <div v-if="rackLayout" class="flex-1 overflow-auto">
          <div class="flex gap-6">
            <!-- Rack Visualization -->
            <div class="flex-1">
              <div class="rack-container">
                <div class="rack-header">{{ rackLayout.rack?.name }}</div>
                <div class="rack-body">
                  <div class="flex">
                    <!-- U Numbers (Left) -->
                    <div class="rack-u-numbers">
                      <div v-for="slot in rackLayout.layout" :key="`u-left-${slot.u}`" class="rack-u-label">
                        {{ slot.u }}
                      </div>
                    </div>

                    <!-- Equipment Slots -->
                    <div class="rack-slots">
                      <div
                        v-for="slot in rackLayout.layout"
                        :key="`slot-${slot.u}`"
                        class="rack-slot"
                        :class="getSlotClass(slot)"
                        @click="handleSlotClick(slot)"
                        v-tooltip.right="getEquipmentTooltip(slot.equipment)"
                      >
                        <template v-if="slot.equipment?.is_start">
                          <div class="rack-equipment-content">
                            <div class="font-semibold">{{ slot.equipment.name }}</div>
                            <div class="text-xs opacity-80">
                              {{ slot.equipment.model_name || 'Unknown Model' }}
                              <span v-if="slot.equipment.height_u > 1"> • {{ slot.equipment.height_u }}U</span>
                            </div>
                          </div>
                        </template>
                        <template v-else-if="!slot.equipment">
                          <span class="rack-empty-label">{{ t('dcim.empty') }}</span>
                        </template>
                      </div>
                    </div>

                    <!-- U Numbers (Right) -->
                    <div class="rack-u-numbers">
                      <div v-for="slot in rackLayout.layout" :key="`u-right-${slot.u}`" class="rack-u-label">
                        {{ slot.u }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Sidebar: PDUs & Unassigned Equipment -->
            <div class="w-80 space-y-6">
              <!-- PDUs in Rack -->
              <div>
                <h4 class="font-semibold mb-3 flex items-center gap-2">
                  <i class="pi pi-bolt text-yellow-500"></i>
                  {{ t('dcim.pdus') }}
                </h4>
                <div v-if="rackLayout.pdus?.length">
                  <div v-for="pdu in rackLayout.pdus" :key="pdu.id" class="p-3 rounded-lg mb-2 border" style="border-color: var(--border-color); background: var(--surface-card);">
                    {{ pdu.name }}
                  </div>
                </div>
                <p v-else class="opacity-50 text-sm">{{ t('dcim.noPdus') }}</p>
              </div>

              <!-- Unassigned Equipment -->
              <div>
                <h4 class="font-semibold mb-3 flex items-center gap-2">
                  <i class="pi pi-box"></i>
                  {{ t('dcim.unassignedEquipment') }}
                </h4>
                <div v-if="rackLayout.unassigned_equipment?.length">
                  <div
                    v-for="eq in rackLayout.unassigned_equipment"
                    :key="eq.id"
                    class="p-3 rounded-lg mb-2 border cursor-pointer hover:border-blue-500 transition-colors"
                    style="border-color: var(--border-color); background: var(--surface-card);"
                    @click="openPlacementDialog(eq)"
                    v-tooltip.left="getUnassignedTooltip(eq)"
                  >
                    <div class="font-medium">{{ eq.name }}</div>
                    <div class="text-xs opacity-70 mt-1">{{ eq.model_name || 'Unknown Model' }} • {{ eq.height_u }}U</div>
                    <div class="text-xs text-blue-500 mt-1">{{ t('dcim.clickToPlace') }}</div>
                  </div>
                </div>
                <p v-else class="opacity-50 text-sm">{{ t('dcim.noUnassigned') }}</p>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="flex-1 flex items-center justify-center opacity-50">
          {{ t('dcim.selectRackToView') }}
        </div>
      </div>
    </div>

    <!-- Rack Dialog -->
    <Dialog v-model:visible="showRackDialog" modal :header="editingRack ? t('dcim.editRack') : t('dcim.newRack')" :style="{ width: '500px' }">
      <div class="flex flex-col gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('common.name') }} <span class="text-red-500">*</span></label>
          <InputText v-model="rackForm.name" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('inventory.location') }} <span class="text-red-500">*</span></label>
          <Dropdown v-model="rackForm.location_id" :options="locationOptions" optionLabel="label" optionValue="id" class="w-full" />
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('dcim.heightU') }}</label>
            <InputNumber v-model="rackForm.height_u" class="w-full" :min="1" :max="50" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('dcim.widthMm') }}</label>
            <InputNumber v-model="rackForm.width_mm" class="w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('dcim.depthMm') }}</label>
            <InputNumber v-model="rackForm.depth_mm" class="w-full" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('dcim.maxPowerKw') }}</label>
          <InputNumber v-model="rackForm.max_power_kw" class="w-full" :minFractionDigits="1" :maxFractionDigits="2" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('inventory.notes') }}</label>
          <Textarea v-model="rackForm.notes" rows="2" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showRackDialog = false" />
          <Button :label="t('common.save')" icon="pi pi-check" @click="saveRack" />
        </div>
      </template>
    </Dialog>

    <!-- PDU Dialog -->
    <Dialog v-model:visible="showPduDialog" modal :header="editingPdu ? t('dcim.editPdu') : t('dcim.newPdu')" :style="{ width: '500px' }">
      <div class="flex flex-col gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('common.name') }} <span class="text-red-500">*</span></label>
          <InputText v-model="pduForm.name" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('dcim.racks') }}</label>
          <Dropdown v-model="pduForm.rack_id" :options="racks" optionLabel="name" optionValue="id" class="w-full" showClear />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('inventory.type') }}</label>
            <Dropdown v-model="pduForm.pdu_type" :options="pduTypeOptions" class="w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('dcim.totalPorts') }}</label>
            <InputNumber v-model="pduForm.total_ports" class="w-full" :min="1" />
          </div>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('dcim.maxAmps') }}</label>
            <InputNumber v-model="pduForm.max_amps" class="w-full" :minFractionDigits="1" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('dcim.voltage') }}</label>
            <Dropdown v-model="pduForm.voltage" :options="voltageOptions" class="w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('dcim.phase') }}</label>
            <Dropdown v-model="pduForm.phase" :options="phaseOptions" class="w-full" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('inventory.notes') }}</label>
          <Textarea v-model="pduForm.notes" rows="2" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showPduDialog = false" />
          <Button :label="t('common.save')" icon="pi pi-check" @click="savePdu" />
        </div>
      </template>
    </Dialog>

    <!-- Equipment Placement Dialog -->
    <Dialog v-model:visible="showPlacementDialog" modal :header="t('dcim.placeEquipment')" :style="{ width: '400px' }">
      <div v-if="equipmentToPlace" class="flex flex-col gap-4">
        <div class="p-3 border rounded-lg" style="border-color: var(--border-color); background: var(--surface-100);">
          <div class="font-semibold">{{ equipmentToPlace.name }}</div>
          <div class="text-sm opacity-70 mt-1">{{ equipmentToPlace.model_name }}</div>
          <div class="text-sm mt-1">{{ t('dcim.heightU') }}: {{ equipmentToPlace.height_u }}U</div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('dcim.position') }} (U) <span class="text-red-500">*</span></label>
          <InputNumber v-model="placementPosition" class="w-full" :min="1" :max="rackLayout?.rack?.height_u || 42" />
          <small class="opacity-70">{{ t('dcim.selectPosition', { max: rackLayout?.rack?.height_u || 42 }) }}</small>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showPlacementDialog = false" />
          <Button :label="t('dcim.place')" icon="pi pi-check" @click="placeEquipment" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import api from '../api';

const { t } = useI18n();
const toast = useToast();
const router = useRouter();

// Active section
const activeSection = ref('racks');

// Data
const racks = ref([]);
const pdus = ref([]);
const locations = ref([]);
const rackLayout = ref(null);
const selectedRackId = ref(null);

// Filters
const filterLocation = ref(null);

// Dialogs
const showRackDialog = ref(false);
const showPduDialog = ref(false);
const showPlacementDialog = ref(false);

// Editing states
const editingRack = ref(null);
const editingPdu = ref(null);

// Equipment placement
const equipmentToPlace = ref(null);
const placementPosition = ref(1);

// Forms
const rackForm = ref({
  name: '', location_id: null, height_u: 42, width_mm: 600, depth_mm: 1000, max_power_kw: null, notes: ''
});

const pduForm = ref({
  name: '', rack_id: null, pdu_type: 'basic', total_ports: 8, max_amps: null, voltage: 230, phase: 'single', notes: ''
});

// Options
const pduTypeOptions = ['basic', 'metered', 'switched', 'smart'];
const voltageOptions = [120, 230, 400];
const phaseOptions = ['single', 'three'];

const locationOptions = computed(() => locations.value.map(l => ({
  id: l.id,
  label: `${l.site}${l.building ? ' / ' + l.building : ''}${l.room ? ' / ' + l.room : ''}`
})));

const filteredRacks = computed(() => {
  if (!filterLocation.value) return racks.value;
  return racks.value.filter(r => r.location_id === filterLocation.value);
});

// Helpers
const getRackName = (rackId) => {
  const rack = racks.value.find(r => r.id === rackId);
  return rack?.name;
};

// Data loading
const loadData = async () => {
  try {
    const [racksRes, pdusRes, locationsRes] = await Promise.all([
      api.get('/dcim/racks/'),
      api.get('/dcim/pdus/'),
      api.get('/inventory/locations/')
    ]);
    racks.value = racksRes.data;
    pdus.value = pdusRes.data;
    locations.value = locationsRes.data;
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || 'Failed to load data' });
  }
};

const loadRackLayout = async () => {
  if (!selectedRackId.value) {
    rackLayout.value = null;
    return;
  }
  try {
    const response = await api.get(`/dcim/racks/${selectedRackId.value}/layout`);
    rackLayout.value = response.data;
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || 'Failed to load rack layout' });
  }
};

const viewRackLayout = (rack) => {
  selectedRackId.value = rack.id;
  activeSection.value = 'rackView';
  loadRackLayout();
};

// Rack CRUD
const openRackDialog = (rack = null) => {
  editingRack.value = rack;
  if (rack) {
    rackForm.value = { ...rack };
  } else {
    rackForm.value = { name: '', location_id: null, height_u: 42, width_mm: 600, depth_mm: 1000, max_power_kw: null, notes: '' };
  }
  showRackDialog.value = true;
};

const saveRack = async () => {
  if (!rackForm.value.name || !rackForm.value.location_id) {
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.fillRequiredFields') });
    return;
  }
  try {
    if (editingRack.value) {
      await api.put(`/dcim/racks/${editingRack.value.id}`, rackForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('dcim.rackUpdated') });
    } else {
      await api.post('/dcim/racks/', rackForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('dcim.rackCreated') });
    }
    showRackDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }
};

const confirmDeleteRack = async (rack) => {
  if (!confirm(t('common.confirmDeleteItem'))) return;
  try {
    await api.delete(`/dcim/racks/${rack.id}`);
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('dcim.rackDeleted') });
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }
};

// PDU CRUD
const openPduDialog = (pdu = null) => {
  editingPdu.value = pdu;
  if (pdu) {
    pduForm.value = { ...pdu };
  } else {
    pduForm.value = { name: '', rack_id: null, pdu_type: 'basic', total_ports: 8, max_amps: null, voltage: 230, phase: 'single', notes: '' };
  }
  showPduDialog.value = true;
};

const savePdu = async () => {
  if (!pduForm.value.name) {
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.fillRequiredFields') });
    return;
  }
  try {
    if (editingPdu.value) {
      await api.put(`/dcim/pdus/${editingPdu.value.id}`, pduForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('dcim.pduUpdated') });
    } else {
      await api.post('/dcim/pdus/', pduForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('dcim.pduCreated') });
    }
    showPduDialog.value = false;
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }
};

const confirmDeletePdu = async (pdu) => {
  if (!confirm(t('common.confirmDeleteItem'))) return;
  try {
    await api.delete(`/dcim/pdus/${pdu.id}`);
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('dcim.pduDeleted') });
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }
};

// Rack visualization helpers
const getStatusColor = (status) => {
  const colors = {
    'in_service': 'bg-blue-600 text-white',
    'maintenance': 'bg-orange-500 text-white',
    'retired': 'bg-gray-500 text-white',
    'stock': 'bg-green-500 text-white'
  };
  return colors[status] || 'bg-gray-400 text-white';
};

const getSlotClass = (slot) => {
  if (!slot.equipment) {
    return 'rack-slot-empty';
  }
  if (slot.equipment.is_start) {
    return `rack-slot-equipment ${getStatusColor(slot.equipment.status)}`;
  }
  return `rack-slot-continuation ${getStatusColor(slot.equipment.status)}`;
};

const getEquipmentTooltip = (equipment) => {
  if (!equipment) return null;
  const parts = [
    `<strong>${equipment.name}</strong>`,
    equipment.manufacturer_name ? `${equipment.manufacturer_name} ${equipment.model_name || ''}` : (equipment.model_name || ''),
    equipment.serial_number ? `S/N: ${equipment.serial_number}` : null,
    equipment.asset_tag ? `Asset: ${equipment.asset_tag}` : null,
    equipment.management_ip ? `IP: ${equipment.management_ip}` : null,
    `Status: ${equipment.status}`
  ];
  return parts.filter(p => p).join('<br>');
};

const getUnassignedTooltip = (eq) => {
  const parts = [
    `<strong>${eq.name}</strong>`,
    eq.manufacturer_name ? `${eq.manufacturer_name} ${eq.model_name || ''}` : (eq.model_name || ''),
    eq.serial_number ? `S/N: ${eq.serial_number}` : null,
    eq.asset_tag ? `Asset: ${eq.asset_tag}` : null,
    eq.management_ip ? `IP: ${eq.management_ip}` : null,
    `Height: ${eq.height_u}U`
  ];
  return parts.filter(p => p).join('<br>');
};

const handleSlotClick = (slot) => {
  if (slot.equipment?.is_start && slot.equipment.id) {
    // Navigate to equipment details in inventory
    router.push({ name: 'Inventory', query: { equipmentId: slot.equipment.id } });
  }
};

// Equipment placement
const openPlacementDialog = (equipment) => {
  equipmentToPlace.value = equipment;
  placementPosition.value = 1;
  showPlacementDialog.value = true;
};

const placeEquipment = async () => {
  if (!equipmentToPlace.value || !placementPosition.value) {
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.fillRequiredFields') });
    return;
  }
  try {
    await api.post(`/dcim/racks/${selectedRackId.value}/place-equipment`, null, {
      params: {
        equipment_id: equipmentToPlace.value.id,
        position_u: placementPosition.value
      }
    });
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('dcim.equipmentPlaced') });
    showPlacementDialog.value = false;
    loadRackLayout();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }
};

onMounted(loadData);
</script>

<style scoped>
/* Rack Container - Hardware Style */
.rack-container {
  border: 3px solid #4a5568;
  border-radius: 8px;
  background: linear-gradient(to bottom, #2d3748, #1a202c);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3), inset 0 2px 4px rgba(255, 255, 255, 0.1);
  overflow: hidden;
  max-width: 800px;
  margin: 0 auto;
}

.rack-header {
  background: linear-gradient(to bottom, #4a5568, #2d3748);
  color: #e2e8f0;
  font-weight: bold;
  font-size: 1.1rem;
  text-align: center;
  padding: 1rem;
  border-bottom: 2px solid #718096;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.rack-body {
  padding: 1rem 0.5rem;
  background: #1a202c;
}

/* U Numbers on sides */
.rack-u-numbers {
  display: flex;
  flex-direction: column-reverse;
  background: #2d3748;
  border: 1px solid #4a5568;
  border-radius: 4px;
}

.rack-u-label {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: bold;
  color: #cbd5e0;
  border-bottom: 1px solid #4a5568;
  font-family: 'Courier New', monospace;
  min-width: 40px;
}

.rack-u-label:last-child {
  border-bottom: none;
}

/* Equipment Slots */
.rack-slots {
  flex: 1;
  display: flex;
  flex-direction: column-reverse;
  margin: 0 0.5rem;
  border: 2px solid #4a5568;
  border-radius: 4px;
  background: #2d3748;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.4);
}

.rack-slot {
  height: 44px;
  border-bottom: 1px solid #4a5568;
  display: flex;
  align-items: center;
  padding: 0 0.75rem;
  transition: all 0.2s ease;
  position: relative;
}

.rack-slot:last-child {
  border-bottom: none;
}

/* Empty Slot */
.rack-slot-empty {
  background: repeating-linear-gradient(
    45deg,
    #2d3748,
    #2d3748 10px,
    #1a202c 10px,
    #1a202c 20px
  );
  cursor: default;
}

.rack-slot-empty:hover {
  background: repeating-linear-gradient(
    45deg,
    #374151,
    #374151 10px,
    #1f2937 10px,
    #1f2937 20px
  );
}

.rack-empty-label {
  font-size: 0.75rem;
  color: #718096;
  font-style: italic;
}

/* Equipment Slot */
.rack-slot-equipment {
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  cursor: pointer;
}

.rack-slot-equipment:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
  transform: translateX(2px);
}

/* Continuation slot (middle of multi-U equipment) */
.rack-slot-continuation {
  border-left: 1px solid rgba(255, 255, 255, 0.2);
  border-right: 1px solid rgba(255, 255, 255, 0.2);
  opacity: 0.9;
}

.rack-equipment-content {
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Status-specific colors are applied via getStatusColor function */
</style>
