<template>
  <div class="flex flex-col gap-6">
    <!-- Breadcrumbs -->
    <Breadcrumbs :items="breadcrumbItems" />

    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h1 class="text-2xl font-bold">{{ t('users.title') }}</h1>
        <p class="text-sm opacity-70">{{ t('users.subtitle') }}</p>
      </div>
      <Button :label="t('users.newUser')" icon="pi pi-plus" @click="openUserDialog()" />
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
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
        <div class="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center">
          <i class="pi pi-star text-purple-500 text-xl"></i>
        </div>
        <div>
          <div class="text-2xl font-bold">{{ superadminCount }}</div>
          <div class="text-sm opacity-70">{{ t('roles.superadmin') }}</div>
        </div>
      </div>

      <div class="card p-4 flex items-center gap-4">
        <div class="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center">
          <i class="pi pi-shield text-red-500 text-xl"></i>
        </div>
        <div>
          <div class="text-2xl font-bold">{{ adminCount }}</div>
          <div class="text-sm opacity-70">{{ t('roles.admin') }}</div>
        </div>
      </div>

      <div class="card p-4 flex items-center gap-4">
        <div class="w-12 h-12 rounded-full bg-orange-500/20 flex items-center justify-center">
          <i class="pi pi-wrench text-orange-500 text-xl"></i>
        </div>
        <div>
          <div class="text-2xl font-bold">{{ techCount }}</div>
          <div class="text-sm opacity-70">{{ t('roles.tech') }}</div>
        </div>
      </div>

      <div class="card p-4 flex items-center gap-4">
        <div class="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
          <i class="pi pi-user text-blue-500 text-xl"></i>
        </div>
        <div>
          <div class="text-2xl font-bold">{{ userCount }}</div>
          <div class="text-sm opacity-70">{{ t('roles.user') }}</div>
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
              <img v-if="slotProps.data.avatar" :src="getAvatarUrl(slotProps.data.avatar)"
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

        <Column field="role" :header="t('settings.role')" sortable style="width: 160px">
          <template #body="slotProps">
            <Tag :value="getRoleLabel(slotProps.data.role)" :severity="getRoleSeverity(slotProps.data.role)" />
          </template>
        </Column>

        <Column :header="t('users.permissions')" style="width: 200px">
          <template #body="slotProps">
            <div v-if="slotProps.data.role === 'tech' && slotProps.data.permissions?.length > 0" class="flex flex-wrap gap-1">
              <Tag v-for="perm in slotProps.data.permissions.slice(0, 3)" :key="perm"
                   :value="perm" severity="secondary" class="text-xs" />
              <Tag v-if="slotProps.data.permissions.length > 3"
                   :value="`+${slotProps.data.permissions.length - 3}`" severity="info" class="text-xs" />
            </div>
            <span v-else-if="slotProps.data.role === 'superadmin'" class="text-xs opacity-50 italic">{{ t('users.allAccess') }}</span>
            <span v-else-if="slotProps.data.role === 'admin'" class="text-xs opacity-50 italic">{{ t('users.allExceptScripts') }}</span>
            <span v-else-if="slotProps.data.role === 'user'" class="text-xs opacity-50 italic">{{ t('users.helpdeskOnly') }}</span>
            <span v-else class="text-xs opacity-50">-</span>
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
              <Button v-if="slotProps.data.id !== currentUserId && canDeleteUser(slotProps.data)"
                      icon="pi pi-trash" text rounded severity="danger" size="small"
                      @click="confirmDeleteUser(slotProps.data)" v-tooltip.top="t('common.delete')" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create/Edit User Dialog -->
    <Dialog v-model:visible="showUserDialog" modal :header="editingUser ? t('users.editUser') : t('users.newUser')"
            :style="{ width: '600px' }" @keydown.enter="onUserDialogEnter">
      <div class="flex flex-col gap-4 mt-2">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('auth.username') }} <span class="text-red-500">*</span></label>
            <InputText v-model="userForm.username" class="w-full" :disabled="editingUser" />
            <small v-if="!editingUser" class="text-xs opacity-50">{{ t('users.usernameHelp') }}</small>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">{{ t('settings.email') }}</label>
            <InputText v-model="userForm.email" type="email" class="w-full" :placeholder="t('settings.emailPlaceholder')" />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">
            {{ t('auth.password') }}
            <span v-if="!editingUser" class="text-red-500">*</span>
            <span v-else class="text-xs opacity-50 ml-1">({{ t('users.leaveBlankToKeep') }})</span>
          </label>
          <Password v-model="userForm.password" toggleMask class="w-full" inputClass="w-full" :feedback="false"
                    :class="{ 'p-invalid': userForm.password && !isPasswordValid }" />
          <!-- Password requirements checklist -->
          <div v-if="userForm.password || !editingUser" class="mt-2 p-2 rounded text-xs" style="background: var(--bg-secondary);">
            <div class="font-medium mb-1 opacity-70">{{ t('validation.passwordRequirements') }}</div>
            <div class="grid grid-cols-1 gap-1">
              <div :class="passwordChecks.minLength ? 'text-green-500' : 'opacity-50'">
                <i :class="passwordChecks.minLength ? 'pi pi-check-circle' : 'pi pi-circle'"></i>
                {{ t('validation.passwordMinLength', { min: 8 }) }}
              </div>
              <div :class="passwordChecks.hasUppercase ? 'text-green-500' : 'opacity-50'">
                <i :class="passwordChecks.hasUppercase ? 'pi pi-check-circle' : 'pi pi-circle'"></i>
                {{ t('validation.passwordRequireUppercase') }}
              </div>
              <div :class="passwordChecks.hasLowercase ? 'text-green-500' : 'opacity-50'">
                <i :class="passwordChecks.hasLowercase ? 'pi pi-check-circle' : 'pi pi-circle'"></i>
                {{ t('validation.passwordRequireLowercase') }}
              </div>
              <div :class="passwordChecks.hasDigit ? 'text-green-500' : 'opacity-50'">
                <i :class="passwordChecks.hasDigit ? 'pi pi-check-circle' : 'pi pi-circle'"></i>
                {{ t('validation.passwordRequireDigit') }}
              </div>
              <div :class="passwordChecks.hasSpecial ? 'text-green-500' : 'opacity-50'">
                <i :class="passwordChecks.hasSpecial ? 'pi pi-check-circle' : 'pi pi-circle'"></i>
                {{ t('validation.passwordRequireSpecial') }}
              </div>
            </div>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">{{ t('settings.role') }} <span class="text-red-500">*</span></label>
          <Dropdown v-model="userForm.role" :options="roleOptions" optionLabel="label" optionValue="value" class="w-full" />
          <small class="text-xs opacity-50 mt-1 block">{{ getRoleDescription(userForm.role) }}</small>
        </div>

        <!-- Granular Permissions for Tech role -->
        <div v-if="userForm.role === 'tech'" class="mt-2">
          <label class="block text-sm font-medium mb-2">{{ t('users.granularPermissions') }}</label>
          <div class="grid grid-cols-2 gap-2 p-3 rounded-lg" style="background: var(--bg-secondary);">
            <div v-for="perm in availablePermissions" :key="perm.value" class="flex items-center gap-2">
              <Checkbox v-model="userForm.permissions" :inputId="perm.value" :value="perm.value" />
              <label :for="perm.value" class="cursor-pointer text-sm">{{ perm.label }}</label>
            </div>
          </div>
          <small class="text-xs opacity-50 mt-1 block">{{ t('users.selectPermissions') }}</small>
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
    <Dialog v-model:visible="showDeleteDialog" modal :header="t('users.deleteUser')" :style="{ width: '400px' }">
      <div class="flex items-center gap-3">
        <i class="pi pi-exclamation-triangle text-red-500 text-2xl"></i>
        <span>{{ t('users.confirmDeleteUser') }} <b>{{ userToDelete?.username }}</b> ?</span>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button type="button" :label="t('common.cancel')" severity="secondary" outlined @click="showDeleteDialog = false" />
          <Button type="button" :label="t('common.delete')" icon="pi pi-trash" severity="danger" :loading="deleting" @click="deleteUser" />
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
import Breadcrumbs from '../components/shared/Breadcrumbs.vue';

