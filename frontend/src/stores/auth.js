/**
 * Authentication Store (Pinia)
 * Manages user authentication state, token storage, and permissions.
 *
 * Role Hierarchy:
 * - user: Helpdesk only (tickets, knowledge base)
 * - tech: Granular permissions (no scripts, no system settings)
 * - admin: All tech permissions + user management (no system settings)
 * - superadmin: Full access including scripts and system settings
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'
import router from '../router'

// Role hierarchy (higher = more privileges)
const ROLE_HIERARCHY = {
  user: 0,
  tech: 1,
  admin: 2,
  superadmin: 3
}

// Available permissions
const AVAILABLE_PERMISSIONS = [
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

/**
 * Safely parse user data from localStorage with validation.
 * Returns null if data is invalid or corrupted.
 */
function parseStoredUser() {
  try {
    const stored = localStorage.getItem('user')
    if (!stored || stored === 'null' || stored === 'undefined') {
      return null
    }
    const parsed = JSON.parse(stored)
    // Validate required user properties
    if (!parsed || typeof parsed !== 'object' || !parsed.id || !parsed.username) {
      console.warn('Invalid user data in localStorage, clearing...')
      localStorage.removeItem('user')
      return null
    }
    return parsed
  } catch (e) {
    console.error('Failed to parse user from localStorage:', e)
    localStorage.removeItem('user')
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(parseStoredUser())
  const isLoading = ref(false)
  const error = ref(null)
  const mfaRequired = ref(false)
  const mfaUserId = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const username = computed(() => user.value?.username || '')
  const userRole = computed(() => user.value?.role || 'user')
  const userPermissions = computed(() => user.value?.permissions || [])

  // Role-based getters
  const isUser = computed(() => userRole.value === 'user')
  const isTech = computed(() => userRole.value === 'tech')
  const isAdmin = computed(() => userRole.value === 'admin' || userRole.value === 'superadmin')
  const isSuperadmin = computed(() => userRole.value === 'superadmin')

  const userInitials = computed(() => {
    if (!user.value?.username) return '??'
    return user.value.username.substring(0, 2).toUpperCase()
  })

  /**
   * Check if user has at least the required role level.
   */
  function hasRole(requiredRole) {
    if (!user.value || !user.value.role) return false
    const userLevel = ROLE_HIERARCHY[user.value.role] || 0
    const requiredLevel = ROLE_HIERARCHY[requiredRole] || 0
    return userLevel >= requiredLevel
  }

  /**
   * Check if user has a specific permission.
   *
   * - superadmin: Always has all permissions
   * - admin: Has all permissions (except scripts handled separately)
   * - tech: Has only their assigned permissions
   * - user: No granular permissions
   */
  function hasPermission(permission) {
    if (!user.value) return false

    // Superadmin has all permissions
    if (user.value.role === 'superadmin') return true

    // Admin has all available permissions
    if (user.value.role === 'admin') {
      return AVAILABLE_PERMISSIONS.includes(permission)
    }

    // Tech has only their assigned permissions
    if (user.value.role === 'tech') {
      return (user.value.permissions || []).includes(permission)
    }

    // Regular users have no granular permissions
    return false
  }

  /**
   * Check if user can access scripts (superadmin only).
   */
  function canAccessScripts() {
    return user.value?.role === 'superadmin'
  }

  /**
   * Check if user can access system settings (superadmin only).
   */
  function canAccessSystemSettings() {
    return user.value?.role === 'superadmin'
  }

  /**
   * Check if user can manage other users (admin and superadmin).
   */
  function canManageUsers() {
    return user.value?.role === 'admin' || user.value?.role === 'superadmin'
  }

  /**
   * Login with username and password.
   * Returns success, or mfaRequired flag if MFA is enabled.
   */
  async function login(username, password) {
    isLoading.value = true
    error.value = null
    mfaRequired.value = false

    try {
      const formData = new FormData()
      formData.append('username', username)
      formData.append('password', password)

      const response = await api.post('/token', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      })
      const data = response.data

      // Check if MFA is required
      if (data.mfa_required) {
        mfaRequired.value = true
        mfaUserId.value = data.user_id
        return { success: false, mfaRequired: true, userId: data.user_id }
      }

      // No MFA - store tokens and fetch user
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)

      // Store refresh token if provided
      if (data.refresh_token) {
        localStorage.setItem('refreshToken', data.refresh_token)
      }

      // Store user data if provided
      if (data.user) {
        user.value = data.user
        localStorage.setItem('user', JSON.stringify(data.user))
      } else {
        await fetchUser()
      }

      return { success: true }
    } catch (err) {
      // Return error type for i18n translation in component
      const detail = err.response?.data?.detail || ''

      let errorType = 'loginFailed'
      if (detail.includes('Incorrect username or password')) {
        errorType = 'incorrectCredentials'
      } else if (detail.includes('disabled')) {
        errorType = 'accountDisabled'
      } else if (detail.includes('Too many')) {
        errorType = 'rateLimited'
      }

      error.value = errorType
      return { success: false, errorType, errorDetail: detail }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Verify MFA code after password authentication.
   */
  async function verifyMfa(code) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.post('/verify-mfa', {
        user_id: mfaUserId.value,
        code: code
      })
      const data = response.data

      // Store tokens
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)

      // Store refresh token if provided
      if (data.refresh_token) {
        localStorage.setItem('refreshToken', data.refresh_token)
      }

      // Store user data
      if (data.user) {
        user.value = data.user
        localStorage.setItem('user', JSON.stringify(data.user))
      } else {
        await fetchUser()
      }

      // Reset MFA state
      mfaRequired.value = false
      mfaUserId.value = null

      return { success: true }
    } catch (err) {
      const detail = err.response?.data?.detail || ''

      let errorType = 'mfaFailed'
      if (detail.includes('Invalid MFA code')) {
        errorType = 'invalidMfaCode'
      }

      error.value = errorType
      return { success: false, errorType, errorDetail: detail }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch current user details from API.
   */
  async function fetchUser() {
    if (!token.value) return

    try {
      const response = await api.get('/me')
      user.value = response.data

      // Ensure permissions is an array
      if (!Array.isArray(user.value.permissions)) {
        user.value.permissions = []
      }

      localStorage.setItem('user', JSON.stringify(user.value))
    } catch (err) {
      // Token might be invalid
      if (err.response?.status === 401) {
        logout()
      }
    }
  }

  /**
   * Logout and clear all auth state.
   * Optionally revoke the refresh token on the server.
   */
  async function logout(revokeToken = true) {
    // Try to revoke the refresh token on the server
    if (revokeToken) {
      const refreshToken = localStorage.getItem('refreshToken')
      if (refreshToken && token.value) {
        try {
          await api.post('/logout', { refresh_token: refreshToken })
        } catch {
          // Ignore errors - we're logging out anyway
        }
      }
    }

    token.value = null
    user.value = null
    error.value = null

    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
    localStorage.removeItem('username')

    router.push('/login')
  }

  /**
   * Update current user's password.
   */
  async function updatePassword(newPassword) {
    isLoading.value = true
    error.value = null

    try {
      await api.put('/me/password', { password: newPassword })
      return { success: true }
    } catch (err) {
      const message = err.response?.data?.detail || 'Password update failed'
      error.value = message
      return { success: false, error: message }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Initialize store from localStorage.
   */
  function init() {
    const storedToken = localStorage.getItem('token')
    const storedUser = localStorage.getItem('user')

    if (storedToken) {
      token.value = storedToken
    }

    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser)
      } catch {
        user.value = null
      }
    }
  }

  return {
    // State
    token,
    user,
    isLoading,
    error,
    mfaRequired,
    mfaUserId,

    // Getters
    isAuthenticated,
    username,
    userRole,
    userPermissions,
    isUser,
    isTech,
    isAdmin,
    isSuperadmin,
    userInitials,

    // Actions
    hasRole,
    hasPermission,
    canAccessScripts,
    canAccessSystemSettings,
    canManageUsers,
    login,
    verifyMfa,
    fetchUser,
    logout,
    updatePassword,
    init
  }
})
