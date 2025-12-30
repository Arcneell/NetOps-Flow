<template>
  <div class="flex flex-col gap-6">

    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h1 class="text-2xl font-bold">{{ t('users.title') }}</h1>
        <p class="text-sm opacity-70">{{ t('users.subtitle') }}</p>
      </div>
      <Button :label="t('users.newUser')" icon="pi pi-plus" @click="openUserDialog()" />
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="card p-4 flex items-center gap-4">
        <div class="w-12 h-12 rounded-full bg-sky-500/20 flex items-center justify-center">
          <i class="pi pi-users text-sky-500 text-xl"></i>
        </div>
        <div>
          <div class="text-2xl font-bold">{{ users.length }}</div>
          <div class="text-sm opacity-70">{{ t('users.totalUsers') }}</div>
        </div>
      </div>

      <div class="card p-4 flex items-center gap-4">
        <div class="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center">
          <i class="pi pi-shield text-red-500 text-xl"></i>
        </div>
        <div>
          <div class="text-2xl font-bold">{{ adminCount }}</div>
          <div class="text-sm opacity-70">{{ t('users.admins') }}</div>
        </div>
      </div>

      <div class="card p-4 flex items-center gap-4">
        <div class="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
          <i class="pi pi-user text-blue-500 text-xl"></i>
        </div>
        <div>
          <div class="text-2xl font-bold">{{ userCount }}</div>
          <div class="text-sm opacity-70">{{ t('users.regularUsers') }}</div>
        </div>
      </div>

      <div class="card p-4 flex items-center gap-4">
        <div class="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center">
          <i class="pi pi-check-circle text-green-500 text-xl"></i>
        </div>
        <div>
          <div class="text-2xl font-bold">{{ mfaEnabledCount }}</div>
          <div class="text-sm opacity-70">{{ t('users.mfaEnabled') }}</div>
        </div>
      </div>
    </div>

    <!-- Users Table -->
    <div class="card p-4">
      <DataTable :value="users" stripedRows paginator :rows="10" dataKey="id" :loading="loading"
                 class="text-sm" :globalFilterFields="['username', 'email', 'role']"
                 v-model:filters="tableFilters" filterDisplay="row">
        <template #header>
          <div class="flex justify-between items-center">
            <span class="text-lg font-bold">{{ t('users.usersList') }}</span>
            <span class="p-input-icon-left">
              <i class="pi pi-search" />
              <InputText v-model="tableFilters['global'].value" :placeholder="t('users.searchUsers')" />
            </span>
          </div>
        </template>

        <Column style="width: 60px">
          <template #body="slotProps">
            <div class="w-10 h-10 rounded-full overflow-hidden bg-slate-700 flex items-center justify-center">
              <img v-if="slotProps.data.avatar" :src="`/api/v1/avatars/${slotProps.data.avatar}`"
                   class="w-full h-full object-cover" alt="">
              <div v-else class="w-full h-full flex items-center justify-center bg-gradient-to-br from-sky-500 to-blue-600">
                <span class="text-sm font-bold text-white">{{ getUserInitials(slotProps.data.username) }}</span>
              </div>
            </div>
          </template>
        </Column>

        <Column field="username" :header="t('auth.username')" sortable>
          <template #body="slotProps">
            <div class="flex flex-col">
              <span class="font-medium">{{ slotProps.data.username }}</span>
              <span v-if="slotProps.data.email" class="text-xs opacity-50">{{ slotProps.data.email }}</span>
            </div>
          </template>
        </Column>

        <Column field="role" :header="t('settings.role')" sortable style="width: 120px">
          <template #body="slotProps">
            <Tag :value="slotProps.data.role === 'admin' ? t('settings.roleAdmin') : t('settings.roleUser')"
                 :severity="slotProps.data.role === 'admin' ? 'danger' : 'info'" />
          </template>
        </Column>

        <Column field="is_active" :header="t('users.status')" sortable style="width: 100px">
          <template #body="slotProps">
            <Tag :value="slotProps.data.is_active ? t('status.active') : t('users.inactive')"
                 :severity="slotProps.data.is_active ? 'success' : 'secondary'" />
          </template>
        </Column>

        <Column field="mfa_enabled" :header="t('users.2fa')" style="width: 80px">
          <template #body="slotProps">
            <i v-if="slotProps.data.mfa_enabled" class="pi pi-shield text-green-500" v-tooltip.top="t('settings.mfaEnabled')"></i>
            <i v-else class="pi pi-shield text-slate-500 opacity-30" v-tooltip.top="t('settings.mfaDisabled')"></i>
          </template>
        </Column>

        <Column field="created_at" :header="t('users.createdAt')" sortable style="width: 140px">
          <template #body="slotProps">
            {{ formatDate(slotProps.data.created_at) }}
          </template>
        </Column>

        <Column :header="t('common.actions')" style="width: 120px">
          <template #body="slotProps">
            <div class="flex gap-2">
              <Button icon="pi pi-pencil" text rounded severity="info" size="small"
                      @click="openUserDialog(slotProps.data)" v-tooltip.top="t('common.edit')" />
              <Button v-if="slotProps.data.id !== currentUserId"
                      icon="pi pi-trash" text rounded severity="danger" size="small"
                      @click="confirmDeleteUser(slotProps.data)" v-tooltip.top="t('common.delete')" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create/Edit User Dialog -->
    <Dialog v-model:visible="showUserDialog" modal :header="editingUser ? t('users.editUser') : t('users.newUser')"
            :style="{ width: '500px' }" @keydown.enter="onUserDialogEnter">
      <div class="flex flex-col gap-4 mt-2">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('auth.username') }} <span class="text-red-500">*</span></label>
          <InputText v-model="userForm.username" class="w-full" :disabled="editingUser" />
          <small v-if="!editingUser" class="text-xs opacity-50">{{ t('users.usernameHelp') }}</small>
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">{{ t('settings.email') }}</label>
          <InputText v-model="userForm.email" type="email" class="w-full" :placeholder="t('settings.emailPlaceholder')" />
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">
            {{ t('auth.password') }}
            <span v-if="!editingUser" class="text-red-500">*</span>
            <span v-else class="text-xs opacity-50 ml-1">({{ t('users.leaveBlankToKeep') }})</span>
          </label>
          <Password v-model="userForm.password" toggleMask class="w-full" inputClass="w-full" :feedback="false" />
          <small class="text-xs opacity-50">{{ t('validation.passwordMinLength', { min: 8 }) }}</small>
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">{{ t('settings.role') }} <span class="text-red-500">*</span></label>
          <Dropdown v-model="userForm.role" :options="roleOptions" optionLabel="label" optionValue="value" class="w-full" />
        </div>

        <div class="flex items-center gap-2">
          <Checkbox v-model="userForm.is_active" :binary="true" inputId="isActive" />
          <label for="isActive" class="cursor-pointer">{{ t('users.isActive') }}</label>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showUserDialog = false" />
          <Button :label="t('common.save')" icon="pi pi-check" @click="saveUser" :loading="saving" />
        </div>
      </template>
    </Dialog>

    <!-- Delete User Confirmation Dialog -->
    <Dialog v-model:visible="showDeleteDialog" modal :header="t('users.deleteUser')" :style="{ width: '400px' }" @keydown.enter="deleteUser">
      <div class="flex items-center gap-3">
        <i class="pi pi-exclamation-triangle text-red-500 text-2xl"></i>
        <span>{{ t('users.confirmDeleteUser') }} <b>{{ userToDelete?.username }}</b>?</span>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showDeleteDialog = false" />
          <Button :label="t('common.delete')" icon="pi pi-trash" @click="deleteUser" severity="danger" :loading="deleting" />
        </div>
      </template>
    </Dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useI18n } from 'vue-i18n';
