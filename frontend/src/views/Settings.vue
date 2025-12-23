<template>
  <div class="flex flex-col gap-8">

      <!-- My Profile Section -->
      <div class="card border-l-4 border-blue-500">
          <h3 class="text-lg font-bold mb-4">{{ t('myProfile').value }}</h3>
          <div class="flex items-end gap-4">
              <div class="flex-grow max-w-md">
                  <label class="block text-sm font-medium mb-1 opacity-70">{{ t('newPassword').value }}</label>
                  <InputText v-model="newPassword" type="password" class="w-full" :placeholder="t('newPassword').value" />
              </div>
              <Button :label="t('updatePassword').value" icon="pi pi-check" @click="updateMyPassword" :loading="updatingPwd" />
          </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- User Management -->
        <div class="card" v-if="currentUser.role === 'admin'">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-bold">{{ t('userManagement').value }}</h3>
                <Button :label="t('newUser').value" icon="pi pi-plus" size="small" @click="openUserDialog" />
            </div>
            <DataTable :value="users" size="small" stripedRows>
                <Column field="username" :header="t('username').value"></Column>
                <Column field="role" :header="t('role').value">
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.role" :severity="slotProps.data.role === 'admin' ? 'danger' : 'info'" />
                    </template>
                </Column>
                <Column :header="t('actions').value" style="width: 100px">
                    <template #body="slotProps">
                        <Button
                            v-if="slotProps.data.id !== currentUser.id"
                            icon="pi pi-trash"
                            text
                            rounded
                            severity="danger"
                            @click="confirmDeleteUser(slotProps.data)"
                            v-tooltip.top="t('deleteUser').value"
                        />
                    </template>
                </Column>
            </DataTable>
        </div>

        <!-- Server Inventory -->
        <div class="card">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-bold">{{ t('serverInventory').value }}</h3>
                <Button :label="t('newServer').value" icon="pi pi-plus" size="small" @click="showServerDialog = true" />
            </div>
            <DataTable :value="servers" size="small" stripedRows>
                <Column field="name" :header="t('name').value"></Column>
                <Column field="ip_address" header="IP"></Column>
                <Column field="os_type" header="OS">
                    <template #body="slotProps">
                        <i :class="getOsIcon(slotProps.data.os_type)" class="mr-2"></i> {{ slotProps.data.os_type }}
                    </template>
                </Column>
                <Column :header="t('actions').value">
                    <template #body="slotProps">
                        <Button icon="pi pi-trash" text rounded severity="danger" @click="deleteServer(slotProps.data.id)" />
                    </template>
                </Column>
            </DataTable>
        </div>
      </div>

      <!-- Create User Dialog -->
      <Dialog v-model:visible="showUserDialog" modal :header="t('newUser').value" :style="{ width: '500px' }">
          <div class="flex flex-col gap-4 mt-2">
              <div class="grid grid-cols-2 gap-4">
                  <div><label class="text-sm font-medium">{{ t('username').value }}</label><InputText v-model="newUser.username" class="w-full" /></div>
                  <div><label class="text-sm font-medium">{{ t('password').value }}</label><InputText v-model="newUser.password" type="password" class="w-full" /></div>
              </div>

              <div>
                  <label class="text-sm font-medium">{{ t('role').value }}</label>
                  <Dropdown v-model="newUser.role" :options="['user', 'admin']" class="w-full" />
              </div>

              <div v-if="newUser.role === 'user'" class="border-t pt-4 mt-2" style="border-color: var(--border-color);">
                  <label class="text-sm font-bold block mb-2">{{ t('permissions').value }}</label>
                  <div class="grid grid-cols-2 gap-3">
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_ipam" v-model="newUser.permissions.ipam">
                          <label for="perm_ipam" class="text-sm">{{ t('accessIpam').value }}</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_topo" v-model="newUser.permissions.topology">
                          <label for="perm_topo" class="text-sm">{{ t('viewTopo').value }}</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_scripts" v-model="newUser.permissions.scripts">
                          <label for="perm_scripts" class="text-sm">{{ t('runScripts').value }}</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_settings" v-model="newUser.permissions.settings">
                          <label for="perm_settings" class="text-sm">{{ t('accessSettings').value }}</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_inventory" v-model="newUser.permissions.inventory">
                          <label for="perm_inventory" class="text-sm">{{ t('accessInventory').value }}</label>
                      </div>
                  </div>
              </div>
          </div>
          <template #footer>
              <div class="flex justify-end gap-3">
                  <Button :label="t('cancel').value" severity="secondary" outlined @click="showUserDialog = false" />
                  <Button :label="t('saveUser').value" icon="pi pi-check" @click="createUser" />
              </div>
          </template>
      </Dialog>

      <!-- Delete User Confirmation Dialog -->
      <Dialog v-model:visible="showDeleteUserDialog" modal :header="t('deleteUser').value" :style="{ width: '400px' }">
          <div class="flex items-center gap-3">
              <i class="pi pi-exclamation-triangle text-red-500 text-2xl"></i>
              <span>{{ t('confirmDeleteUser').value }} <b>{{ userToDelete?.username }}</b>?</span>
          </div>
          <template #footer>
              <div class="flex justify-end gap-3">
                  <Button :label="t('cancel').value" severity="secondary" outlined @click="showDeleteUserDialog = false" />
                  <Button :label="t('delete').value" icon="pi pi-trash" @click="deleteUser" severity="danger" />
              </div>
          </template>
      </Dialog>

      <!-- Create Server Dialog -->
      <Dialog v-model:visible="showServerDialog" modal :header="t('newServer').value" :style="{ width: '500px' }">
          <div class="grid grid-cols-2 gap-4 mt-2">
              <div class="col-span-2"><label class="text-sm font-medium">{{ t('name').value }}</label><InputText v-model="newServer.name" class="w-full" /></div>
              <div><label class="text-sm font-medium">{{ t('ipAddress').value }}</label><InputText v-model="newServer.ip_address" class="w-full" /></div>
              <div><label class="text-sm font-medium">Port</label><InputText v-model="newServer.port" type="number" class="w-full" /></div>

              <div>
                  <label class="text-sm font-medium">OS Type</label>
                  <Dropdown v-model="newServer.os_type" :options="['linux', 'windows']" class="w-full" />
              </div>
              <div>
                  <label class="text-sm font-medium">Connection</label>
                  <Dropdown v-model="newServer.connection_type" :options="['ssh', 'winrm']" class="w-full" />
              </div>

              <div><label class="text-sm font-medium">{{ t('username').value }}</label><InputText v-model="newServer.username" class="w-full" /></div>
              <div><label class="text-sm font-medium">{{ t('password').value }}</label><InputText v-model="newServer.password" type="password" class="w-full" /></div>
          </div>
          <template #footer>
              <div class="flex justify-end gap-3">
                  <Button :label="t('cancel').value" severity="secondary" outlined @click="showServerDialog = false" />
                  <Button :label="t('saveServer').value" icon="pi pi-check" @click="createServer" />
              </div>
          </template>
      </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '../api';
