<template>
  <div class="min-h-screen w-full flex items-center justify-center relative overflow-hidden font-sans"
       :style="{ background: 'var(--bg-app)' }">

    <!-- Theme & Language Toggle (Top Right) -->
    <div class="absolute top-6 right-6 z-20 flex items-center gap-2">
      <!-- Theme Toggle -->
      <button @click="toggleTheme" class="theme-toggle-login" :title="isDark ? 'Light mode' : 'Dark mode'">
        <i :class="['pi', isDark ? 'pi-sun' : 'pi-moon']"></i>
      </button>

      <!-- Language Switcher -->
      <div class="lang-switcher-login">
        <button @click="setLang('en')" :class="['lang-btn-login', locale === 'en' ? 'active' : '']" title="English">
          <svg viewBox="0 0 60 30" class="w-5 h-3.5">
            <clipPath id="s-login"><path d="M0,0 v30 h60 v-30 z"/></clipPath>
            <clipPath id="t-login"><path d="M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z"/></clipPath>
            <g clip-path="url(#s-login)">
              <path d="M0,0 v30 h60 v-30 z" fill="#012169"/>
              <path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/>
              <path d="M0,0 L60,30 M60,0 L0,30" clip-path="url(#t-login)" stroke="#C8102E" stroke-width="4"/>
              <path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/>
              <path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/>
            </g>
          </svg>
        </button>
        <button @click="setLang('fr')" :class="['lang-btn-login', locale === 'fr' ? 'active' : '']" title="Français">
          <svg viewBox="0 0 3 2" class="w-5 h-3.5">
            <rect width="1" height="2" x="0" fill="#002395"/>
            <rect width="1" height="2" x="1" fill="#fff"/>
            <rect width="1" height="2" x="2" fill="#ED2939"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Background Effects -->
    <div class="absolute inset-0 z-0 pointer-events-none overflow-hidden">
      <!-- Gradient orbs -->
      <div class="absolute -top-40 -left-40 w-96 h-96 rounded-full opacity-30"
           style="background: radial-gradient(circle, var(--primary) 0%, transparent 70%); filter: blur(80px);"></div>
      <div class="absolute -bottom-40 -right-40 w-96 h-96 rounded-full opacity-20"
           style="background: radial-gradient(circle, var(--accent-cyan) 0%, transparent 70%); filter: blur(80px);"></div>
      <!-- Grid pattern -->
      <div class="absolute inset-0 opacity-[0.03]"
           style="background-image: radial-gradient(var(--text-primary) 1px, transparent 1px); background-size: 32px 32px;"></div>
    </div>

    <!-- Login Card -->
    <div class="relative z-10 w-full max-w-md px-6">
      <div class="login-card">
        <!-- Logo & Header -->
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-5 shadow-lg"
               style="background: var(--primary-gradient); box-shadow: 0 8px 32px rgba(14, 165, 233, 0.3);">
            <i class="pi pi-server text-white text-3xl"></i>
          </div>
          <h1 class="text-3xl font-bold tracking-tight" style="color: var(--text-primary);">
            {{ t('auth.loginTitle') }}
          </h1>
          <p class="mt-2 text-sm" style="color: var(--text-tertiary);">
            {{ t('auth.loginSubtitle') }}
          </p>
        </div>

        <!-- Login Form -->
        <form v-if="!showMfaScreen" @submit.prevent="handleLogin" class="space-y-5">
          <!-- Error Alert -->
          <div v-if="errorMessage" class="error-alert">
            <div class="flex items-start gap-3">
              <i class="pi pi-exclamation-circle text-lg mt-0.5" style="color: var(--danger);"></i>
              <p class="text-sm font-medium" style="color: var(--danger);">{{ errorMessage }}</p>
            </div>
          </div>

          <!-- Username Field -->
          <div class="space-y-2">
            <label class="input-label">
              {{ t('auth.username') }} <span style="color: var(--danger);">*</span>
            </label>
            <div class="input-wrapper">
              <i class="pi pi-user input-icon"></i>
              <InputText
                v-model="username"
                :placeholder="t('auth.username')"
                class="login-input"
                @input="errorMessage = ''"
              />
            </div>
          </div>

          <!-- Password Field -->
          <div class="space-y-2">
            <label class="input-label">
              {{ t('auth.password') }} <span style="color: var(--danger);">*</span>
            </label>
            <div class="input-wrapper">
              <i class="pi pi-lock input-icon"></i>
              <Password
                v-model="password"
                :placeholder="t('auth.password')"
                :feedback="false"
                toggleMask
                class="login-password-field"
                inputClass="login-input with-icon"
                @input="errorMessage = ''"
              />
            </div>
          </div>

          <!-- Submit Button -->
          <button type="submit" :disabled="loading" class="login-button">
            <i v-if="loading" class="pi pi-spinner pi-spin text-lg"></i>
            <span>{{ t('auth.signIn') }}</span>
          </button>
        </form>

        <!-- MFA Verification Form -->
        <form v-else @submit.prevent="handleMfaVerify" class="space-y-5">
          <!-- Error Alert -->
          <div v-if="errorMessage" class="error-alert">
            <div class="flex items-start gap-3">
              <i class="pi pi-exclamation-circle text-lg mt-0.5" style="color: var(--danger);"></i>
              <p class="text-sm font-medium" style="color: var(--danger);">{{ errorMessage }}</p>
            </div>
          </div>

          <!-- MFA Info -->
          <div class="mfa-info">
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                   style="background: var(--primary-light);">
                <i class="pi pi-shield" style="color: var(--primary);"></i>
              </div>
              <div>
                <p class="font-medium text-sm" style="color: var(--text-primary);">
                  {{ t('auth.mfaRequired') }}
                </p>
                <p class="text-xs mt-1" style="color: var(--text-tertiary);">
                  {{ t('auth.mfaHint') }}
                </p>
              </div>
            </div>
          </div>

          <!-- MFA Code Input -->
          <div class="space-y-2">
            <label class="input-label">
              {{ t('auth.mfaCode') }} <span style="color: var(--danger);">*</span>
            </label>
            <InputText
              v-model="mfaCode"
              type="text"
              maxlength="6"
              :placeholder="t('auth.mfaCodePlaceholder')"
              class="login-input mfa-input"
              @input="errorMessage = ''"
              autofocus
            />
          </div>

          <!-- MFA Buttons -->
          <div class="flex gap-3">
            <button type="button" @click="backToLogin" class="login-button-secondary">
              <i class="pi pi-arrow-left"></i>
              <span>{{ t('common.cancel') }}</span>
            </button>
            <button type="submit" :disabled="loading" class="login-button flex-1">
              <i v-if="loading" class="pi pi-spinner pi-spin text-lg"></i>
              <span>{{ loading ? t('auth.verifying') : t('auth.verify') }}</span>
            </button>
          </div>
        </form>

        <!-- Footer -->
        <div class="mt-8 text-center">
          <p class="text-[10px] uppercase tracking-widest" style="color: var(--text-muted);">
            {{ t('auth.authOnly') }}
          </p>
        </div>
      </div>
    </div>

    </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useUIStore } from '../stores/ui'

