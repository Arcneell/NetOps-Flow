<template>
  <div class="h-screen w-screen overflow-hidden flex" style="background-color: var(--bg-app); color: var(--text-primary);" v-if="!isLoginPage">

    <!-- Sidebar -->
    <aside class="sidebar-container flex-shrink-0 flex flex-col z-20">
      <!-- Logo -->
      <div class="sidebar-header">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl flex items-center justify-center" style="background: var(--primary-gradient);">
            <i class="pi pi-server text-white text-lg"></i>
          </div>
          <div>
            <span class="text-white font-bold text-base tracking-tight">Inframate</span>
            <div class="text-[10px] text-slate-400 font-medium -mt-0.5">Your Infrastructure Companion</div>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="flex-grow py-5 overflow-y-auto custom-scrollbar">
        <nav class="flex flex-col">
          <!-- Dashboard -->
          <router-link to="/" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-th-large"></i>
              <span>{{ t('nav.dashboard') }}</span>
            </div>
          </router-link>

          <!-- Helpdesk Section -->
          <div class="sidebar-section-title">Helpdesk</div>

          <router-link to="/tickets" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-ticket"></i>
              <span>{{ t('tickets.title') }}</span>
            </div>
          </router-link>
          <router-link to="/knowledge" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-book"></i>
              <span>{{ t('knowledge.title') }}</span>
            </div>
          </router-link>

          <!-- Network Section - Permission-based -->
          <div v-if="hasPermission('ipam')" class="sidebar-section-title">{{ t('nav.network') }}</div>

          <router-link v-if="hasPermission('ipam')" to="/ipam" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-sitemap"></i>
              <span>{{ t('nav.ipam') }}</span>
            </div>
          </router-link>

          <!-- Assets Section - Permission-based -->
          <div v-if="hasPermission('inventory') || hasPermission('dcim') || hasPermission('contracts') || hasPermission('software')" class="sidebar-section-title">{{ t('nav.inventory') }}</div>

          <router-link v-if="hasPermission('inventory')" to="/inventory" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-box"></i>
              <span>{{ t('nav.inventory') }}</span>
            </div>
          </router-link>
          <router-link v-if="hasPermission('dcim')" to="/dcim" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-server"></i>
              <span>{{ t('dcim.title') }}</span>
            </div>
          </router-link>
          <router-link v-if="hasPermission('contracts')" to="/contracts" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-file-edit"></i>
              <span>{{ t('contracts.title') }}</span>
            </div>
          </router-link>
          <router-link v-if="hasPermission('software')" to="/software" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-desktop"></i>
              <span>{{ t('software.title') }}</span>
            </div>
          </router-link>

          <!-- Automation Section - Superadmin only -->
          <div v-if="isSuperadmin" class="sidebar-section-title">{{ t('nav.automation') }}</div>

          <router-link v-if="isSuperadmin" to="/scripts" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-code"></i>
              <span>{{ t('nav.scriptRunner') }}</span>
            </div>
          </router-link>

          <!-- System Section - Admin and above -->
          <div v-if="isAdmin" class="sidebar-section-title">{{ t('nav.system') }}</div>

          <router-link v-if="isAdmin" to="/users" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-users"></i>
              <span>{{ t('users.title') }}</span>
            </div>
          </router-link>
          <router-link v-if="isSuperadmin" to="/administration" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-cog"></i>
              <span>{{ t('admin.title') }}</span>
            </div>
          </router-link>
        </nav>
      </div>

      <!-- User Profile -->
      <div class="sidebar-footer">
        <router-link to="/settings" class="flex items-center gap-3 flex-1 min-w-0 hover:opacity-80 transition-opacity">
          <div class="user-avatar-container">
            <img v-if="user.avatar && !avatarError" :src="`${apiUrl}/api/v1/avatars/${user.avatar}`" class="user-avatar-img" alt="" @error="avatarError = true">
            <div v-else class="user-avatar">
              {{ userInitials }}
            </div>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-white text-sm font-medium truncate">{{ user.username }}</div>
            <div class="text-slate-400 text-xs capitalize">{{ user.role }}</div>
          </div>
        </router-link>
        <Button icon="pi pi-cog" text rounded size="small"
                class="!text-slate-400 hover:!text-white hover:!bg-white/10"
                @click="$router.push('/settings')" v-tooltip.top="t('nav.settings')" />
        <Button icon="pi pi-sign-out" text rounded size="small"
                class="!text-slate-400 hover:!text-white hover:!bg-white/10"
                @click="logout" v-tooltip.top="t('nav.logout')" />
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="app-header">
        <div class="flex items-center gap-4">
          <h1 class="text-xl font-semibold" style="color: var(--text-primary);">{{ currentRouteName }}</h1>
        </div>

        <div class="flex items-center gap-2">
          <!-- Search Button -->
          <button
            @click="showCommandBar = true"
            class="search-btn flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm"
            :title="`${t('search.placeholder')} (Ctrl+K)`"
          >
            <i class="pi pi-search"></i>
            <span class="hidden md:inline opacity-60">{{ t('search.placeholder') }}</span>
            <kbd class="hidden md:inline px-1.5 py-0.5 text-xs rounded bg-gray-200 dark:bg-gray-700 opacity-60">Ctrl+K</kbd>
          </button>

          <!-- Divider -->
          <div class="header-divider"></div>

          <!-- Language Switcher -->
          <div class="lang-switcher">
            <button @click="setLang('en')"
                    :class="['lang-btn', locale === 'en' ? 'active' : '']"
                    title="English">
              <svg viewBox="0 0 60 30" class="w-5 h-3.5">
                <clipPath id="s"><path d="M0,0 v30 h60 v-30 z"/></clipPath>
                <clipPath id="t"><path d="M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z"/></clipPath>
                <g clip-path="url(#s)">
                  <path d="M0,0 v30 h60 v-30 z" fill="#012169"/>
                  <path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/>
                  <path d="M0,0 L60,30 M60,0 L0,30" clip-path="url(#t)" stroke="#C8102E" stroke-width="4"/>
                  <path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/>
                  <path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/>
                </g>
              </svg>
            </button>
            <button @click="setLang('fr')"
                    :class="['lang-btn', locale === 'fr' ? 'active' : '']"
                    title="Francais">
              <svg viewBox="0 0 3 2" class="w-5 h-3.5">
                <rect width="1" height="2" x="0" fill="#002395"/>
                <rect width="1" height="2" x="1" fill="#fff"/>
                <rect width="1" height="2" x="2" fill="#ED2939"/>
              </svg>
            </button>
          </div>

          <!-- Divider -->
          <div class="header-divider"></div>

          <!-- Notifications -->
          <NotificationBell />

          <!-- Theme Toggle -->
          <button @click="toggleTheme" class="header-icon-btn" :title="isDark ? 'Light mode' : 'Dark mode'">
            <i :class="isDark ? 'pi pi-sun' : 'pi pi-moon'"></i>
          </button>
        </div>
      </header>

      <!-- Content Area -->
      <div class="flex-1 overflow-auto custom-scrollbar" style="padding: 1.5rem 2rem;">
        <router-view v-slot="{ Component }" :key="userKey">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>

  <!-- Login Page -->
  <div v-else class="h-screen w-screen" :style="{ background: 'var(--bg-app)' }">
    <router-view />
  </div>

  <!-- Global Command Bar -->
  <CommandBar v-model="showCommandBar" />
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import api from './api';
import NotificationBell from './components/shared/NotificationBell.vue';
import CommandBar from './components/shared/CommandBar.vue';
import { useAuthStore } from './stores/auth';
import { hasPermission as checkPermission } from './utils/permissions';

