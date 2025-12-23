<template>
  <div class="flex gap-6 h-full">
    <!-- Sidebar Menu -->
    <div class="w-64 flex-shrink-0">
      <div class="card p-0 overflow-hidden">
        <div class="p-4 border-b" style="border-color: var(--border-color);">
          <h3 class="font-bold text-lg">{{ t('inventory').value }}</h3>
        </div>
        <nav class="p-2">
          <div
            @click="activeSection = 'equipment'"
            :class="['flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-colors', activeSection === 'equipment' ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800']"
          >
            <i class="pi pi-box"></i>
            <span class="font-medium">{{ t('equipment').value }}</span>
          </div>

          <div class="px-4 py-2 text-xs font-semibold text-gray-500 uppercase mt-4">{{ t('configuration').value }}</div>

          <div
            @click="activeSection = 'manufacturers'"
            :class="['flex items-center gap-3 px-4 py-2.5 rounded-lg cursor-pointer transition-colors text-sm', activeSection === 'manufacturers' ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800']"
          >
            <i class="pi pi-building"></i>
            <span>{{ t('manufacturers').value }}</span>
          </div>

          <div
            @click="activeSection = 'models'"
            :class="['flex items-center gap-3 px-4 py-2.5 rounded-lg cursor-pointer transition-colors text-sm', activeSection === 'models' ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800']"
          >
            <i class="pi pi-th-large"></i>
            <span>{{ t('equipmentModels').value }}</span>
          </div>

          <div
            @click="activeSection = 'types'"
            :class="['flex items-center gap-3 px-4 py-2.5 rounded-lg cursor-pointer transition-colors text-sm', activeSection === 'types' ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800']"
          >
            <i class="pi pi-tags"></i>
            <span>{{ t('equipmentTypes').value }}</span>
          </div>

          <div
            @click="activeSection = 'locations'"
            :class="['flex items-center gap-3 px-4 py-2.5 rounded-lg cursor-pointer transition-colors text-sm', activeSection === 'locations' ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800']"
          >
            <i class="pi pi-map-marker"></i>
            <span>{{ t('locations').value }}</span>
          </div>

          <div
            @click="activeSection = 'suppliers'"
            :class="['flex items-center gap-3 px-4 py-2.5 rounded-lg cursor-pointer transition-colors text-sm', activeSection === 'suppliers' ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800']"
          >
            <i class="pi pi-truck"></i>
            <span>{{ t('suppliers').value }}</span>
          </div>
        </nav>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 overflow-hidden">
      <!-- Equipment Section -->
      <div v-if="activeSection === 'equipment'" class="card h-full flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('equipmentList').value }}</h3>
          <Button :label="t('newEquipment').value" icon="pi pi-plus" @click="openEquipmentDialog()" />
        </div>

        <div class="flex gap-3 mb-4">
          <Dropdown v-model="filterType" :options="typeOptions" optionLabel="name" optionValue="id" :placeholder="t('allTypes').value" showClear class="w-48" />
          <Dropdown v-model="filterStatus" :options="statusOptions" optionLabel="label" optionValue="value" :placeholder="t('allStatuses').value" showClear class="w-48" />
          <Dropdown v-model="filterLocation" :options="locationOptions" optionLabel="label" optionValue="id" :placeholder="t('allLocations').value" showClear class="w-48" />
        </div>

        <div class="flex-1 overflow-auto">
          <DataTable :value="filteredEquipment" stripedRows paginator :rows="10" v-model:expandedRows="expandedRows" dataKey="id" class="text-sm">
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
            <Column :header="t('actions').value" style="width: 100px">
              <template #body="slotProps">
                <div class="flex gap-1">
                  <Button icon="pi pi-pencil" text rounded size="small" @click="openEquipmentDialog(slotProps.data)" v-tooltip.top="t('edit').value" />
                  <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="confirmDeleteEquipment(slotProps.data)" v-tooltip.top="t('delete').value" />
                </div>
              </template>
            </Column>

            <template #expansion="slotProps">
              <div class="p-4 grid grid-cols-3 gap-6" style="background-color: var(--bg-app);">
                <div>
                  <h4 class="font-semibold mb-3 text-blue-500">{{ t('details').value }}</h4>
                  <p class="mb-2"><span class="opacity-60">{{ t('assetTag').value }}:</span> {{ slotProps.data.asset_tag || '-' }}</p>
                  <p class="mb-2"><span class="opacity-60">{{ t('purchaseDate').value }}:</span> {{ formatDate(slotProps.data.purchase_date) }}</p>
                  <p class="mb-2"><span class="opacity-60">{{ t('warrantyExpiry').value }}:</span> {{ formatDate(slotProps.data.warranty_expiry) }}</p>
                  <p><span class="opacity-60">{{ t('supplier').value }}:</span> {{ slotProps.data.supplier?.name || '-' }}</p>
                </div>
                <div>
                  <h4 class="font-semibold mb-3 text-blue-500">{{ t('linkedIps').value }}</h4>
                  <div v-if="slotProps.data.ip_addresses?.length">
                    <div v-for="ip in slotProps.data.ip_addresses" :key="ip.id" class="flex items-center justify-between p-2 rounded mb-1" style="background-color: var(--bg-card);">
                      <span class="font-mono text-sm">{{ ip.address }}</span>
                      <Button icon="pi pi-times" text rounded size="small" severity="danger" @click="unlinkIpFromExpansion(slotProps.data.id, ip.id)" />
                    </div>
                  </div>
                  <p v-else class="opacity-50 text-sm">{{ t('noIpLinked').value }}</p>
                  <Button :label="t('linkIp').value" icon="pi pi-link" size="small" class="mt-3" @click="openLinkIpDialog(slotProps.data)" />
                </div>
                <div>
                  <h4 class="font-semibold mb-3 text-blue-500">{{ t('notes').value }}</h4>
                  <p class="text-sm opacity-70 whitespace-pre-wrap">{{ slotProps.data.notes || '-' }}</p>
                </div>
              </div>
            </template>
          </DataTable>
        </div>
      </div>

      <!-- Manufacturers Section -->
      <div v-if="activeSection === 'manufacturers'" class="card">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('manufacturers').value }}</h3>
          <Button :label="t('newManufacturer').value" icon="pi pi-plus" @click="openManufacturerDialog()" />
        </div>
        <DataTable :value="manufacturers" stripedRows class="text-sm">
          <Column field="name" :header="t('name').value" sortable></Column>
          <Column field="website" :header="t('website').value">
            <template #body="slotProps">
              <a v-if="slotProps.data.website" :href="slotProps.data.website" target="_blank" class="text-blue-500 hover:underline">{{ slotProps.data.website }}</a>
              <span v-else class="opacity-50">-</span>
            </template>
          </Column>
          <Column field="notes" :header="t('notes').value">
            <template #body="slotProps">
              <span class="truncate block max-w-xs">{{ slotProps.data.notes || '-' }}</span>
            </template>
          </Column>
          <Column :header="t('actions').value" style="width: 100px">
            <template #body="slotProps">
              <div class="flex gap-1">
                <Button icon="pi pi-pencil" text rounded size="small" @click="openManufacturerDialog(slotProps.data)" />
                <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="deleteManufacturer(slotProps.data.id)" />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- Models Section -->
      <div v-if="activeSection === 'models'" class="card">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('equipmentModels').value }}</h3>
          <Button :label="t('newModel').value" icon="pi pi-plus" @click="openModelDialog()" />
        </div>
        <DataTable :value="models" stripedRows class="text-sm">
          <Column field="name" :header="t('name').value" sortable></Column>
          <Column :header="t('manufacturer').value">
            <template #body="slotProps">{{ slotProps.data.manufacturer?.name || '-' }}</template>
          </Column>
          <Column :header="t('equipmentType').value">
            <template #body="slotProps">
              <span v-if="slotProps.data.equipment_type">
                <i :class="'pi ' + slotProps.data.equipment_type.icon + ' mr-2'"></i>
                {{ slotProps.data.equipment_type.name }}
              </span>
              <span v-else class="opacity-50">-</span>
            </template>
          </Column>
          <Column :header="t('actions').value" style="width: 100px">
            <template #body="slotProps">
              <div class="flex gap-1">
                <Button icon="pi pi-pencil" text rounded size="small" @click="openModelDialog(slotProps.data)" />
                <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="deleteModel(slotProps.data.id)" />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- Types Section -->
      <div v-if="activeSection === 'types'" class="card">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('equipmentTypes').value }}</h3>
          <Button :label="t('newType').value" icon="pi pi-plus" @click="openTypeDialog()" />
        </div>
        <DataTable :value="types" stripedRows class="text-sm">
          <Column :header="t('icon').value" style="width: 80px">
            <template #body="slotProps">
              <i :class="'pi ' + slotProps.data.icon + ' text-xl'"></i>
            </template>
          </Column>
          <Column field="name" :header="t('name').value" sortable></Column>
          <Column :header="t('actions').value" style="width: 100px">
            <template #body="slotProps">
              <div class="flex gap-1">
                <Button icon="pi pi-pencil" text rounded size="small" @click="openTypeDialog(slotProps.data)" />
                <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="deleteType(slotProps.data.id)" />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- Locations Section -->
      <div v-if="activeSection === 'locations'" class="card">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('locations').value }}</h3>
          <Button :label="t('newLocation').value" icon="pi pi-plus" @click="openLocationDialog()" />
        </div>
        <DataTable :value="locations" stripedRows class="text-sm">
          <Column field="site" :header="t('site').value" sortable></Column>
          <Column field="building" :header="t('building').value">
            <template #body="slotProps">{{ slotProps.data.building || '-' }}</template>
          </Column>
          <Column field="room" :header="t('room').value">
            <template #body="slotProps">{{ slotProps.data.room || '-' }}</template>
          </Column>
          <Column :header="t('actions').value" style="width: 100px">
            <template #body="slotProps">
              <div class="flex gap-1">
                <Button icon="pi pi-pencil" text rounded size="small" @click="openLocationDialog(slotProps.data)" />
                <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="deleteLocation(slotProps.data.id)" />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- Suppliers Section -->
      <div v-if="activeSection === 'suppliers'" class="card">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('suppliers').value }}</h3>
          <Button :label="t('newSupplier').value" icon="pi pi-plus" @click="openSupplierDialog()" />
        </div>
        <DataTable :value="suppliers" stripedRows class="text-sm">
          <Column field="name" :header="t('name').value" sortable></Column>
          <Column field="contact_email" :header="t('contactEmail').value">
            <template #body="slotProps">
              <a v-if="slotProps.data.contact_email" :href="'mailto:' + slotProps.data.contact_email" class="text-blue-500 hover:underline">{{ slotProps.data.contact_email }}</a>
              <span v-else class="opacity-50">-</span>
            </template>
          </Column>
          <Column field="phone" :header="t('phone').value">
            <template #body="slotProps">{{ slotProps.data.phone || '-' }}</template>
          </Column>
          <Column field="website" :header="t('website').value">
            <template #body="slotProps">
              <a v-if="slotProps.data.website" :href="slotProps.data.website" target="_blank" class="text-blue-500 hover:underline">{{ slotProps.data.website }}</a>
              <span v-else class="opacity-50">-</span>
            </template>
          </Column>
          <Column :header="t('actions').value" style="width: 100px">
            <template #body="slotProps">
              <div class="flex gap-1">
                <Button icon="pi pi-pencil" text rounded size="small" @click="openSupplierDialog(slotProps.data)" />
                <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="deleteSupplier(slotProps.data.id)" />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <!-- Equipment Dialog -->
    <Dialog v-model:visible="showEquipmentDialog" modal :header="editingEquipment ? t('editEquipment').value : t('newEquipment').value" :style="{ width: '650px' }">
      <div class="grid grid-cols-2 gap-x-4 gap-y-4">
        <div class="col-span-2">
          <label class="block text-sm font-medium mb-1">{{ t('name').value }} <span class="text-red-500">*</span></label>
          <InputText v-model="equipmentForm.name" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('equipmentModel').value }}</label>
          <Dropdown v-model="equipmentForm.model_id" :options="models" optionLabel="name" optionValue="id" :placeholder="t('equipmentModel').value" class="w-full" showClear>
            <template #option="slotProps">
              {{ slotProps.option.manufacturer?.name }} - {{ slotProps.option.name }}
            </template>
          </Dropdown>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('status').value }}</label>
          <Dropdown v-model="equipmentForm.status" :options="statusOptions" optionLabel="label" optionValue="value" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('serialNumber').value }}</label>
          <InputText v-model="equipmentForm.serial_number" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('assetTag').value }}</label>
          <InputText v-model="equipmentForm.asset_tag" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('location').value }}</label>
          <Dropdown v-model="equipmentForm.location_id" :options="locationOptions" optionLabel="label" optionValue="id" :placeholder="t('location').value" class="w-full" showClear />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('supplier').value }}</label>
          <Dropdown v-model="equipmentForm.supplier_id" :options="suppliers" optionLabel="name" optionValue="id" :placeholder="t('supplier').value" class="w-full" showClear />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('purchaseDate').value }}</label>
          <Calendar v-model="equipmentForm.purchase_date" dateFormat="yy-mm-dd" class="w-full" showIcon />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('warrantyExpiry').value }}</label>
          <Calendar v-model="equipmentForm.warranty_expiry" dateFormat="yy-mm-dd" class="w-full" showIcon />
        </div>
        <div class="col-span-2">
          <label class="block text-sm font-medium mb-1">{{ t('notes').value }}</label>
          <Textarea v-model="equipmentForm.notes" rows="3" class="w-full" />
        </div>

        <!-- Remote Execution Section -->
        <div v-if="selectedModelSupportsRemoteExecution" class="col-span-2 border-t pt-4 mt-2" style="border-color: var(--border-color);">
          <h4 class="font-semibold mb-3 text-blue-500">{{ t('remoteExecution').value }}</h4>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('remoteIp').value }}</label>
              <InputText v-model="equipmentForm.remote_ip" class="w-full" placeholder="192.168.1.100" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('remotePort').value }}</label>
              <InputNumber v-model="equipmentForm.remote_port" class="w-full" :placeholder="22" :min="1" :max="65535" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('osType').value }}</label>
              <Dropdown v-model="equipmentForm.os_type" :options="osTypeOptions" class="w-full" :placeholder="t('osType').value" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('connectionType').value }}</label>
              <Dropdown v-model="equipmentForm.connection_type" :options="connectionTypeOptions" class="w-full" :placeholder="t('connectionType').value" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('username').value }}</label>
              <InputText v-model="equipmentForm.remote_username" class="w-full" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('password').value }}</label>
              <Password v-model="equipmentForm.remote_password" class="w-full" :feedback="false" toggleMask />
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('cancel').value" severity="secondary" outlined @click="showEquipmentDialog = false" />
          <Button :label="t('save').value" icon="pi pi-check" @click="saveEquipment" />
        </div>
      </template>
    </Dialog>

    <!-- Manufacturer Dialog -->
    <Dialog v-model:visible="showManufacturerDialog" modal :header="editingManufacturer ? t('edit').value + ' ' + t('manufacturer').value : t('newManufacturer').value" :style="{ width: '450px' }">
      <div class="flex flex-col gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('name').value }} <span class="text-red-500">*</span></label>
          <InputText v-model="manufacturerForm.name" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('website').value }}</label>
          <InputText v-model="manufacturerForm.website" class="w-full" placeholder="https://" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('notes').value }}</label>
          <Textarea v-model="manufacturerForm.notes" rows="2" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('cancel').value" severity="secondary" outlined @click="showManufacturerDialog = false" />
          <Button :label="t('save').value" icon="pi pi-check" @click="saveManufacturer" />
        </div>
      </template>
    </Dialog>

    <!-- Model Dialog -->
    <Dialog v-model:visible="showModelDialog" modal :header="editingModel ? t('edit').value + ' ' + t('equipmentModel').value : t('newModel').value" :style="{ width: '450px' }">
      <div class="flex flex-col gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('name').value }} <span class="text-red-500">*</span></label>
          <InputText v-model="modelForm.name" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('manufacturer').value }} <span class="text-red-500">*</span></label>
          <Dropdown v-model="modelForm.manufacturer_id" :options="manufacturers" optionLabel="name" optionValue="id" :placeholder="t('manufacturer').value" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('equipmentType').value }} <span class="text-red-500">*</span></label>
          <Dropdown v-model="modelForm.equipment_type_id" :options="types" optionLabel="name" optionValue="id" :placeholder="t('equipmentType').value" class="w-full">
            <template #option="slotProps">
              <i :class="'pi ' + slotProps.option.icon + ' mr-2'"></i>
              {{ slotProps.option.name }}
            </template>
          </Dropdown>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('cancel').value" severity="secondary" outlined @click="showModelDialog = false" />
          <Button :label="t('save').value" icon="pi pi-check" @click="saveModel" />
        </div>
      </template>
    </Dialog>

    <!-- Type Dialog -->
    <Dialog v-model:visible="showTypeDialog" modal :header="editingType ? t('edit').value + ' ' + t('equipmentType').value : t('newType').value" :style="{ width: '450px' }">
      <div class="flex flex-col gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('name').value }} <span class="text-red-500">*</span></label>
          <InputText v-model="typeForm.name" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('icon').value }}</label>
          <Dropdown v-model="typeForm.icon" :options="iconOptions" class="w-full">
            <template #value="slotProps">
              <span v-if="slotProps.value"><i :class="'pi ' + slotProps.value + ' mr-2'"></i> {{ slotProps.value }}</span>
              <span v-else>{{ t('icon').value }}</span>
            </template>
            <template #option="slotProps">
              <i :class="'pi ' + slotProps.option + ' mr-2'"></i> {{ slotProps.option }}
            </template>
          </Dropdown>
        </div>
        <div class="flex items-center gap-2 border-t pt-4" style="border-color: var(--border-color);">
          <Checkbox v-model="typeForm.supports_remote_execution" binary inputId="supports_remote" />
          <label for="supports_remote" class="text-sm cursor-pointer">{{ t('supportsRemoteExecution').value }}</label>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('cancel').value" severity="secondary" outlined @click="showTypeDialog = false" />
          <Button :label="t('save').value" icon="pi pi-check" @click="saveType" />
        </div>
      </template>
    </Dialog>

    <!-- Location Dialog -->
    <Dialog v-model:visible="showLocationDialog" modal :header="editingLocation ? t('edit').value + ' ' + t('location').value : t('newLocation').value" :style="{ width: '450px' }">
      <div class="flex flex-col gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('site').value }} <span class="text-red-500">*</span></label>
          <InputText v-model="locationForm.site" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('building').value }}</label>
          <InputText v-model="locationForm.building" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('room').value }}</label>
          <InputText v-model="locationForm.room" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('cancel').value" severity="secondary" outlined @click="showLocationDialog = false" />
          <Button :label="t('save').value" icon="pi pi-check" @click="saveLocation" />
        </div>
      </template>
    </Dialog>

    <!-- Supplier Dialog -->
    <Dialog v-model:visible="showSupplierDialog" modal :header="editingSupplier ? t('edit').value + ' ' + t('supplier').value : t('newSupplier').value" :style="{ width: '500px' }">
      <div class="flex flex-col gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('name').value }} <span class="text-red-500">*</span></label>
          <InputText v-model="supplierForm.name" class="w-full" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('contactEmail').value }}</label>
            <InputText v-model="supplierForm.contact_email" class="w-full" type="email" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('phone').value }}</label>
            <InputText v-model="supplierForm.phone" class="w-full" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('website').value }}</label>
          <InputText v-model="supplierForm.website" class="w-full" placeholder="https://" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('notes').value }}</label>
          <Textarea v-model="supplierForm.notes" rows="2" class="w-full" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('cancel').value" severity="secondary" outlined @click="showSupplierDialog = false" />
          <Button :label="t('save').value" icon="pi pi-check" @click="saveSupplier" />
        </div>
      </template>
    </Dialog>

    <!-- Link IP Dialog -->
    <Dialog v-model:visible="showLinkIpDialog" modal :header="t('linkIp').value" :style="{ width: '450px' }">
      <div v-if="linkingEquipment" class="flex flex-col gap-4">
        <div class="p-3 rounded-lg" style="background-color: var(--bg-app);">
          <span class="opacity-60">{{ t('equipment').value }}:</span>
          <strong class="ml-2">{{ linkingEquipment.name }}</strong>
        </div>

        <div v-if="linkingEquipment.ip_addresses?.length">
          <label class="block text-sm font-medium mb-2">{{ t('linkedIps').value }}</label>
          <div v-for="ip in linkingEquipment.ip_addresses" :key="ip.id" class="flex items-center justify-between p-3 rounded-lg mb-2" style="background-color: var(--bg-app);">
            <span class="font-mono">{{ ip.address }}</span>
            <Button icon="pi pi-times" text rounded size="small" severity="danger" @click="unlinkIp(ip.id)" />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium mb-2">{{ t('availableIps').value }}</label>
          <Dropdown v-model="selectedIpToLink" :options="availableIps" optionLabel="address" optionValue="id" :placeholder="t('selectIp').value" class="w-full" showClear>
            <template #option="slotProps">
              <span class="font-mono">{{ slotProps.option.address }}</span>
              <span v-if="slotProps.option.hostname" class="ml-2 opacity-60">({{ slotProps.option.hostname }})</span>
            </template>
          </Dropdown>
          <p v-if="!availableIps.length" class="text-sm opacity-50 mt-2">{{ t('noAvailableIps').value }}</p>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('cancel').value" severity="secondary" outlined @click="showLinkIpDialog = false" />
          <Button :label="t('linkIp').value" icon="pi pi-link" @click="linkIp" :disabled="!selectedIpToLink" />
        </div>
      </template>
    </Dialog>

    <!-- Delete Equipment Confirmation -->
    <Dialog v-model:visible="showDeleteEquipmentDialog" modal :header="t('confirmDelete').value" :style="{ width: '400px' }">
      <div class="flex items-start gap-4">
        <i class="pi pi-exclamation-triangle text-orange-500 text-3xl"></i>
        <div>
          <p class="mb-2">{{ t('confirmDeleteEquipment').value }}</p>
          <p class="font-bold">{{ deletingEquipment?.name }}</p>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('cancel').value" severity="secondary" outlined @click="showDeleteEquipmentDialog = false" />
          <Button :label="t('deleted').value" icon="pi pi-trash" severity="danger" @click="deleteEquipment" />
        </div>
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

