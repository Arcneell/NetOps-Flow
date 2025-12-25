<template>
  <div class="min-h-screen w-full flex items-center justify-center relative overflow-hidden bg-slate-900 font-sans text-slate-100">

    <!-- Language Toggle (Top Right) -->
    <div class="absolute top-6 right-6 z-20 flex items-center gap-2">
        <button @click="setLang('en')" :class="['w-8 h-6 rounded overflow-hidden transition-all cursor-pointer focus:outline-none border', locale === 'en' ? 'scale-110 opacity-100 border-blue-500' : 'scale-90 opacity-50 hover:opacity-80 border-transparent']">
            <svg viewBox="0 0 60 30" class="w-full h-full">
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
        <span class="text-slate-500">/</span>
        <button @click="setLang('fr')" :class="['w-8 h-6 rounded overflow-hidden transition-all cursor-pointer focus:outline-none border', locale === 'fr' ? 'scale-110 opacity-100 border-blue-500' : 'scale-90 opacity-50 hover:opacity-80 border-transparent']">
            <svg viewBox="0 0 3 2" class="w-full h-full">
                <rect width="1" height="2" x="0" fill="#002395"/>
                <rect width="1" height="2" x="1" fill="#fff"/>
                <rect width="1" height="2" x="2" fill="#ED2939"/>
            </svg>
        </button>
    </div>

    <!-- Background -->
    <div class="absolute inset-0 z-0 pointer-events-none">
        <div class="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900/40 via-slate-900 to-slate-950"></div>
        <div class="absolute inset-0 opacity-20" style="background-image: radial-gradient(#3b82f6 1px, transparent 1px); background-size: 40px 40px;"></div>
    </div>

    <!-- Login Card -->
    <div class="relative z-10 w-full max-w-md px-6">
        <div class="bg-slate-900/80 backdrop-blur-xl border border-white/10 p-8 rounded-2xl shadow-2xl">
            <div class="text-center mb-8">
                <div class="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/30 mb-4">
                    <i class="pi pi-bolt text-white text-3xl"></i>
                </div>
                <h1 class="text-3xl font-bold text-white tracking-tight">{{ t('auth.loginTitle') }}</h1>
                <p class="text-blue-200/70 mt-2 text-sm">{{ t('auth.loginSubtitle') }}</p>
            </div>

            <!-- Login Form -->
            <form v-if="!showMfaScreen" @submit.prevent="handleLogin" class="space-y-6">
                <!-- Error Alert -->
                <div v-if="errorMessage" class="bg-red-500/10 border border-red-500/30 rounded-lg p-4 backdrop-blur-sm">
                    <div class="flex items-start gap-3">
                        <i class="pi pi-exclamation-circle text-red-400 text-xl mt-0.5"></i>
                        <div class="flex-1">
                            <p class="text-red-200 text-sm font-medium">{{ errorMessage }}</p>
                        </div>
                    </div>
                </div>

                <div class="space-y-1">
                    <label class="text-xs font-bold text-blue-100 uppercase tracking-wider ml-1">{{ t('auth.username') }} <span class="text-red-500">*</span></label>
                    <div class="relative group">
                        <i class="pi pi-user absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-400 transition-colors z-20"></i>
                        <InputText
                            v-model="username"
                            :placeholder="t('auth.username')"
                            class="block w-full !pl-12 !py-3 !bg-slate-950/80 !border-slate-700 !text-white placeholder:!text-slate-500 focus:!border-blue-500 focus:!ring-1 focus:!ring-blue-500 transition-all"
                            style="padding-left: 3rem !important; background-color: #020617 !important; color: white !important;"
                            @input="errorMessage = ''"
                        />
                    </div>
                </div>

                <div class="space-y-1">
                    <label class="text-xs font-bold text-blue-100 uppercase tracking-wider ml-1">{{ t('auth.password') }} <span class="text-red-500">*</span></label>
                    <div class="relative group">
                        <i class="pi pi-lock absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-400 transition-colors z-20"></i>
                        <InputText
                            v-model="password"
                            :type="showPassword ? 'text' : 'password'"
                            :placeholder="t('auth.password')"
                            class="block w-full !pl-12 !pr-12 !py-3 !bg-slate-950/80 !border-slate-700 !text-white placeholder:!text-slate-500 focus:!border-blue-500 focus:!ring-1 focus:!ring-blue-500 transition-all"
                            style="padding-left: 3rem !important; padding-right: 3rem !important; background-color: #020617 !important; color: white !important;"
                            @input="errorMessage = ''"
                        />
                        <button
                            type="button"
                            @click="togglePasswordVisibility"
                            class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-blue-400 transition-colors z-20 focus:outline-none"
                            :title="showPassword ? t('auth.hidePassword') : t('auth.showPassword')"
                        >
                            <i :class="showPassword ? 'pi pi-eye-slash' : 'pi pi-eye'"></i>
                        </button>
                    </div>
                </div>

                <button
                    type="submit"
                    :disabled="loading"
                    class="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:from-slate-700 disabled:to-slate-700 disabled:cursor-not-allowed border-0 text-white font-bold py-3 rounded-lg shadow-lg shadow-blue-600/20 mt-2 transform active:scale-[0.98] transition-all flex items-center justify-center gap-2 h-12"
                >
                    <i v-if="loading" class="pi pi-spinner pi-spin text-xl"></i>
                    <span>{{ t('auth.signIn') }}</span>
                </button>
            </form>

            <!-- MFA Verification Form -->
            <form v-else @submit.prevent="handleMfaVerify" class="space-y-6">
                <!-- Error Alert -->
                <div v-if="errorMessage" class="bg-red-500/10 border border-red-500/30 rounded-lg p-4 backdrop-blur-sm">
                    <div class="flex items-start gap-3">
                        <i class="pi pi-exclamation-circle text-red-400 text-xl mt-0.5"></i>
                        <div class="flex-1">
                            <p class="text-red-200 text-sm font-medium">{{ errorMessage }}</p>
                        </div>
                    </div>
                </div>

                <!-- MFA Info -->
                <div class="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 backdrop-blur-sm">
                    <div class="flex items-start gap-3">
                        <i class="pi pi-shield text-blue-400 text-xl mt-0.5"></i>
                        <div class="flex-1">
                            <p class="text-blue-200 text-sm font-medium">{{ t('auth.mfaHint') }}</p>
                        </div>
                    </div>
                </div>

                <div class="space-y-1">
                    <label class="text-xs font-bold text-blue-100 uppercase tracking-wider ml-1">{{ t('auth.mfaCode') }} <span class="text-red-500">*</span></label>
                    <div class="relative group">
                        <i class="pi pi-key absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-400 transition-colors z-20"></i>
                        <InputText
                            v-model="mfaCode"
                            type="text"
                            maxlength="6"
                            :placeholder="t('auth.mfaCodePlaceholder')"
                            class="block w-full !pl-12 !py-3 !bg-slate-950/80 !border-slate-700 !text-white placeholder:!text-slate-500 focus:!border-blue-500 focus:!ring-1 focus:!ring-blue-500 transition-all text-center tracking-widest text-2xl font-mono"
                            style="padding-left: 3rem !important; background-color: #020617 !important; color: white !important;"
                            @input="errorMessage = ''"
                            autofocus
                        />
                    </div>
                </div>

                <div class="flex gap-3">
                    <button
                        type="button"
                        @click="backToLogin"
                        class="flex-1 bg-slate-700 hover:bg-slate-600 border-0 text-white font-bold py-3 rounded-lg transform active:scale-[0.98] transition-all flex items-center justify-center gap-2 h-12"
                    >
                        <i class="pi pi-arrow-left"></i>
                        <span>{{ t('common.cancel') }}</span>
                    </button>
                    <button
                        type="submit"
                        :disabled="loading"
                        class="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:from-slate-700 disabled:to-slate-700 disabled:cursor-not-allowed border-0 text-white font-bold py-3 rounded-lg shadow-lg shadow-blue-600/20 transform active:scale-[0.98] transition-all flex items-center justify-center gap-2 h-12"
                    >
                        <i v-if="loading" class="pi pi-spinner pi-spin text-xl"></i>
                        <span>{{ loading ? t('auth.verifying') : t('auth.verify') }}</span>
                    </button>
                </div>
            </form>

            <div class="mt-8 text-center">
                <p class="text-[10px] text-slate-600 uppercase tracking-widest">{{ t('auth.authOnly') }}</p>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const { t, locale } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')