import { FilterMatchMode } from 'primevue/api';
import api from '../api';

const { t } = useI18n();
const toast = useToast();

const users = ref([]);
const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);

const showUserDialog = ref(false);
const showDeleteDialog = ref(false);
const editingUser = ref(null);
const userToDelete = ref(null);

const currentUserId = computed(() => {
  const userStr = localStorage.getItem('user');
  if (userStr) {
    try {
      return JSON.parse(userStr).id;
    } catch {
      return null;
    }
  }
  return null;
});

const userForm = ref({
  username: '',
  email: '',
  password: '',
  role: 'user',
  is_active: true
});

const roleOptions = [
  { label: t('settings.roleUser'), value: 'user' },
  { label: t('settings.roleAdmin'), value: 'admin' }
];

const tableFilters = ref({
  'global': { value: null, matchMode: FilterMatchMode.CONTAINS }
});

const adminCount = computed(() => users.value.filter(u => u.role === 'admin').length);
const userCount = computed(() => users.value.filter(u => u.role === 'user').length);
const mfaEnabledCount = computed(() => users.value.filter(u => u.mfa_enabled).length);

const getUserInitials = (username) => {
  if (!username) return '??';
  return username.substring(0, 2).toUpperCase();
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString();
};

const loadUsers = async () => {
  loading.value = true;
  try {
    const response = await api.get('/users/');
    users.value = response.data;
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  } finally {
    loading.value = false;
  }
};

const openUserDialog = (user = null) => {
  editingUser.value = user;
  if (user) {
    userForm.value = {
      username: user.username,
      email: user.email || '',
      password: '',
      role: user.role,
      is_active: user.is_active
    };
  } else {
    userForm.value = {
      username: '',
      email: '',
      password: '',
      role: 'user',
      is_active: true
    };
  }
  showUserDialog.value = true;
};

const saveUser = async () => {
  // Validation
  if (!editingUser.value) {
    if (!userForm.value.username || userForm.value.username.length < 3) {
      toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.usernameTooShort') });
      return;
    }
    if (!userForm.value.password || userForm.value.password.length < 8) {
      toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.passwordTooShort') });
      return;
    }
  } else {
    if (userForm.value.password && userForm.value.password.length < 8) {
      toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.passwordTooShort') });
      return;
    }
  }

  saving.value = true;
  try {
    if (editingUser.value) {
      // Update user
      const updateData = {
        email: userForm.value.email,
        role: userForm.value.role,
        is_active: userForm.value.is_active
      };
      if (userForm.value.password) {
        updateData.password = userForm.value.password;
      }
      await api.put(`/users/${editingUser.value.id}`, updateData);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('users.userUpdated') });
    } else {
      // Create user
      await api.post('/users/', userForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('users.userCreated') });
    }
    showUserDialog.value = false;
    await loadUsers();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  } finally {
    saving.value = false;
  }
};

const confirmDeleteUser = (user) => {
  userToDelete.value = user;
  showDeleteDialog.value = true;
};

const deleteUser = async () => {
  if (!userToDelete.value) return;

  deleting.value = true;
  try {
    await api.delete(`/users/${userToDelete.value.id}`);
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('users.userDeleted') });
    showDeleteDialog.value = false;
    await loadUsers();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  } finally {
    deleting.value = false;
  }
};

const onUserDialogEnter = (event) => {
  if (event.target.tagName !== 'TEXTAREA' && !saving.value) {
    event.preventDefault();
    saveUser();
  }
};

onMounted(loadUsers);
</script>
