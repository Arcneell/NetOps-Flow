<template>
  <div class="flex flex-col gap-8">
      
      <!-- My Profile Section -->
      <div class="card border-l-4 border-blue-500">
          <h3 class="text-lg font-bold mb-4">My Profile</h3>
          <div class="flex items-end gap-4">
              <div class="flex-grow max-w-md">
                  <label class="block text-sm font-medium mb-1 opacity-70">New Password</label>
                  <InputText v-model="newPassword" type="password" class="w-full" placeholder="Enter new password" />
              </div>
              <Button label="Update Password" icon="pi pi-check" @click="updateMyPassword" :loading="updatingPwd" />
          </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- User Management -->
        <div class="card" v-if="currentUser.role === 'admin'">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-bold">User Management</h3>
                <Button label="New User" icon="pi pi-plus" size="small" @click="openUserDialog" />
            </div>
            <DataTable :value="users" size="small" stripedRows>
                <Column field="username" header="Username"></Column>
                <Column field="role" header="Role">
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.role" :severity="slotProps.data.role === 'admin' ? 'danger' : 'info'" />
                    </template>
                </Column>
            </DataTable>
        </div>

        <!-- Server Inventory -->
        <div class="card">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-bold">Server Inventory</h3>
                <Button label="New Server" icon="pi pi-plus" size="small" @click="showServerDialog = true" />
            </div>
            <DataTable :value="servers" size="small" stripedRows>
                <Column field="name" header="Name"></Column>
                <Column field="ip_address" header="IP"></Column>
                <Column field="os_type" header="OS">
                    <template #body="slotProps">
                        <i :class="getOsIcon(slotProps.data.os_type)" class="mr-2"></i> {{ slotProps.data.os_type }}
                    </template>
                </Column>
                <Column header="Actions">
                    <template #body="slotProps">
                        <Button icon="pi pi-trash" text rounded severity="danger" @click="deleteServer(slotProps.data.id)" />
                    </template>
                </Column>
            </DataTable>
        </div>
      </div>

      <!-- Create User Dialog -->
      <Dialog v-model:visible="showUserDialog" modal header="Create User" :style="{ width: '500px' }">
          <div class="flex flex-col gap-4 mt-2">
              <div class="grid grid-cols-2 gap-4">
                  <div><label class="text-sm font-medium">Username</label><InputText v-model="newUser.username" class="w-full" /></div>
                  <div><label class="text-sm font-medium">Password</label><InputText v-model="newUser.password" type="password" class="w-full" /></div>
              </div>
              
              <div>
                  <label class="text-sm font-medium">Role</label>
                  <Dropdown v-model="newUser.role" :options="['user', 'admin']" class="w-full" />
              </div>

              <div v-if="newUser.role === 'user'" class="border-t pt-4 mt-2" style="border-color: var(--border-color);">
                  <label class="text-sm font-bold block mb-2">Permissions</label>
                  <div class="grid grid-cols-2 gap-3">
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_ipam" v-model="newUser.permissions.ipam">
                          <label for="perm_ipam" class="text-sm">Access IPAM</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_topo" v-model="newUser.permissions.topology">
                          <label for="perm_topo" class="text-sm">View Topology</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_scripts" v-model="newUser.permissions.scripts">
                          <label for="perm_scripts" class="text-sm">Run Scripts</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_settings" v-model="newUser.permissions.settings">
                          <label for="perm_settings" class="text-sm">Access Settings</label>
                      </div>
                  </div>
              </div>
          </div>
          <template #footer>
              <Button label="Save User" @click="createUser" />
          </template>
      </Dialog>

      <!-- Create Server Dialog -->
      <Dialog v-model:visible="showServerDialog" modal header="Add Server" :style="{ width: '500px' }">
          <div class="grid grid-cols-2 gap-4 mt-2">
              <div class="col-span-2"><label class="text-sm font-medium">Name</label><InputText v-model="newServer.name" class="w-full" /></div>
              <div><label class="text-sm font-medium">IP Address</label><InputText v-model="newServer.ip_address" class="w-full" /></div>
              <div><label class="text-sm font-medium">Port</label><InputText v-model="newServer.port" type="number" class="w-full" /></div>
              
              <div>
                  <label class="text-sm font-medium">OS Type</label>
                  <Dropdown v-model="newServer.os_type" :options="['linux', 'windows']" class="w-full" />
              </div>
              <div>
                  <label class="text-sm font-medium">Connection</label>
                  <Dropdown v-model="newServer.connection_type" :options="['ssh', 'winrm']" class="w-full" />
              </div>
              
              <div><label class="text-sm font-medium">Username</label><InputText v-model="newServer.username" class="w-full" /></div>
              <div><label class="text-sm font-medium">Password</label><InputText v-model="newServer.password" type="password" class="w-full" /></div>
          </div>
          <template #footer>
              <Button label="Save Server" @click="createServer" />
          </template>
      </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '../api';

const toast = useToast();
const users = ref([]);
const servers = ref([]);
const currentUser = ref({ role: 'user' });
const showUserDialog = ref(false);
const showServerDialog = ref(false);
const updatingPwd = ref(false);
const newPassword = ref('');

const newUser = ref({ 
    username: '', 
    password: '', 
    role: 'user', 
    permissions: { ipam: false, topology: false, scripts: false, settings: false } 
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
        toast.add({ severity: 'warn', summary: 'Password Too Short', detail: 'Password must be at least 8 characters.' });
        return;
    }
    updatingPwd.value = true;
    try {
        await api.put('/users/me/password', { password: newPassword.value });
        toast.add({ severity: 'success', summary: 'Password Updated', detail: 'Your password has been changed.' });
        newPassword.value = '';
    } catch (e) {
        const detail = e.response?.data?.detail || 'Could not update password.';
        toast.add({ severity: 'error', summary: 'Update Failed', detail: detail });
    } finally {
        updatingPwd.value = false;
    }
};

const openUserDialog = () => {
    newUser.value = { 
        username: '', 
        password: '', 
        role: 'user', 
        permissions: { ipam: true, topology: true, scripts: false, settings: false } 
    };
    showUserDialog.value = true;
};

const createUser = async () => {
    try {
        await api.post('/users/', newUser.value);
        showUserDialog.value = false;
        loadData();
        toast.add({ severity: 'success', summary: 'User Created' });
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Failed', detail: e.response?.data?.detail || 'Error' });
    }
};

const createServer = async () => {
    // Validation client-side
    if (!newServer.value.name || !newServer.value.ip_address || !newServer.value.username) {
        toast.add({ severity: 'warn', summary: 'Validation Error', detail: 'Please fill all required fields.' });
        return;
    }
    try {
        await api.post('/servers/', newServer.value);
        showServerDialog.value = false;
        loadData();
        toast.add({ severity: 'success', summary: 'Server Added' });
    } catch (e) {
        const detail = e.response?.data?.detail || 'Failed to add server.';
        toast.add({ severity: 'error', summary: 'Failed', detail: detail });
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