const { t } = useI18n();
const toast = useToast();

// Breadcrumbs
const breadcrumbItems = computed(() => [
  { label: t('users.title'), icon: 'pi-users' }
]);

const users = ref([]);
const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);

const showUserDialog = ref(false);
const showDeleteDialog = ref(false);
const editingUser = ref(null);
const userToDelete = ref(null);

const currentUser = computed(() => {
  const userStr = localStorage.getItem('user');
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }
  return null;
});

// Password validation checks
const passwordChecks = computed(() => {
  const pwd = userForm.value.password || '';
  return {
    minLength: pwd.length >= 8,
    hasUppercase: /[A-Z]/.test(pwd),
    hasLowercase: /[a-z]/.test(pwd),
    hasDigit: /\d/.test(pwd),
    hasSpecial: /[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;'`~]/.test(pwd)
  };
});

const isPasswordValid = computed(() => {
  const checks = passwordChecks.value;
  return checks.minLength && checks.hasUppercase && checks.hasLowercase && checks.hasDigit && checks.hasSpecial;
});

const currentUserId = computed(() => currentUser.value?.id);
const currentUserRole = computed(() => currentUser.value?.role);

const userForm = ref({
  username: '',
  email: '',
  password: '',
  role: 'user',
  permissions: [],
  is_active: true
});

// Role options - admins can't create superadmins
const roleOptions = computed(() => {
  const options = [
    { label: t('roles.user'), value: 'user' },
    { label: t('roles.tech'), value: 'tech' },
    { label: t('roles.admin'), value: 'admin' }
  ];
  // Only superadmins can create other superadmins
  if (currentUserRole.value === 'superadmin') {
    options.push({ label: t('roles.superadmin'), value: 'superadmin' });
  }
  return options;
});

// Available permissions for tech role
const availablePermissions = computed(() => [
  { label: t('permissions.ipam'), value: 'ipam' },
  { label: t('permissions.inventory'), value: 'inventory' },
  { label: t('permissions.dcim'), value: 'dcim' },
  { label: t('permissions.contracts'), value: 'contracts' },
  { label: t('permissions.software'), value: 'software' },
  { label: t('permissions.topology'), value: 'topology' },
  { label: t('permissions.knowledge'), value: 'knowledge' },
  { label: t('permissions.network_ports'), value: 'network_ports' },
  { label: t('permissions.attachments'), value: 'attachments' },
  { label: t('permissions.tickets_admin'), value: 'tickets_admin' },
  { label: t('permissions.reports'), value: 'reports' }
]);

const tableFilters = ref({
  'global': { value: null, matchMode: FilterMatchMode.CONTAINS }
});

const superadminCount = computed(() => users.value.filter(u => u.role === 'superadmin').length);
const adminCount = computed(() => users.value.filter(u => u.role === 'admin').length);
const techCount = computed(() => users.value.filter(u => u.role === 'tech').length);
const userCount = computed(() => users.value.filter(u => u.role === 'user').length);

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getUserInitials = (username) => {
  if (!username) return '??';
  return username.substring(0, 2).toUpperCase();
};

const getAvatarUrl = (avatar) => {
  if (!avatar) return null;
  return `${apiUrl}/api/v1/avatars/${avatar}`;
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString();
};

const getRoleLabel = (role) => {
  const labels = {
    superadmin: t('roles.superadmin'),
    admin: t('roles.admin'),
    tech: t('roles.tech'),
    user: t('roles.user')
  };
  return labels[role] || role;
};

const getRoleSeverity = (role) => {
  const severities = {
    superadmin: 'danger',
    admin: 'warning',
    tech: 'info',
    user: 'secondary'
  };
  return severities[role] || 'secondary';
};

const getRoleDescription = (role) => {
  const descriptions = {
    user: t('users.roleDescUser'),
    tech: t('users.roleDescTech'),
    admin: t('users.roleDescAdmin'),
    superadmin: t('users.roleDescSuperadmin')
  };
  return descriptions[role] || '';
};

const canDeleteUser = (user) => {
  // Can't delete yourself
  if (user.id === currentUserId.value) return false;
  // Admins can't delete superadmins
  if (currentUserRole.value === 'admin' && user.role === 'superadmin') return false;
  return true;
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
      permissions: user.permissions || [],
      is_active: user.is_active
    };
  } else {
    userForm.value = {
      username: '',
      email: '',
      password: '',
      role: 'user',
      permissions: [],
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
    if (!userForm.value.password || !isPasswordValid.value) {
      toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.passwordTooShort') });
      return;
    }
  } else {
    if (userForm.value.password && !isPasswordValid.value) {
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
        permissions: userForm.value.role === 'tech' ? userForm.value.permissions : [],
        is_active: userForm.value.is_active
      };
      if (userForm.value.password) {
        updateData.password = userForm.value.password;
      }
      await api.put(`/users/${editingUser.value.id}`, updateData);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('users.userUpdated') });
    } else {
      // Create user
      const createData = {
        ...userForm.value,
        permissions: userForm.value.role === 'tech' ? userForm.value.permissions : []
      };
      await api.post('/users/', createData);
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
  const id = userToDelete.value.id;

  deleting.value = true;
  try {
    await api.delete(`/users/${id}`);
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('users.userDeleted') });
    showDeleteDialog.value = false;
    userToDelete.value = null;
    await loadUsers();
  } catch (e) {
    const msg = e?.response?.data?.detail ?? t('common.error');
    toast.add({ severity: 'error', summary: t('common.error'), detail: String(msg) });
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
