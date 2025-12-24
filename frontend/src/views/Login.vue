<template>
  <div class="min-h-screen w-full flex items-center justify-center relative overflow-hidden bg-slate-900 font-sans text-slate-100">

    <!-- Language Toggle (Top Right) -->
    <div class="absolute top-6 right-6 z-20">
        <button @click="toggleLang" class="text-2xl hover:scale-110 transition-transform cursor-pointer focus:outline-none" title="Switch Language">
            {{ langIcon }}
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

            <form @submit.prevent="handleLogin" class="space-y-6">
                <div class="space-y-1">
                    <label class="text-xs font-bold text-blue-100 uppercase tracking-wider ml-1">{{ t('auth.username') }} <span class="text-red-500">*</span></label>
                    <div class="relative group">
                        <i class="pi pi-user absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-400 transition-colors z-20"></i>
                        <InputText
                            v-model="username"
                            :placeholder="t('auth.username')"
                            class="block w-full !pl-12 !py-3 !bg-slate-950/80 !border-slate-700 !text-white placeholder:!text-slate-500 focus:!border-blue-500 focus:!ring-1 focus:!ring-blue-500 transition-all"
                            style="padding-left: 3rem !important; background-color: #020617 !important; color: white !important;"
                        />
                    </div>
                </div>

                <div class="space-y-1">
                    <label class="text-xs font-bold text-blue-100 uppercase tracking-wider ml-1">{{ t('auth.password') }} <span class="text-red-500">*</span></label>
                    <div class="relative group">
                        <i class="pi pi-lock absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-400 transition-colors z-20"></i>
                        <InputText
                            v-model="password"
                            type="password"
                            :placeholder="t('auth.password')"
                            class="block w-full !pl-12 !py-3 !bg-slate-950/80 !border-slate-700 !text-white placeholder:!text-slate-500 focus:!border-blue-500 focus:!ring-1 focus:!ring-blue-500 transition-all"
                            style="padding-left: 3rem !important; background-color: #020617 !important; color: white !important;"
                        />
                    </div>
                </div>

                <!-- Custom Button with centered spinner -->
                <button
                    type="submit"
                    :disabled="loading"
                    class="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 border-0 text-white font-bold py-3 rounded-lg shadow-lg shadow-blue-600/20 mt-2 transform active:scale-[0.98] transition-all flex items-center justify-center gap-2 h-12"
                >
                    <i v-if="loading" class="pi pi-spinner pi-spin text-xl"></i>
                    <span>{{ t('auth.signIn') }}</span>
                </button>
            </form>

            <div class="mt-8 text-center">
                <p class="text-[10px] text-slate-600 uppercase tracking-widest">{{ t('auth.authOnly') }}</p>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useI18n } from 'vue-i18n';
import axios from 'axios';
import api from '../api';

const { t, locale } = useI18n();
const router = useRouter();
const toast = useToast();

const username = ref('');
const password = ref('');
const loading = ref(false);

const langIcon = computed(() => locale.value === 'fr' ? '🇫🇷' : '🇬🇧');

const toggleLang = () => {
    const newLang = locale.value === 'fr' ? 'en' : 'fr';
    locale.value = newLang;
    localStorage.setItem('lang', newLang);
};

onMounted(() => {
    const savedLang = localStorage.getItem('lang') || 'en';
    locale.value = savedLang;
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('user');
});

const handleLogin = async () => {
    if (!username.value || !password.value) {
        toast.add({ severity: 'warn', summary: t('auth.accessDenied'), detail: t('validation.fillRequiredFields'), life: 3000 });
        return;
    }
    loading.value = true;
    const formData = new FormData();
    formData.append('username', username.value);
    formData.append('password', password.value);

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    try {
        // Login to get token
        const res = await axios.post(`${apiUrl}/token`, formData);
        const token = res.data.access_token;
        localStorage.setItem('token', token);
        localStorage.setItem('username', username.value);

        // Fetch user data and store it for permission checks
        const userRes = await axios.get(`${apiUrl}/me`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        localStorage.setItem('user', JSON.stringify(userRes.data));

        toast.add({ severity: 'success', summary: t('auth.accessGranted'), detail: t('auth.welcomeBack'), life: 2000 });

        setTimeout(() => {
            window.location.href = '/';
        }, 500);

    } catch (e) {
        let msg = "Invalid credentials";
        if (e.response?.data?.detail) msg = e.response.data.detail;
        toast.add({ severity: 'error', summary: t('auth.accessDenied'), detail: msg, life: 3000 });
    } finally {
        loading.value = false;
    }
};
</script>
