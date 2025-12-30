<template>
  <div class="flex flex-col gap-6 max-w-4xl mx-auto">

    <!-- Profile Header with Avatar -->
    <div class="card p-6">
      <div class="flex items-center gap-6">
        <!-- Avatar Upload -->
        <div class="relative group">
          <div class="w-24 h-24 rounded-full overflow-hidden bg-slate-700 flex items-center justify-center cursor-pointer"
               @click="triggerAvatarUpload">
            <img v-if="avatarUrl" :src="avatarUrl" class="w-full h-full object-cover" alt="Profile">
            <div v-else class="w-full h-full flex items-center justify-center bg-gradient-to-br from-sky-500 to-blue-600">
              <span class="text-3xl font-bold text-white">{{ userInitials }}</span>
            </div>
            <div class="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity rounded-full">
              <i class="pi pi-camera text-white text-2xl"></i>
            </div>
          </div>
          <input ref="avatarInput" type="file" accept="image/*" class="hidden" @change="uploadAvatar">
          <Button v-if="currentUser.avatar" icon="pi pi-times" text rounded size="small"
                  class="!absolute -top-1 -right-1 !bg-red-500/80 !text-white !w-6 !h-6"
                  @click.stop="deleteAvatar" v-tooltip.top="t('settings.removeAvatar')" />
        </div>

        <!-- User Info -->
        <div class="flex-1">
          <h2 class="text-2xl font-bold">{{ currentUser.username }}</h2>
          <div class="flex items-center gap-2 mt-1 text-sm opacity-70">
            <Tag :value="currentUser.role === 'admin' ? t('settings.roleAdmin') : t('settings.roleUser')"
                 :severity="currentUser.role === 'admin' ? 'danger' : 'info'" />
            <span v-if="currentUser.email" class="ml-2">
              <i class="pi pi-envelope mr-1"></i>{{ currentUser.email }}
            </span>
          </div>
          <p v-if="currentUser.created_at" class="text-xs opacity-50 mt-2">
            {{ t('settings.memberSince') }} {{ formatDate(currentUser.created_at) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Profile Settings -->
    <div class="card p-6">
      <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
        <i class="pi pi-user text-sky-500"></i>
        {{ t('settings.profileSettings') }}
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1 opacity-70">{{ t('auth.username') }}</label>
          <InputText :value="currentUser.username" disabled class="w-full opacity-50" />
          <small class="text-xs opacity-50">{{ t('settings.usernameCannotChange') }}</small>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1 opacity-70">{{ t('settings.email') }}</label>
          <InputText v-model="profileForm.email" type="email" class="w-full" :placeholder="t('settings.emailPlaceholder')" />
        </div>
      </div>

      <div class="flex justify-end mt-4">
        <Button :label="t('settings.saveProfile')" icon="pi pi-check" @click="saveProfile" :loading="savingProfile" />
      </div>
    </div>

    <!-- Password Change -->
    <div class="card p-6">
      <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
        <i class="pi pi-lock text-orange-500"></i>
        {{ t('settings.changePassword') }}
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1 opacity-70">{{ t('settings.newPassword') }}</label>
          <Password v-model="newPassword" toggleMask class="w-full" inputClass="w-full" :feedback="false"
                    :placeholder="t('settings.newPasswordPlaceholder')" />
          <small class="text-xs opacity-50">{{ t('validation.passwordMinLength', { min: 8 }) }}</small>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1 opacity-70">{{ t('settings.confirmPassword') }}</label>
          <Password v-model="confirmPassword" toggleMask class="w-full" inputClass="w-full" :feedback="false"
                    :placeholder="t('settings.confirmPasswordPlaceholder')" />
        </div>
      </div>

      <div class="flex justify-end mt-4">
        <Button :label="t('settings.updatePassword')" icon="pi pi-check" @click="updatePassword"
                :loading="updatingPassword" :disabled="!newPassword || !confirmPassword" />
      </div>
    </div>

    <!-- Security - 2FA -->
    <div class="card p-6">
      <h3 class="text-lg font-bold mb-4 flex items-center gap-2">
        <i class="pi pi-shield text-green-500"></i>
        {{ t('settings.security') }}
      </h3>

      <div class="p-4 rounded-lg" :style="{ background: currentUser.mfa_enabled ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)' }">
        <div class="flex items-center justify-between">
          <div>
            <h4 class="font-bold flex items-center gap-2">
              <i :class="currentUser.mfa_enabled ? 'pi pi-check-circle text-green-500' : 'pi pi-exclamation-circle text-red-500'"></i>
              {{ t('settings.twoFactorAuth') }}
            </h4>
            <p class="text-sm opacity-70 mt-1">
              {{ currentUser.mfa_enabled ? t('settings.mfaEnabled') : t('settings.mfaDisabled') }}
            </p>
          </div>
          <Button
              v-if="!currentUser.mfa_enabled"
              :label="t('settings.enableMfa')"
              icon="pi pi-shield"
              @click="startMfaSetup"
              severity="success"
          />
          <Button
              v-else
              :label="t('settings.disableMfa')"
              icon="pi pi-times"
              @click="showDisableMfaDialog = true"
              severity="danger"
              outlined
          />
        </div>
      </div>
    </div>

    <!-- MFA Setup Dialog -->
    <Dialog v-model:visible="showMfaSetupDialog" modal :header="t('settings.enableMfa')" :style="{ width: '500px' }" @hide="resetMfaSetup" @keydown.enter="onMfaSetupEnter">
      <div class="flex flex-col gap-4 mt-2">
        <div v-if="mfaQrCode" class="flex flex-col items-center gap-3 p-4 bg-white rounded-lg">
          <p class="text-sm text-slate-700 text-center">{{ t('settings.qrCodeInstructions') }}</p>
          <canvas ref="qrCanvas" class="border-2 border-slate-300 rounded"></canvas>
          <p class="text-xs text-slate-500 text-center break-all font-mono">{{ mfaSecret }}</p>
        </div>

        <div class="mt-4">
          <label class="text-sm font-medium block mb-2">{{ t('settings.enterCodeToEnable') }}</label>
          <InputText v-model="mfaVerificationCode" type="text" maxlength="6" class="w-full text-center text-2xl tracking-widest font-mono" placeholder="000000" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showMfaSetupDialog = false" />
          <Button :label="t('settings.enableMfa')" icon="pi pi-check" @click="enableMfa" :loading="enablingMfa" />
        </div>
      </template>
    </Dialog>

    <!-- MFA Disable Dialog -->
    <Dialog v-model:visible="showDisableMfaDialog" modal :header="t('settings.disableMfa')" :style="{ width: '400px' }" @keydown.enter="onMfaDisableEnter">
      <div class="flex flex-col gap-4">
        <div class="flex items-center gap-3">
          <i class="pi pi-exclamation-triangle text-orange-500 text-2xl"></i>
          <span>{{ t('settings.confirmDisableMfa') }}</span>
        </div>
        <div>
          <label class="text-sm font-medium block mb-2">{{ t('settings.currentPassword') }}</label>
          <Password v-model="mfaDisablePassword" toggleMask class="w-full" inputClass="w-full" :feedback="false"
                    :placeholder="t('auth.password')" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showDisableMfaDialog = false" />
          <Button :label="t('settings.disableMfa')" icon="pi pi-times" @click="disableMfa" severity="danger" :loading="disablingMfa" />
        </div>
      </template>
    </Dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useI18n } from 'vue-i18n';
import QRCode from 'qrcode';
import api from '../api';

const { t } = useI18n();
const toast = useToast();

const currentUser = ref({ role: 'user', mfa_enabled: false });
const avatarInput = ref(null);

// Profile
const profileForm = ref({ email: '' });
const savingProfile = ref(false);

// Password
const newPassword = ref('');
const confirmPassword = ref('');
const updatingPassword = ref(false);

// MFA state
const showMfaSetupDialog = ref(false);
const showDisableMfaDialog = ref(false);
const mfaSecret = ref('');
const mfaQrCode = ref('');
const mfaVerificationCode = ref('');
const mfaDisablePassword = ref('');
const enablingMfa = ref(false);
const disablingMfa = ref(false);
const qrCanvas = ref(null);

const userInitials = computed(() => {
  if (!currentUser.value?.username) return '??';
  return currentUser.value.username.substring(0, 2).toUpperCase();
});

const avatarUrl = computed(() => {
  if (!currentUser.value?.avatar) return null;
  return `/api/v1/avatars/${currentUser.value.avatar}`;
});

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString();
};

