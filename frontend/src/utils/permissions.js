/**
 * Permissions utility functions for role-based access control.
 * Provides centralized permission checking for the frontend.
 */

// Role hierarchy (higher = more privileges)
export const ROLE_HIERARCHY = {
  user: 0,
  tech: 1,
  admin: 2,
  superadmin: 3
}

// Available permissions for granular access control
export const AVAILABLE_PERMISSIONS = [
  'ipam',
  'inventory',
  'dcim',
  'contracts',
  'software',
  'topology',
  'knowledge',
  'network_ports',
  'attachments',
  'tickets_admin',
  'reports'
]

// Permission labels for display
export const PERMISSION_LABELS = {
  ipam: 'IPAM',
  inventory: 'Inventaire',
  dcim: 'DCIM',
  contracts: 'Contrats',
  software: 'Logiciels',
  topology: 'Topologie',
  knowledge: 'Base de connaissances',
  network_ports: 'Ports réseau',
  attachments: 'Pièces jointes',
  tickets_admin: 'Administration tickets',
  reports: 'Rapports'
}

// Role labels for display
export const ROLE_LABELS = {
  user: 'Utilisateur',
  tech: 'Technicien',
  admin: 'Administrateur',
  superadmin: 'Super Administrateur'
}

/**
 * Get user from localStorage
 * @returns {Object|null} User object or null
 */
export function getCurrentUser() {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    try {
      const user = JSON.parse(userStr)
      // Ensure permissions is always an array
      if (!Array.isArray(user.permissions)) {
        user.permissions = []
      }
      return user
    } catch (e) {
      return null
    }
  }
  return null
}

/**
 * Check if user has at least the required role level
 * @param {Object} user - User object
 * @param {string} requiredRole - Required role name
 * @returns {boolean}
 */
export function hasRole(user, requiredRole) {
  if (!user || !user.role) return false
  const userLevel = ROLE_HIERARCHY[user.role] || 0
  const requiredLevel = ROLE_HIERARCHY[requiredRole] || 0
  return userLevel >= requiredLevel
}

/**
 * Check if user is superadmin
 * @param {Object} user - User object (optional, uses getCurrentUser if not provided)
 * @returns {boolean}
 */
export function isSuperadmin(user = null) {
  const u = user || getCurrentUser()
  return u && u.role === 'superadmin'
}

/**
 * Check if user is admin or superadmin
 * @param {Object} user - User object (optional, uses getCurrentUser if not provided)
 * @returns {boolean}
 */
export function isAdmin(user = null) {
  const u = user || getCurrentUser()
  return u && (u.role === 'admin' || u.role === 'superadmin')
}

/**
 * Check if user is tech, admin, or superadmin
 * @param {Object} user - User object (optional, uses getCurrentUser if not provided)
 * @returns {boolean}
 */
export function isTechOrAbove(user = null) {
  const u = user || getCurrentUser()
  return u && (u.role === 'tech' || u.role === 'admin' || u.role === 'superadmin')
}

/**
 * Check if user has a specific permission
 * @param {Object} user - User object
 * @param {string} permission - Permission name
 * @returns {boolean}
 */
export function hasPermission(user, permission) {
  if (!user) return false

  // Superadmin has all permissions
  if (user.role === 'superadmin') return true

  // Admin has all available permissions
  if (user.role === 'admin') {
    return AVAILABLE_PERMISSIONS.includes(permission)
  }

  // Tech has only their assigned permissions
  if (user.role === 'tech') {
    return (user.permissions || []).includes(permission)
  }

  // Regular users have no granular permissions
  return false
}

/**
 * Check if user can access tickets (all roles can access their own)
 * @param {Object} user - User object (optional)
 * @returns {boolean}
 */
export function canAccessTickets(user = null) {
  const u = user || getCurrentUser()
  return !!u // All authenticated users can access tickets
}

/**
 * Check if user can manage all tickets (tech, admin, superadmin)
 * @param {Object} user - User object (optional)
 * @returns {boolean}
 */
export function canManageAllTickets(user = null) {
  const u = user || getCurrentUser()
  return isTechOrAbove(u)
}

/**
 * Check if user can access knowledge base (all roles)
 * @param {Object} user - User object (optional)
 * @returns {boolean}
 */