// Active section
const activeSection = ref('equipment');

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

// Editing states
const editingEquipment = ref(null);
const editingManufacturer = ref(null);
const editingModel = ref(null);
const editingType = ref(null);
const editingLocation = ref(null);
const editingSupplier = ref(null);
const linkingEquipment = ref(null);
const deletingEquipment = ref(null);
const selectedIpToLink = ref(null);

// Forms
const equipmentForm = ref({
  name: '', serial_number: '', asset_tag: '', status: 'in_service',
  purchase_date: null, warranty_expiry: null, notes: '',
  model_id: null, location_id: null, supplier_id: null,
  // Remote execution fields
  remote_ip: '', os_type: null, connection_type: null,
  remote_username: '', remote_password: '', remote_port: null
});

const manufacturerForm = ref({ name: '', website: '', notes: '' });
const modelForm = ref({ name: '', manufacturer_id: null, equipment_type_id: null });
const typeForm = ref({ name: '', icon: 'pi-box', supports_remote_execution: false });
const locationForm = ref({ site: '', building: '', room: '' });
const supplierForm = ref({ name: '', contact_email: '', phone: '', website: '', notes: '' });

// Remote execution options
const osTypeOptions = ['linux', 'windows'];
const connectionTypeOptions = ['ssh', 'winrm'];

