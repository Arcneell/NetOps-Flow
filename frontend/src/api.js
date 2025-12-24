/**
 * Axios API Client with enhanced interceptors.
 * Handles token management, refresh, and global error notifications.
 */
import axios from 'axios'
import { useNotificationStore } from './stores/notification'

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create axios instance
const api = axios.create({
  baseURL: `${apiUrl}/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Token refresh state
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Handle 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Check if we're on login page
      if (window.location.pathname.includes('/login')) {
        return Promise.reject(error)
      }

      // Token is invalid - logout
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      localStorage.removeItem('username')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      // Check if it's a permission error vs invalid password
      const detail = error.response?.data?.detail || ''
      if (detail.includes('permission') || detail.includes('privilege')) {
        // Show toast notification if available
        showErrorToast('Permission Denied', detail)
      }
    }

    // Handle 429 Rate Limited
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after'] || 60
      showErrorToast(
        'Rate Limited',
        `Too many requests. Please try again in ${retryAfter} seconds.`
      )
    }

    // Handle 500 Server Error
    if (error.response?.status >= 500) {
      showErrorToast(
        'Server Error',
        'An unexpected error occurred. Please try again later.'
      )
    }

    // Handle network errors
    if (!error.response) {
      showErrorToast(
        'Network Error',
        'Unable to connect to the server. Please check your connection.'
      )
    }

    return Promise.reject(error)
  }
)

/**
 * Get notification store instance.
 * Wrapped in a function to avoid circular dependencies.
 */
function getNotificationStore() {
  try {
    return useNotificationStore()
  } catch (e) {
    console.error('Notification store not available:', e)
    return null
  }
}

/**
 * Show error toast notification.
 */
function showErrorToast(summary, detail) {
  const notificationStore = getNotificationStore()
  if (notificationStore) {
    notificationStore.error(summary, detail, 5000)
  } else {
    console.error(`${summary}: ${detail}`)
  }
}

/**
 * Show success toast notification.
 */
export function showSuccessToast(summary, detail) {
  const notificationStore = getNotificationStore()
  if (notificationStore) {
    notificationStore.success(summary, detail, 3000)
  }
}

/**
 * Show info toast notification.
 */
export function showInfoToast(summary, detail) {
  const notificationStore = getNotificationStore()
  if (notificationStore) {
    notificationStore.info(summary, detail, 3000)
  }
}

/**
 * Show warning toast notification.
 */
export function showWarningToast(summary, detail) {
  const notificationStore = getNotificationStore()
  if (notificationStore) {
    notificationStore.warning(summary, detail, 4000)
  }
}

export default api