export function canAccessKnowledge(user = null) {
  const u = user || getCurrentUser()
  return !!u // All authenticated users can access knowledge base
}

/**
 * Check if user can manage knowledge base articles (tech, admin, superadmin)
 * @param {Object} user - User object (optional)
 * @returns {boolean}
 */
export function canManageKnowledge(user = null) {
  const u = user || getCurrentUser()
  return isTechOrAbove(u)
}

/**
 * Check if user can access scripts (superadmin only)
 * @param {Object} user - User object (optional)
 * @returns {boolean}
 */
export function canAccessScripts(user = null) {
  return isSuperadmin(user)
}

/**
 * Check if user can manage users (admin, superadmin)
 * @param {Object} user - User object (optional)
 * @returns {boolean}
 */
export function canManageUsers(user = null) {
  return isAdmin(user)
}

/**
 * Check if user can access system administration (superadmin only)
 * @param {Object} user - User object (optional)
 * @returns {boolean}
 */
export function canAccessAdministration(user = null) {
  return isSuperadmin(user)
}

/**
 * Check if user can delete tickets (admin, superadmin only)
 * @param {Object} user - User object (optional)
 * @returns {boolean}
 */
export function canDeleteTickets(user = null) {
  return isAdmin(user)
}

/**
 * Check if user can delete users (admin, superadmin)
 * @param {Object} user - User object (optional)
 * @returns {boolean}
 */
export function canDeleteUsers(user = null) {
  return isAdmin(user)
}

/**
 * Check if user can create superadmins (superadmin only)
 * @param {Object} user - User object (optional)
 * @returns {boolean}
 */
export function canCreateSuperadmin(user = null) {
  return isSuperadmin(user)
}

/**
 * Get all permissions that a user has
 * @param {Object} user - User object (optional)
 * @returns {string[]} Array of permission names
 */
export function getUserPermissions(user = null) {
  const u = user || getCurrentUser()
  if (!u) return []

  // Superadmin and admin have all permissions
  if (u.role === 'superadmin' || u.role === 'admin') {
    return [...AVAILABLE_PERMISSIONS]
  }

  // Tech has their assigned permissions
  if (u.role === 'tech') {
    return (u.permissions || []).filter(p => AVAILABLE_PERMISSIONS.includes(p))
  }

  // Regular users have no permissions
  return []
}

/**
 * Get role display label
 * @param {string} role - Role name
 * @returns {string} Display label
 */
export function getRoleLabel(role) {
  return ROLE_LABELS[role] || role
}

/**
 * Get permission display label
 * @param {string} permission - Permission name
 * @returns {string} Display label
 */
export function getPermissionLabel(permission) {
  return PERMISSION_LABELS[permission] || permission
}

/**
 * Check if the current user can access a specific route
 * @param {Object} routeMeta - Route meta object
 * @returns {boolean}
 */
export function canAccessRoute(routeMeta) {
  const user = getCurrentUser()

  // Public routes
  if (routeMeta.public) return true

  // Not logged in
  if (!user) return false

  // Superadmin-only routes
  if (routeMeta.requiresSuperadmin) {
    return isSuperadmin(user)
  }

  // Role-based routes
  if (routeMeta.requiresRole) {
    return hasRole(user, routeMeta.requiresRole)
  }

  // Permission-based routes
  if (routeMeta.requiresPermission) {
    return hasPermission(user, routeMeta.requiresPermission)
  }

  // Default: allow for authenticated users
  return true
}

// Vue composable for reactive permission checks
export function usePermissions() {
  return {
    getCurrentUser,
    hasRole,
    hasPermission,
    isSuperadmin,
    isAdmin,
    isTechOrAbove,
    canAccessTickets,
    canManageAllTickets,
    canAccessKnowledge,
    canManageKnowledge,
    canAccessScripts,
    canManageUsers,
    canAccessAdministration,
    canDeleteTickets,
    canDeleteUsers,
    canCreateSuperadmin,
    getUserPermissions,
    getRoleLabel,
    getPermissionLabel,
    canAccessRoute,
    ROLE_HIERARCHY,
    AVAILABLE_PERMISSIONS,
    PERMISSION_LABELS,
    ROLE_LABELS
  }
}
