/**
 * Authentication Store (Pinia)
 * Manages user authentication state, token storage, and permissions.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const isLoading = ref(false)
  const error = ref(null)
  const mfaRequired = ref(false)
  const mfaUserId = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const username = computed(() => user.value?.username || '')
  const userInitials = computed(() => {
    if (!user.value?.username) return '??'
    return user.value.username.substring(0, 2).toUpperCase()
  })

  /**
   * Check if user has a specific permission.
   */
  function hasPermission(permission) {
    if (!user.value) return false
    if (user.value.role === 'admin') return true
    if (!permission) return true
    return user.value.permissions?.[permission] === true
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

      // No MFA - store token and fetch user
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)

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

      // Store token
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)

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

      if (!user.value.permissions) {
        user.value.permissions = {}
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
   */
  function logout() {
    token.value = null
    user.value = null
    error.value = null

    localStorage.removeItem('token')
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
    isAdmin,
    username,
    userInitials,

    // Actions
    hasPermission,
    login,
    verifyMfa,
    fetchUser,
    logout,
    updatePassword,
    init
  }
})
