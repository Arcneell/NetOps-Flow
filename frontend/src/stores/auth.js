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
   */
  async function login(username, password) {
    isLoading.value = true
    error.value = null

    try {
      const formData = new FormData()
      formData.append('username', username)
      formData.append('password', password)

      const response = await api.post('/token', formData)
      const data = response.data

      // Store token
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)

      // Fetch user details
      await fetchUser()

      return { success: true }
    } catch (err) {
      const message = err.response?.data?.detail || 'Login failed'
      error.value = message
      return { success: false, error: message }
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
      const response = await api.get('/users/me')
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
      await api.put('/users/me/password', { password: newPassword })
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

    // Getters
    isAuthenticated,
    isAdmin,
    username,
    userInitials,

    // Actions
    hasPermission,
    login,
    fetchUser,
    logout,
    updatePassword,
    init
  }
})