const loadUserData = async () => {
  try {
    const response = await api.get('/me');
    currentUser.value = response.data;
    profileForm.value.email = currentUser.value.email || '';

    // Also update localStorage
    localStorage.setItem('user', JSON.stringify(currentUser.value));
  } catch (e) {
    console.error('Failed to load user data:', e);
  }
};

const triggerAvatarUpload = () => {
  avatarInput.value?.click();
};

const uploadAvatar = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;

  // Validate file size (max 2MB)
  if (file.size > 2 * 1024 * 1024) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('settings.avatarTooLarge') });
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    await api.post('/me/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('settings.avatarUpdated') });
    await loadUserData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }

  // Reset input
  event.target.value = '';
};

const deleteAvatar = async () => {
  try {
    await api.delete('/me/avatar');
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('settings.avatarDeleted') });
    await loadUserData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  }
};

const saveProfile = async () => {
  savingProfile.value = true;
  try {
    await api.put('/me/profile', { email: profileForm.value.email });
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('settings.profileUpdated') });
    await loadUserData();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  } finally {
    savingProfile.value = false;
  }
};

const updatePassword = async () => {
  if (!newPassword.value || newPassword.value.length < 8) {
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.passwordTooShort') });
    return;
  }

  if (newPassword.value !== confirmPassword.value) {
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('settings.passwordMismatch') });
    return;
  }

  updatingPassword.value = true;
  try {
    await api.put('/me/password', { password: newPassword.value });
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('users.passwordUpdated') });
    newPassword.value = '';
    confirmPassword.value = '';
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  } finally {
    updatingPassword.value = false;
  }
};