const { t, locale } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUIStore()

// Theme state
const isDark = computed(() => uiStore.isDark)
const toggleTheme = () => uiStore.toggleTheme()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')
const mfaCode = ref('')
const showMfaScreen = ref(false)

const setLang = (lang) => {
  locale.value = lang
  localStorage.setItem('lang', lang)
}

onMounted(() => {
  // Initialize UI store (theme, language)
  uiStore.init()

  const savedLang = localStorage.getItem('lang') || 'en'
  locale.value = savedLang

  // Clear any existing auth data
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('user')
})

const handleLogin = async () => {
  errorMessage.value = ''

  if (!username.value || !password.value) {
    errorMessage.value = t('validation.fillRequiredFields')
    return
  }

  loading.value = true

  try {
    const result = await authStore.login(username.value, password.value)

    if (result.success) {
      router.push('/')
    } else if (result.mfaRequired) {
      showMfaScreen.value = true
      errorMessage.value = ''
    } else {
      const errorKey = result.errorType || 'loginFailed'
      errorMessage.value = t(`auth.${errorKey}`)
    }
  } catch (error) {
    errorMessage.value = t('auth.loginFailed')
  } finally {
    loading.value = false
  }
}

const handleMfaVerify = async () => {
  errorMessage.value = ''

  if (!mfaCode.value || mfaCode.value.length !== 6) {
    errorMessage.value = t('auth.invalidMfaCode')
    return
  }

  loading.value = true

  try {
    const result = await authStore.verifyMfa(mfaCode.value)

    if (result.success) {
      router.push('/')
    } else {
      const errorKey = result.errorType || 'mfaFailed'
      errorMessage.value = t(`auth.${errorKey}`)
    }
  } catch (error) {
    errorMessage.value = t('auth.mfaFailed')
  } finally {
    loading.value = false
  }
}

