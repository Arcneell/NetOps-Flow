import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Ipam from './views/Ipam.vue'
import ScriptRunner from './views/ScriptRunner.vue'
import Topology from './views/Topology.vue'
import Login from './views/Login.vue'
import Settings from './views/Settings.vue'
import UserManagement from './views/UserManagement.vue'
import Unauthorized from './views/Unauthorized.vue'
import Inventory from './views/Inventory.vue'
import Dcim from './views/Dcim.vue'
import Contracts from './views/Contracts.vue'
import Software from './views/Software.vue'
import Tickets from './views/Tickets.vue'
import Knowledge from './views/Knowledge.vue'
import Administration from './views/Administration.vue'
import {
  getCurrentUser,
  hasRole,
  hasPermission,
  isSuperadmin
} from './utils/permissions'

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
  {
    path: '/topology',
    component: Topology,
    name: 'Network Topology',
    meta: { requiresPermission: 'topology' }
  },
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