// Options
const statusOptions = computed(() => [
  { label: t('inService').value, value: 'in_service' },
  { label: t('inStock').value, value: 'in_stock' },
  { label: t('retired').value, value: 'retired' },
  { label: t('maintenance').value, value: 'maintenance' }
]);

const typeOptions = computed(() => types.value.map(tp => ({ id: tp.id, name: tp.name })));

const locationOptions = computed(() => locations.value.map(l => ({
  id: l.id,
  label: `${l.site}${l.building ? ' / ' + l.building : ''}${l.room ? ' / ' + l.room : ''}`
})));

const iconOptions = ['pi-server', 'pi-desktop', 'pi-mobile', 'pi-box', 'pi-database', 'pi-wifi', 'pi-globe', 'pi-print', 'pi-shield', 'pi-bolt', 'pi-cog', 'pi-sitemap', 'pi-sliders-h', 'pi-tablet', 'pi-video'];

// Filtered equipment
const filteredEquipment = computed(() => {
  let result = equipment.value;
  if (filterType.value) {
    result = result.filter(eq => eq.model?.equipment_type_id === filterType.value);
  }
  if (filterStatus.value) {
    result = result.filter(eq => eq.status === filterStatus.value);
  }
  if (filterLocation.value) {
    result = result.filter(eq => eq.location_id === filterLocation.value);
  }
  return result;
});