const backToLogin = () => {
  showMfaScreen.value = false
  mfaCode.value = ''
  errorMessage.value = ''
}
</script>

<style scoped>
/* Login Card */
.login-card {
  background: var(--bg-card);
  backdrop-filter: blur(var(--blur-lg));
  -webkit-backdrop-filter: blur(var(--blur-lg));
  border: 1px solid var(--border-default);
  border-radius: var(--radius-2xl);
  padding: 2.5rem;
  box-shadow: var(--shadow-xl);
  position: relative;
  overflow: hidden;
}

.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(14, 165, 233, 0.3), transparent);
}

/* Theme Toggle */
.theme-toggle-login {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--radius-md);
  background: var(--bg-card);
  backdrop-filter: blur(var(--blur-md));
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all var(--transition-fast);
  color: var(--text-secondary);
}

.theme-toggle-login:hover {
  background: var(--bg-secondary);
  border-color: var(--border-strong);
  color: var(--primary);
}

.theme-toggle-login i {
  font-size: 1rem;
}

/* Language Switcher */
.lang-switcher-login {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem;
  border-radius: var(--radius-md);
  background: var(--bg-card);
  backdrop-filter: blur(var(--blur-md));
  border: 1px solid var(--border-default);
}

.lang-btn-login {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem 0.5rem;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
  opacity: 0.5;
}

.lang-btn-login:hover {
  opacity: 0.8;
}

.lang-btn-login.active {
  background: var(--bg-secondary);
  opacity: 1;
}

/* Input Styles */
.input-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  margin-left: 0.25rem;
}

.input-wrapper {
  position: relative;
}

.input-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  z-index: 10;
  transition: color var(--transition-fast);
  pointer-events: none;
}

.input-wrapper:focus-within .input-icon {
  color: var(--primary);
}

.login-input {
  width: 100%;
  padding: 0.875rem 1rem 0.875rem 2.75rem !important;
  background: var(--bg-input) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: var(--radius-lg) !important;
  color: var(--text-primary) !important;
  font-size: 0.9375rem !important;
  transition: all var(--transition-fast) !important;
}

.login-input:hover {
  border-color: var(--border-strong) !important;
}

.login-input:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px var(--ring-color) !important;
  outline: none !important;
}

.login-input::placeholder {
  color: var(--text-muted) !important;
}

.login-input.mfa-input {
  text-align: center;
  font-size: 1.5rem !important;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.4em;
  font-weight: 600;
  padding: 0.875rem 1.5rem !important;
}

/* Password field wrapper */
.login-password-field {
  width: 100%;
}

.login-password-field :deep(.p-inputtext) {
  width: 100%;
  padding: 0.875rem 3rem 0.875rem 2.75rem !important;
  background: var(--bg-input) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: var(--radius-lg) !important;
  color: var(--text-primary) !important;
  font-size: 0.9375rem !important;
}

.login-password-field :deep(.p-inputtext):hover {
  border-color: var(--border-strong) !important;
}

.login-password-field :deep(.p-inputtext):focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px var(--ring-color) !important;
}

.login-password-field :deep(.p-inputtext)::placeholder {
  color: var(--text-muted) !important;
}

.login-password-field :deep(.p-password-toggle-mask-icon) {
  color: var(--text-muted);
  right: 1rem;
}

.login-password-field :deep(.p-password-toggle-mask-icon):hover {
  color: var(--text-secondary);
}

/* Buttons */
.login-button {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  background: var(--primary-gradient);
  border: none;
  border-radius: var(--radius-lg);
  color: white;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: 0 4px 14px rgba(14, 165, 233, 0.35);
}

.login-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(14, 165, 233, 0.45);
}

.login-button:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
}

.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.login-button-secondary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  color: var(--text-primary);
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.login-button-secondary:hover {
  background: var(--bg-tertiary);
  border-color: var(--border-strong);
}

/* Error Alert */
.error-alert {
  padding: 0.875rem 1rem;
  background: var(--danger-light);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-lg);
}

/* MFA Info */
.mfa-info {
  padding: 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
}

/* Responsive */
@media (max-width: 480px) {
  .login-card {
    padding: 1.75rem;
    margin: 0 0.5rem;
  }
}
</style>
