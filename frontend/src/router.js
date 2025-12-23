import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Ipam from './views/Ipam.vue'
import ScriptRunner from './views/ScriptRunner.vue'
import Topology from './views/Topology.vue'
import Login from './views/Login.vue'
import Settings from './views/Settings.vue'
import Unauthorized from './views/Unauthorized.vue'
import Inventory from './views/Inventory.vue'

const routes = [
  { path: '/login', component: Login, name: 'Login', meta: { public: true } },
  { path: '/unauthorized', component: Unauthorized, name: 'Unauthorized', meta: { public: true } },
  { path: '/', component: Dashboard, name: 'Dashboard' },
  { path: '/ipam', component: Ipam, name: 'IP Address Management', meta: { permission: 'ipam' } },
  { path: '/topology', component: Topology, name: 'Network Topology', meta: { permission: 'topology' } },
  { path: '/scripts', component: ScriptRunner, name: 'Script Automation', meta: { permission: 'scripts' } },
  { path: '/inventory', component: Inventory, name: 'Inventory', meta: { permission: 'inventory' } },
  { path: '/settings', component: Settings, name: 'Settings', meta: { permission: 'settings' } }
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

// Check if user has permission
const hasPermission = (user, permission) => {
  if (!user) return false;
  if (user.role === 'admin') return true;
  if (!permission) return true;
  return user.permissions && user.permissions[permission] === true;
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

  // Check permissions for protected routes
  const requiredPermission = to.meta.permission;
  if (requiredPermission) {
    const user = getCurrentUser();
    if (!hasPermission(user, requiredPermission)) {
      return next('/unauthorized');
    }
  }

  next();
});

export default router