import { t } from '../i18n';

const toast = useToast();
const users = ref([]);
const servers = ref([]);
const currentUser = ref({ role: 'user' });
const showUserDialog = ref(false);
const showServerDialog = ref(false);
const showDeleteUserDialog = ref(false);
const userToDelete = ref(null);
const updatingPwd = ref(false);
const newPassword = ref('');

const newUser = ref({
    username: '',
    password: '',
    role: 'user',
    permissions: { ipam: false, topology: false, scripts: false, settings: false, inventory: false }
});

const newServer = ref({ name: '', ip_address: '', port: 22, os_type: 'linux', connection_type: 'ssh', username: '', password: '' });

const loadData = async () => {
    try {
        const meRes = await api.get('/users/me');
        currentUser.value = meRes.data;

        if (currentUser.value.role === 'admin') {
             const uRes = await api.get('/users/');
             users.value = uRes.data;
        }

        const sRes = await api.get('/servers/');
        servers.value = sRes.data;
    } catch (e) {
        console.error(e);
    }
};

const updateMyPassword = async () => {
    if(!newPassword.value) return;
    if(newPassword.value.length < 8) {
        toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('passwordTooShort').value });
        return;
    }
    updatingPwd.value = true;
    try {
        await api.put('/users/me/password', { password: newPassword.value });
        toast.add({ severity: 'success', summary: t('success').value, detail: t('passwordUpdated').value });
        newPassword.value = '';
    } catch (e) {
        const detail = e.response?.data?.detail || t('updateFailed').value;
        toast.add({ severity: 'error', summary: t('updateFailed').value, detail: detail });
    } finally {
        updatingPwd.value = false;
    }
};

const openUserDialog = () => {
    newUser.value = {
        username: '',
        password: '',
        role: 'user',
        permissions: { ipam: true, topology: true, scripts: false, settings: false, inventory: false }
    };
    showUserDialog.value = true;
};

const createUser = async () => {
    // Client-side validation
    if (!newUser.value.username || newUser.value.username.length < 3) {
        toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('usernameTooShort').value });
        return;
    }
    if (!newUser.value.password || newUser.value.password.length < 8) {
        toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('passwordTooShort').value });
        return;
    }
    try {
        await api.post('/users/', newUser.value);
        showUserDialog.value = false;
        loadData();
        toast.add({ severity: 'success', summary: t('success').value, detail: t('userCreated').value });
    } catch (e) {
        toast.add({ severity: 'error', summary: t('error').value, detail: e.response?.data?.detail || t('error').value });
    }
};

const confirmDeleteUser = (user) => {
    userToDelete.value = user;
    showDeleteUserDialog.value = true;
};

const deleteUser = async () => {
    if (!userToDelete.value) return;
    try {
        await api.delete(`/users/${userToDelete.value.id}`);
        showDeleteUserDialog.value = false;
        loadData();
        toast.add({ severity: 'success', summary: t('deleted').value, detail: t('userDeleted').value });
    } catch (e) {
        const detail = e.response?.data?.detail || t('error').value;
        toast.add({ severity: 'error', summary: t('error').value, detail: detail });
    }
};

const createServer = async () => {
    // Validation client-side
    if (!newServer.value.name || !newServer.value.ip_address || !newServer.value.username) {
        toast.add({ severity: 'warn', summary: t('validationError').value, detail: t('fillRequiredFields').value });
        return;
    }
    try {
        await api.post('/servers/', newServer.value);
        showServerDialog.value = false;
        loadData();
        toast.add({ severity: 'success', summary: t('success').value, detail: 'Server Added' });
    } catch (e) {
        const detail = e.response?.data?.detail || t('error').value;
        toast.add({ severity: 'error', summary: t('error').value, detail: detail });
    }
};

const deleteServer = async (id) => {
    if(confirm('Are you sure?')) {
        await api.delete(`/servers/${id}`);
        loadData();
    }
};

const getOsIcon = (os) => {
    return os === 'windows' ? 'pi pi-microsoft' : 'pi pi-linux';
};

onMounted(loadData);
</script>