const showPassword = ref(false)
const mfaCode = ref('')
const showMfaScreen = ref(false)

const setLang = (lang) => {
    locale.value = lang
    localStorage.setItem('lang', lang)
}

const togglePasswordVisibility = () => {
    showPassword.value = !showPassword.value
}

onMounted(() => {
    const savedLang = localStorage.getItem('lang') || 'en'
    locale.value = savedLang

    // Clear any existing auth data
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('user')
})

const handleLogin = async () => {
    // Reset error message
    errorMessage.value = ''

    // Validate inputs
    if (!username.value || !password.value) {
        errorMessage.value = t('validation.fillRequiredFields')
        return
    }

    loading.value = true

    try {
        const result = await authStore.login(username.value, password.value)

        if (result.success) {
            // Redirect to dashboard
            router.push('/')
        } else if (result.mfaRequired) {
            // Show MFA screen
            showMfaScreen.value = true
            errorMessage.value = ''
        } else {
            // Display translated error message
            const errorKey = result.errorType || 'loginFailed'
            errorMessage.value = t(`auth.${errorKey}`)
        }
    } catch (error) {
        // Fallback error handling
        errorMessage.value = t('auth.loginFailed')
    } finally {
        loading.value = false
    }
}

const handleMfaVerify = async () => {
    // Reset error message
    errorMessage.value = ''

    // Validate MFA code
    if (!mfaCode.value || mfaCode.value.length !== 6) {
        errorMessage.value = t('auth.invalidMfaCode')
        return
    }

    loading.value = true

    try {
        const result = await authStore.verifyMfa(mfaCode.value)

        if (result.success) {
            // Redirect to dashboard
            router.push('/')
        } else {
            // Display translated error message
            const errorKey = result.errorType || 'mfaFailed'
            errorMessage.value = t(`auth.${errorKey}`)
        }
    } catch (error) {
        // Fallback error handling
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
