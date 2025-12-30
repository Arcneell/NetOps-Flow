<template>
  <div class="h-screen w-screen overflow-hidden flex" style="background-color: var(--bg-app); color: var(--text-primary);" v-if="!isLoginPage">

    <!-- Sidebar -->
    <aside class="sidebar-container flex-shrink-0 flex flex-col z-20">
      <!-- Logo -->
      <div class="sidebar-header">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl flex items-center justify-center" style="background: var(--primary-gradient);">
            <i class="pi pi-bolt text-white text-lg"></i>
          </div>
          <div>
            <span class="text-white font-bold text-base tracking-tight">NetOps Flow</span>
            <div class="text-[10px] text-slate-400 font-medium -mt-0.5">IT Operations Hub</div>
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

          <!-- Network Section - Admin only -->
          <div v-if="isAdmin" class="sidebar-section-title">{{ t('nav.network') }}</div>

          <router-link v-if="isAdmin" to="/ipam" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-sitemap"></i>
              <span>{{ t('nav.ipam') }}</span>
            </div>
          </router-link>
          <router-link v-if="isAdmin" to="/topology" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-share-alt"></i>
              <span>{{ t('nav.topology') }}</span>
            </div>
          </router-link>

          <!-- Assets Section - Admin only -->
          <div v-if="isAdmin" class="sidebar-section-title">{{ t('nav.inventory') }}</div>

          <router-link v-if="isAdmin" to="/inventory" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-box"></i>
              <span>{{ t('nav.inventory') }}</span>
            </div>
          </router-link>
          <router-link v-if="isAdmin" to="/dcim" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-server"></i>
              <span>{{ t('dcim.title') }}</span>
            </div>
          </router-link>
          <router-link v-if="isAdmin" to="/contracts" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-file-edit"></i>
              <span>{{ t('contracts.title') }}</span>
            </div>
          </router-link>
          <router-link v-if="isAdmin" to="/software" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-desktop"></i>
              <span>{{ t('software.title') }}</span>
            </div>
          </router-link>

          <!-- System Section - Admin only -->
          <div v-if="isAdmin" class="sidebar-section-title">{{ t('nav.system') }}</div>

          <router-link v-if="isAdmin" to="/settings" custom v-slot="{ navigate, isActive }">
            <div @click="navigate" :class="['sidebar-link', isActive ? 'active' : '']">
              <i class="pi pi-cog"></i>
              <span>{{ t('nav.settings') }}</span>
            </div>
          </router-link>
        </nav>
      </div>

      <!-- User Profile -->
      <div class="sidebar-footer">
        <div class="flex items-center gap-3 flex-1 min-w-0">
          <div class="user-avatar">
            {{ userInitials }}
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-white text-sm font-medium truncate">{{ user.username }}</div>
            <div class="text-slate-400 text-xs capitalize">{{ user.role }}</div>
          </div>
        </div>
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
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>

  <!-- Login Page -->
  <div v-else class="h-screen w-screen" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);">
    <router-view />
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import api from './api';
import NotificationBell from './components/shared/NotificationBell.vue';

const { t, locale } = useI18n();
const route = useRoute();
const router = useRouter();
const user = ref({ username: '', role: '', permissions: {} });
const isDark = ref(false);

const isLoginPage = computed(() => route.path === '/login' || route.path === '/unauthorized');
const isAdmin = computed(() => user.value.role === 'admin');
const userInitials = computed(() => (user.value.username ? user.value.username.substring(0, 2).toUpperCase() : '??'));

const currentRouteName = computed(() => {
  if(route.name === 'Dashboard') return t('nav.dashboard');
  if(route.name === 'IP Address Management') return t('nav.ipam');
  if(route.name === 'Network Topology') return t('nav.topology');
  if(route.name === 'Script Automation') return t('nav.scriptRunner');
  if(route.name === 'Inventory') return t('nav.inventory');
  if(route.name === 'Settings') return t('nav.settings');
  if(route.name === 'DCIM') return t('dcim.title');
  if(route.name === 'Contracts') return t('contracts.title');
  if(route.name === 'Software') return t('software.title');
  if(route.name === 'Tickets') return t('tickets.title');
  if(route.name === 'Knowledge Base') return t('knowledge.title');
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
  const savedLang = localStorage.getItem('lang') || 'en';
  locale.value = savedLang;
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
</style>
