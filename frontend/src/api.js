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
  withCredentials: true, // Send cookies with requests (HTTP-only refresh token)
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

/**
 * Refresh the access token using the HTTP-only cookie.
 * The refresh token is stored in an HTTP-only cookie for security (XSS protection).
 * Returns the new access token or null if refresh fails.
 */
async function refreshAccessToken() {
  try {
    // Make request with credentials - cookie will be sent automatically
    const response = await axios.post(`${apiUrl}/api/v1/refresh`, {}, {
      withCredentials: true // Ensure cookie is sent
    })

    const { access_token } = response.data

    // Validate response contains valid access token before storing
    if (!access_token || typeof access_token !== 'string' || access_token.length < 10) {
      console.error('Invalid access token received from refresh endpoint')
      throw new Error('Invalid token response')
    }

    // Store new access token (refresh token is in HTTP-only cookie)
    localStorage.setItem('token', access_token)

    // Update user data if provided and valid
    if (response.data.user && typeof response.data.user === 'object' && response.data.user.id) {
      localStorage.setItem('user', JSON.stringify(response.data.user))
    }

    return access_token
  } catch (error) {
    // Log error for debugging (without sensitive data)
    console.error('Token refresh failed:', error.message || 'Unknown error')
    // Refresh failed - clear access token and user data
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    return null
  }
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
      // Check if we're on login page or refresh endpoint
      if (window.location.pathname.includes('/login') ||
          originalRequest.url?.includes('/refresh')) {
        return Promise.reject(error)
      }

      // If already refreshing, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          // Validate token before retry to prevent race condition
          if (!token) {
            return Promise.reject(new Error('Token refresh failed'))
          }
          originalRequest.headers['Authorization'] = `Bearer ${token}`
          return api(originalRequest)
        }).catch(err => {
          return Promise.reject(err)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      // Try to refresh the token
      const newToken = await refreshAccessToken()

      if (newToken) {
        // Retry original request with new token
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`
        processQueue(null, newToken)
        isRefreshing = false
        return api(originalRequest)
      } else {
        // Refresh failed - redirect to login
        processQueue(new Error('Token refresh failed'), null)
        isRefreshing = false
        window.location.href = '/login'
        return Promise.reject(error)
      }
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
  } catch {
    // Notification store not available during initialization
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
  }
  // Silent fallback if notification store not available
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