const { t, locale } = useI18n();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const user = ref({ username: '', role: '', permissions: [] });
const isDark = ref(false);
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const avatarError = ref(false);
const showCommandBar = ref(false);

const isLoginPage = computed(() => route.path === '/login' || route.path === '/unauthorized');
const isSuperadmin = computed(() => user.value.role === 'superadmin');
const isAdmin = computed(() => user.value.role === 'admin' || user.value.role === 'superadmin');
const userInitials = computed(() => user.value?.username?.substring(0, 2)?.toUpperCase() || '??');
// Key for router-view to force remount when user changes (avoids cache issues on account switch)
// Uses authStore.user for reactivity when switching accounts
const userKey = computed(() => authStore.user?.id || user.value?.id || 'anonymous');

const currentRouteName = computed(() => {
  if(route.name === 'Dashboard') return t('nav.dashboard');
  if(route.name === 'IP Address Management') return t('nav.ipam');
  if(route.name === 'Network Topology') return t('nav.topology');
  if(route.name === 'Script Automation') return t('nav.scriptRunner');
  if(route.name === 'Inventory') return t('nav.inventory');
  if(route.name === 'Settings') return t('nav.settings');
  if(route.name === 'User Management') return t('users.title');
  if(route.name === 'DCIM') return t('dcim.title');
  if(route.name === 'Contracts') return t('contracts.title');
  if(route.name === 'Software') return t('software.title');
  if(route.name === 'Tickets') return t('tickets.title');
  if(route.name === 'Knowledge Base') return t('knowledge.title');
  if(route.name === 'Administration') return t('admin.title');
  return route.name;
});

