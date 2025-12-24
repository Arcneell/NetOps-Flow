<template>
  <div class="flex flex-col gap-8">

      <!-- My Profile Section -->
      <div class="card border-l-4 border-blue-500">
          <h3 class="text-lg font-bold mb-4">{{ t('settings.myProfile') }}</h3>
          <div class="flex items-end gap-4">
              <div class="flex-grow max-w-md">
                  <label class="block text-sm font-medium mb-1 opacity-70">{{ t('settings.newPassword') }}</label>
                  <InputText v-model="newPassword" type="password" class="w-full" :placeholder="t('settings.newPassword')" />
              </div>
              <Button :label="t('settings.updatePassword')" icon="pi pi-check" @click="updateMyPassword" :loading="updatingPwd" />
          </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- User Management -->
        <div class="card" v-if="currentUser.role === 'admin'">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-bold">{{ t('settings.userManagement') }}</h3>
                <Button :label="t('settings.newUser')" icon="pi pi-plus" size="small" @click="openUserDialog" />
            </div>
            <DataTable :value="users" size="small" stripedRows>
                <Column field="username" :header="t('auth.username')"></Column>
                <Column field="role" :header="t('settings.role')">
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.role" :severity="slotProps.data.role === 'admin' ? 'danger' : 'info'" />
                    </template>
                </Column>
                <Column :header="t('common.actions')" style="width: 100px">
                    <template #body="slotProps">
                        <Button
                            v-if="slotProps.data.id !== currentUser.id"
                            icon="pi pi-trash"
                            text
                            rounded
                            severity="danger"
                            @click="confirmDeleteUser(slotProps.data)"
                            v-tooltip.top="t('users.deleteUser')"
                        />
                    </template>
                </Column>
            </DataTable>
        </div>

      </div>

      <!-- Create User Dialog -->
      <Dialog v-model:visible="showUserDialog" modal :header="t('settings.newUser')" :style="{ width: '500px' }">
          <div class="flex flex-col gap-4 mt-2">
              <div class="grid grid-cols-2 gap-4">
                  <div><label class="text-sm font-medium">{{ t('auth.username') }}</label><InputText v-model="newUser.username" class="w-full" /></div>
                  <div><label class="text-sm font-medium">{{ t('auth.password') }}</label><InputText v-model="newUser.password" type="password" class="w-full" /></div>
              </div>

              <div>
                  <label class="text-sm font-medium">{{ t('settings.role') }}</label>
                  <Dropdown v-model="newUser.role" :options="['user', 'admin']" class="w-full" />
              </div>

              <div v-if="newUser.role === 'user'" class="border-t pt-4 mt-2" style="border-color: var(--border-color);">
                  <label class="text-sm font-bold block mb-2">{{ t('settings.permissions') }}</label>
                  <div class="grid grid-cols-2 gap-3">
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_ipam" v-model="newUser.permissions.ipam">
                          <label for="perm_ipam" class="text-sm">{{ t('settings.accessIpam') }}</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_topo" v-model="newUser.permissions.topology">
                          <label for="perm_topo" class="text-sm">{{ t('settings.viewTopo') }}</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_scripts" v-model="newUser.permissions.scripts">
                          <label for="perm_scripts" class="text-sm">{{ t('settings.runScripts') }}</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_settings" v-model="newUser.permissions.settings">
                          <label for="perm_settings" class="text-sm">{{ t('settings.accessSettings') }}</label>
                      </div>
                      <div class="flex items-center gap-2">
                          <input type="checkbox" id="perm_inventory" v-model="newUser.permissions.inventory">
                          <label for="perm_inventory" class="text-sm">{{ t('settings.accessInventory') }}</label>
                      </div>
                  </div>
              </div>
          </div>
          <template #footer>
              <div class="flex justify-end gap-3">
                  <Button :label="t('common.cancel')" severity="secondary" outlined @click="showUserDialog = false" />
                  <Button :label="t('settings.saveUser')" icon="pi pi-check" @click="createUser" />
              </div>
          </template>
      </Dialog>

      <!-- Delete User Confirmation Dialog -->
      <Dialog v-model:visible="showDeleteUserDialog" modal :header="t('users.deleteUser')" :style="{ width: '400px' }">
          <div class="flex items-center gap-3">
              <i class="pi pi-exclamation-triangle text-red-500 text-2xl"></i>
              <span>{{ t('users.confirmDeleteUser') }} <b>{{ userToDelete?.username }}</b>?</span>
          </div>
          <template #footer>
              <div class="flex justify-end gap-3">
                  <Button :label="t('common.cancel')" severity="secondary" outlined @click="showDeleteUserDialog = false" />
                  <Button :label="t('common.delete')" icon="pi pi-trash" @click="deleteUser" severity="danger" />
              </div>
          </template>
      </Dialog>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useI18n } from 'vue-i18n';
import api from '../api';

const { t } = useI18n();
const toast = useToast();
const users = ref([]);
const currentUser = ref({ role: 'user' });
const showUserDialog = ref(false);
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

const loadData = async () => {
    try {
        const meRes = await api.get('/me');
        currentUser.value = meRes.data;

        if (currentUser.value.role === 'admin') {
             const uRes = await api.get('/users/');
             users.value = uRes.data;
        }
    } catch (e) {
        console.error(e);
    }
};

const updateMyPassword = async () => {
    if(!newPassword.value) return;
    if(newPassword.value.length < 8) {
        toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.passwordTooShort') });
        return;
    }
    updatingPwd.value = true;
    try {
        await api.put('/me/password', { password: newPassword.value });
        toast.add({ severity: 'success', summary: t('common.success'), detail: t('users.passwordUpdated') });
        newPassword.value = '';
    } catch (e) {
        const detail = e.response?.data?.detail || t('validation.updateFailed');
        toast.add({ severity: 'error', summary: t('validation.updateFailed'), detail: detail });
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
        toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.usernameTooShort') });
        return;
    }
    if (!newUser.value.password || newUser.value.password.length < 8) {
        toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.passwordTooShort') });
        return;
    }
    try {
        await api.post('/users/', newUser.value);
        showUserDialog.value = false;
        loadData();
        toast.add({ severity: 'success', summary: t('common.success'), detail: t('users.userCreated') });
    } catch (e) {
        toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
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
        toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('users.userDeleted') });
    } catch (e) {
        const detail = e.response?.data?.detail || t('common.error');
        toast.add({ severity: 'error', summary: t('common.error'), detail: detail });
    }
};

onMounted(loadData);
</script>