// MFA Functions
const startMfaSetup = async () => {
  try {
    const response = await api.post('/mfa/setup');
    mfaSecret.value = response.data.secret;
    mfaQrCode.value = response.data.qr_uri;
    showMfaSetupDialog.value = true;

    await nextTick();
    if (qrCanvas.value && mfaQrCode.value) {
      QRCode.toCanvas(qrCanvas.value, mfaQrCode.value, {
        width: 256,
        margin: 2,
        color: { dark: '#000000', light: '#FFFFFF' }
      });
    }
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('settings.mfaSetupFailed') });
  }
};

const enableMfa = async () => {
  if (!mfaVerificationCode.value || mfaVerificationCode.value.length !== 6) {
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('auth.invalidMfaCode') });
    return;
  }

  enablingMfa.value = true;
  try {
    await api.post('/mfa/enable-with-secret', null, {
      params: { secret: mfaSecret.value, code: mfaVerificationCode.value }
    });
    showMfaSetupDialog.value = false;
    await loadUserData();
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('settings.mfaEnabledSuccess') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  } finally {
    enablingMfa.value = false;
  }
};

const disableMfa = async () => {
  if (!mfaDisablePassword.value) {
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.fillRequiredFields') });
    return;
  }

  disablingMfa.value = true;
  try {
    await api.post('/mfa/disable', { password: mfaDisablePassword.value });
    showDisableMfaDialog.value = false;
    mfaDisablePassword.value = '';
    await loadUserData();
    toast.add({ severity: 'success', summary: t('common.success'), detail: t('settings.mfaDisabledSuccess') });
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  } finally {
    disablingMfa.value = false;
  }
};

const resetMfaSetup = () => {
  mfaSecret.value = '';
  mfaQrCode.value = '';
  mfaVerificationCode.value = '';
};

const onMfaSetupEnter = (event) => {
  if (event.target.tagName !== 'TEXTAREA' && !enablingMfa.value) {
    event.preventDefault();
    enableMfa();
  }
};

const onMfaDisableEnter = (event) => {
  if (event.target.tagName !== 'TEXTAREA' && !disablingMfa.value) {
    event.preventDefault();
    disableMfa();
  }
};

onMounted(loadUserData);
</script>
