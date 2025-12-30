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

const routes = [
  { path: '/login', component: Login, name: 'Login', meta: { public: true } },
  { path: '/unauthorized', component: Unauthorized, name: 'Unauthorized', meta: { public: true } },
  { path: '/', component: Dashboard, name: 'Dashboard' },
  // Accessible to all authenticated users
  { path: '/tickets', component: Tickets, name: 'Tickets' },
  { path: '/knowledge', component: Knowledge, name: 'Knowledge Base' },
  { path: '/settings', component: Settings, name: 'Settings' },
  // Admin only routes
  { path: '/ipam', component: Ipam, name: 'IP Address Management', meta: { adminOnly: true } },
  { path: '/topology', component: Topology, name: 'Network Topology', meta: { adminOnly: true } },
  { path: '/scripts', component: ScriptRunner, name: 'Script Automation', meta: { adminOnly: true } },
  { path: '/inventory', component: Inventory, name: 'Inventory', meta: { adminOnly: true } },
  { path: '/dcim', component: Dcim, name: 'DCIM', meta: { adminOnly: true } },
  { path: '/contracts', component: Contracts, name: 'Contracts', meta: { adminOnly: true } },
  { path: '/software', component: Software, name: 'Software', meta: { adminOnly: true } },
  { path: '/users', component: UserManagement, name: 'User Management', meta: { adminOnly: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Helper to get current user from localStorage
const getCurrentUser = () => {
  const userStr = localStorage.getItem('user');
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch (e) {
      return null;
    }
  }
  return null;
};

// Check if user is admin
const isAdmin = (user) => {
  return user && user.role === 'admin';
};

router.beforeEach((to, from, next) => {
  const isPublic = to.meta.public === true;
  const loggedIn = localStorage.getItem('token');

  // If page is public, allow access
  if (isPublic) {
    // If logged in and trying to access login page, redirect to dashboard
    if (loggedIn && to.path === '/login') {
      return next('/');
    }
    return next();
  }

  // If not logged in and page requires auth, redirect to login
  if (!loggedIn) {
    return next('/login');
  }

  // Check admin-only routes
  if (to.meta.adminOnly) {
    const user = getCurrentUser();
    if (!isAdmin(user)) {
      return next('/unauthorized');
    }
  }

  next();
});

export default router
