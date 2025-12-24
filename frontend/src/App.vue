<template>
  <div class="h-screen w-screen overflow-hidden flex bg-[var(--bg-app)] text-[var(--text-main)]" v-if="!isLoginPage">
    
    <aside class="w-64 sidebar-container flex-shrink-0 flex flex-col z-20">
      <div class="sidebar-header">
        <i class="pi pi-bolt text-blue-500 text-xl mr-3"></i>
        <span class="text-white font-bold text-lg tracking-wide">NetOps Flow</span>
      </div>

      <div class="flex-grow py-4 overflow-y-auto custom-scrollbar">
        <nav class="flex flex-col space-y-1">
            <router-link to="/" custom v-slot="{ navigate, isActive }">
                <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
                    <i class="pi pi-home mr-3"></i> {{ t('dashboard') }}
                </div>
            </router-link>
            
            <div v-if="hasPerm('ipam') || hasPerm('topology')" class="px-6 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mt-4">{{ t('network') }}</div>
            
            <router-link v-if="hasPerm('ipam')" to="/ipam" custom v-slot="{ navigate, isActive }">
                <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
                    <i class="pi pi-table mr-3"></i> {{ t('ipam') }}
                </div>
            </router-link>
            <router-link v-if="hasPerm('topology')" to="/topology" custom v-slot="{ navigate, isActive }">
                <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
                    <i class="pi pi-share-alt mr-3"></i> {{ t('topology') }}
                </div>
            </router-link>

            <div v-if="hasPerm('scripts')" class="px-6 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mt-4">{{ t('automation') }}</div>

            <router-link v-if="hasPerm('scripts')" to="/scripts" custom v-slot="{ navigate, isActive }">
                <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
                    <i class="pi pi-code mr-3"></i> {{ t('scriptRunner') }}
                </div>
            </router-link>

            <div v-if="hasPerm('inventory')" class="px-6 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mt-4">{{ t('inventory') }}</div>

            <router-link v-if="hasPerm('inventory')" to="/inventory" custom v-slot="{ navigate, isActive }">
                <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
                    <i class="pi pi-box mr-3"></i> {{ t('inventory') }}
                </div>
            </router-link>
            <router-link v-if="hasPerm('inventory')" to="/dcim" custom v-slot="{ navigate, isActive }">
                <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
                    <i class="pi pi-server mr-3"></i> {{ t('dcim') }}
                </div>
            </router-link>
            <router-link v-if="hasPerm('inventory')" to="/contracts" custom v-slot="{ navigate, isActive }">
                <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
                    <i class="pi pi-file-edit mr-3"></i> {{ t('contracts') }}
                </div>
            </router-link>
            <router-link v-if="hasPerm('inventory')" to="/software" custom v-slot="{ navigate, isActive }">
                <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
                    <i class="pi pi-desktop mr-3"></i> {{ t('software') }}
                </div>
            </router-link>

            <div class="px-6 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mt-4">{{ t('system') }}</div>

            <router-link v-if="hasPerm('settings') || user.role === 'admin'" to="/settings" custom v-slot="{ navigate, isActive }">
                <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
                    <i class="pi pi-cog mr-3"></i> {{ t('settings') }}
                </div>
            </router-link>
        </nav>
      </div>

      <div class="p-4 bg-gray-900 border-t border-gray-800">
          <div class="flex items-center justify-between">
              <div class="flex items-center gap-3 overflow-hidden">
                  <div class="w-8 h-8 rounded-full bg-blue-600 flex-shrink-0 flex items-center justify-center text-white font-bold text-xs uppercase">
                      {{ userInitials }}
                  </div>
                  <div class="text-sm overflow-hidden">
                      <div class="text-white font-medium truncate">{{ user.username }}</div>
                      <div class="text-gray-400 text-xs capitalize">{{ user.role }}</div>
                  </div>
              </div>
              <Button icon="pi pi-sign-out" text rounded class="!text-gray-400 hover:!text-white" @click="logout" v-tooltip.top="t('logout')" />
          </div>
      </div>
    </aside>

    <main class="flex-1 flex flex-col overflow-hidden relative">
      <header class="h-16 flex items-center justify-between px-8 z-10 flex-shrink-0 border-b" style="background-color: var(--bg-card); border-color: var(--border-color);">
          <h2 class="text-xl font-bold">{{ currentRouteName }}</h2>
          <div class="flex items-center gap-4">
              <button @click="toggleLang" class="text-2xl hover:scale-110 transition-transform cursor-pointer focus:outline-none mr-2">
                  {{ langIcon }}
              </button>
              <Button :icon="isDark ? 'pi pi-sun' : 'pi pi-moon'" text rounded @click="toggleTheme" class="!text-slate-500 dark:!text-yellow-400 hover:bg-slate-100 dark:hover:bg-slate-700" />
          </div>
      </header>

      <div class="flex-1 overflow-auto p-8 custom-scrollbar">
        <router-view v-slot="{ Component }">
            <component :is="Component" />
        </router-view>
      </div>
    </main>
  </div>
  
  <div v-else class="h-screen w-screen bg-slate-900 flex items-center justify-center">
      <router-view />
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from './api';
import { t, toggleLang, langIcon, initLang } from './i18n';

const route = useRoute();
const router = useRouter();
const user = ref({ username: '', role: '', permissions: {} });
const isDark = ref(false);

const isLoginPage = computed(() => route.path === '/login' || route.path === '/unauthorized');
const userInitials = computed(() => (user.value.username ? user.value.username.substring(0, 2).toUpperCase() : '??'));

const currentRouteName = computed(() => {
    // Map route names to translations keys roughly
    if(route.name === 'Dashboard') return t('dashboard').value;
    if(route.name === 'IP Address Management') return t('ipam').value;
    if(route.name === 'Network Topology') return t('topology').value;
    if(route.name === 'Script Automation') return t('scriptRunner').value;
    if(route.name === 'Inventory') return t('inventory').value;
    if(route.name === 'Settings') return t('settings').value;
    if(route.name === 'DCIM') return t('dcim').value;
    if(route.name === 'Contracts') return t('contracts').value;
    if(route.name === 'Software') return t('software').value;
    return route.name;
});

const toggleTheme = () => {
    isDark.value = !isDark.value;
    updateThemeClass();
};

const updateThemeClass = () => {
    if (isDark.value) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme', 'dark');
    } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme', 'light');
    }
};

const initTheme = () => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        isDark.value = true;
    } else {
        isDark.value = false;
    }
    updateThemeClass();
};

const hasPerm = (perm) => {
    if (user.value.role === 'admin') return true;
    return user.value.permissions && user.value.permissions[perm] === true;
};

const fetchUser = async () => {
    try {
        const res = await api.get('/me');
        user.value = res.data;
        if (!user.value.permissions) user.value.permissions = {};
    } catch (e) {
        // Handled by interceptor
    }
};

const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('user');
    router.push('/login');
};

watch(() => route.path, async (newPath) => {
    if (newPath !== '/login' && !user.value.username) {
        await fetchUser();
    }
});

onMounted(async () => {
    initTheme();
    initLang();
    if (!isLoginPage.value) {
        await fetchUser();
    }
});
</script>

<style>
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: var(--border-color);
  border-radius: 99px;
}
</style>
