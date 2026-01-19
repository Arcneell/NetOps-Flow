import { createRouter, createWebHistory } from 'vue-router'
import {
  getCurrentUser,
  hasRole,
  hasPermission,
  isSuperadmin
} from './utils/permissions'
import { startRouteLoading, endRouteLoading } from './routeLoading'

// Eagerly loaded routes (critical path for initial page load)
import Login from './views/Login.vue'
import Dashboard from './views/Dashboard.vue'
import Unauthorized from './views/Unauthorized.vue'

// Lazily loaded routes (code splitting for performance)
// These routes will be loaded on-demand when the user navigates to them
const Ipam = () => import(/* webpackChunkName: "ipam" */ './views/Ipam.vue')
const ScriptRunner = () => import(/* webpackChunkName: "scripts" */ './views/ScriptRunner.vue')
// Topology page removed - functionality integrated into Equipment details
// const Topology = () => import(/* webpackChunkName: "topology" */ './views/Topology.vue')
const Settings = () => import(/* webpackChunkName: "settings" */ './views/Settings.vue')
const UserManagement = () => import(/* webpackChunkName: "users" */ './views/UserManagement.vue')
const Inventory = () => import(/* webpackChunkName: "inventory" */ './views/Inventory.vue')
const Dcim = () => import(/* webpackChunkName: "dcim" */ './views/Dcim.vue')
const Contracts = () => import(/* webpackChunkName: "contracts" */ './views/Contracts.vue')
const Software = () => import(/* webpackChunkName: "software" */ './views/Software.vue')
const Tickets = () => import(/* webpackChunkName: "tickets" */ './views/Tickets.vue')
const Knowledge = () => import(/* webpackChunkName: "knowledge" */ './views/Knowledge.vue')
const Administration = () => import(/* webpackChunkName: "admin" */ './views/Administration.vue')

const routes = [
  // Public routes
  { path: '/login', component: Login, name: 'Login', meta: { public: true } },
  { path: '/unauthorized', component: Unauthorized, name: 'Unauthorized', meta: { public: true } },

  // Dashboard - accessible to all authenticated users
  { path: '/', component: Dashboard, name: 'Dashboard' },

  // Helpdesk - accessible to all authenticated users
  { path: '/tickets', component: Tickets, name: 'Tickets' },
  { path: '/knowledge', component: Knowledge, name: 'Knowledge Base' },

  // User settings - accessible to all authenticated users
  { path: '/settings', component: Settings, name: 'Settings' },

  // Permission-based routes (tech with permission, admin, superadmin)
  {
    path: '/ipam',
    component: Ipam,
    name: 'IP Address Management',
    meta: { requiresPermission: 'ipam' }
  },
  // Topology page removed - network connections now shown in Equipment details slide-over
  // {
  //   path: '/topology',
  //   component: Topology,
  //   name: 'Network Topology',
  //   meta: { requiresPermission: 'topology' }
  // },
  {
    path: '/inventory',
    component: Inventory,
    name: 'Inventory',
    meta: { requiresPermission: 'inventory' }
  },
  {
    path: '/dcim',
    component: Dcim,
    name: 'DCIM',
    meta: { requiresPermission: 'dcim' }
  },
  {
    path: '/contracts',
    component: Contracts,
    name: 'Contracts',
    meta: { requiresPermission: 'contracts' }
  },
  {
    path: '/software',
    component: Software,
    name: 'Software',
    meta: { requiresPermission: 'software' }
  },

  // Superadmin only - Scripts
  {
    path: '/scripts',
    component: ScriptRunner,
    name: 'Script Automation',
    meta: { requiresSuperadmin: true }
  },

  // Admin and Superadmin - User Management
  {
    path: '/users',
    component: UserManagement,
    name: 'User Management',
    meta: { requiresRole: 'admin' }
  },

  // Superadmin only - System Administration
  {
    path: '/administration',
    component: Administration,
    name: 'Administration',
    meta: { requiresSuperadmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Indicateur de chargement (overlay) pendant les changements de page.
// Délai ~120 ms avant affichage pour éviter un flash sur les navigations rapides.
router.beforeEach((_to, _from, next) => {
  startRouteLoading()
  next()
})
router.afterEach(() => {
  endRouteLoading()
})

router.beforeEach((to, from, next) => {
  const isPublic = to.meta.public === true
  const loggedIn = localStorage.getItem('token')

  // If page is public, allow access
  if (isPublic) {
    // If logged in and trying to access login page, redirect to dashboard
    if (loggedIn && to.path === '/login') {
      return next('/')
    }
    return next()
  }

  // If not logged in and page requires auth, redirect to login
  if (!loggedIn) {
    return next('/login')
  }

  const user = getCurrentUser()

  // Check superadmin-only routes
  if (to.meta.requiresSuperadmin) {
    if (!isSuperadmin(user)) {
      return next('/unauthorized')
    }
  }

  // Check role-based routes (admin and above)
  if (to.meta.requiresRole) {
    if (!hasRole(user, to.meta.requiresRole)) {
      return next('/unauthorized')
    }
  }

  // Check permission-based routes
  if (to.meta.requiresPermission) {
    if (!hasPermission(user, to.meta.requiresPermission)) {
      return next('/unauthorized')
    }
  }

  next()
})

export default router