// Check if selected model supports remote execution
const selectedModelSupportsRemoteExecution = computed(() => {
  if (!equipmentForm.value.model_id) return false;
  const model = models.value.find(m => m.id === equipmentForm.value.model_id);
  return model?.equipment_type?.supports_remote_execution || false;
});

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
      supplier_id: eq.supplier_id,
      // Remote execution fields
      remote_ip: eq.remote_ip || '',
      os_type: eq.os_type || null,
      connection_type: eq.connection_type || null,
      remote_username: eq.remote_username || '',
      remote_password: '',  // Never pre-fill password for security
      remote_port: eq.remote_port || null
    };
  } else {
    equipmentForm.value = {
      name: '', serial_number: '', asset_tag: '', status: 'in_service',
      purchase_date: null, warranty_expiry: null, notes: '',
      model_id: null, location_id: null, supplier_id: null,
      remote_ip: '', os_type: null, connection_type: null,
      remote_username: '', remote_password: '', remote_port: null
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
    // Format dates as ISO datetime for the API
    if (data.purchase_date) {
      const d = data.purchase_date instanceof Date ? data.purchase_date : new Date(data.purchase_date);
      data.purchase_date = d.toISOString();
    }
    if (data.warranty_expiry) {
      const d = data.warranty_expiry instanceof Date ? data.warranty_expiry : new Date(data.warranty_expiry);
      data.warranty_expiry = d.toISOString();
    }

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
    const res = await api.get(`/inventory/equipment/${linkingEquipment.value.id}`);
    linkingEquipment.value = res.data;
    await loadAvailableIps();
    loadData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
  }
};

const unlinkIpFromExpansion = async (equipmentId, ipId) => {
  try {
    await api.delete(`/inventory/equipment/${equipmentId}/unlink-ip/${ipId}`);
    toast.add({ severity: 'success', summary: t('success').value, detail: t('ipUnlinked').value });
    loadData();
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
  if (!confirm(t('confirmDeleteItem').value)) return;
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
  if (!confirm(t('confirmDeleteItem').value)) return;
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
  typeForm.value = tp ? { ...tp } : { name: '', icon: 'pi-box', supports_remote_execution: false };
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
  if (!confirm(t('confirmDeleteItem').value)) return;
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
  if (!confirm(t('confirmDeleteItem').value)) return;
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
  if (!confirm(t('confirmDeleteItem').value)) return;
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