const setLang = (lang) => {
  locale.value = lang;
  localStorage.setItem('lang', lang);
};

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
  isDark.value = savedTheme === 'dark';
  updateThemeClass();
};

// Use imported checkPermission with reactive user
const hasPermission = (permission) => {
  return checkPermission(user.value, permission);
};

const fetchUser = async () => {
  try {
    const res = await api.get('/me');
    user.value = res.data;
    avatarError.value = false; // Reset avatar error on user refresh
    // Ensure permissions is an array (not object)
    if (!Array.isArray(user.value.permissions)) {
      user.value.permissions = [];
    }
    // Sync with authStore for components using it
    authStore.user = { ...user.value };
    localStorage.setItem('user', JSON.stringify(user.value));
  } catch {
    // Handled by interceptor
  }
};

const logout = async () => {
  // Try to revoke refresh token on server
  const refreshToken = localStorage.getItem('refreshToken');
  if (refreshToken) {
    try {
      await api.post('/logout', { refresh_token: refreshToken });
    } catch {
      // Ignore errors - we're logging out anyway
    }
  }

  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('username');
  localStorage.removeItem('user');
  router.push('/login');
};

// Watch route changes to fetch user when navigating away from login
watch(() => route.path, async (newPath) => {
  if (newPath !== '/login' && newPath !== '/unauthorized' && !user.value.username) {
    await fetchUser();
  }
});

// Watch authStore user changes to sync local user ref (for account switching)
// Only watch the user ID to avoid deep watching the entire object (performance optimization)
watch(() => authStore.user?.id, (newId) => {
  if (newId && newId !== user.value.id) {
    user.value = { ...authStore.user };
    avatarError.value = false;
  }
});

onMounted(async () => {
  initTheme();
  const savedLang = localStorage.getItem('lang') || 'en';
  locale.value = savedLang;

  // Initialize authStore from localStorage
  authStore.init();

  if (!isLoginPage.value) {
    await fetchUser();
  }
});
</script>

<style scoped>
/* Sidebar Section Title */
.sidebar-section-title {
  padding: 1.25rem 1.25rem 0.5rem 1.25rem;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(148, 163, 184, 0.6);
}

/* Sidebar Footer */
.sidebar-footer {
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(0, 0, 0, 0.15);
}

/* User Avatar */
.user-avatar-container {
  width: 2.25rem;
  height: 2.25rem;
  flex-shrink: 0;
}

.user-avatar-img {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.625rem;
  object-fit: cover;
}

.user-avatar {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.625rem;
  background: var(--primary-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 0.75rem;
  flex-shrink: 0;
}

/* App Header */
.app-header {
  height: 4rem;
  padding: 0 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-card);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  flex-shrink: 0;
}

/* Language Switcher */
.lang-switcher {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem;
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

.lang-btn {
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

.lang-btn:hover {
  opacity: 0.8;
}

.lang-btn.active {
  background: var(--bg-card-solid);
  opacity: 1;
  box-shadow: var(--shadow-sm);
}

/* Header Divider */
.header-divider {
  width: 1px;
  height: 1.5rem;
  background: var(--border-default);
  margin: 0 0.5rem;
}

/* Header Icon Button */
.header-icon-btn {
  width: 2.25rem;
  height: 2.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.header-icon-btn:hover {
  background: var(--bg-hover);
  color: var(--primary);
}

.header-icon-btn i {
  font-size: 1.125rem;
}

/* Page Transition */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Search Button */
.search-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.search-btn:hover {
  background: var(--bg-hover);
  border-color: var(--primary);
  color: var(--primary);
}

.search-btn kbd {
  font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
}
</style>
