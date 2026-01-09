import { defineStore } from 'pinia'
import { ref, computed, onUnmounted } from 'vue'
import api from '../api'

export const useNotificationsStore = defineStore('notifications', () => {
  // State
  const notifications = ref([])
  const count = ref({ total: 0, unread: 0 })
  const loading = ref(false)
  const pollingInterval = ref(null)
  const isPollingActive = ref(false)

  // Getters
  const unreadNotifications = computed(() =>
    notifications.value.filter(n => !n.is_read)
  )

  const hasUnread = computed(() => count.value.unread > 0)

  // Actions
  async function fetchNotifications(options = {}) {
    loading.value = true
    try {
      const params = new URLSearchParams()
      if (options.unread_only) params.append('unread_only', 'true')
      if (options.skip) params.append('skip', options.skip)
      if (options.limit) params.append('limit', options.limit)

      const response = await api.get(`/notifications/?${params}`)
      notifications.value = response.data
      return response.data
    } catch (err) {
      // Error handled by API interceptor
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchCount() {
    try {
      const response = await api.get('/notifications/count')
      count.value = response.data
      return response.data
    } catch {
      // Silent fail for polling - don't disrupt user experience
    }
  }

  async function markAsRead(notificationId) {
    try {
      await api.put(`/notifications/${notificationId}/read`)
      const notification = notifications.value.find(n => n.id === notificationId)
      if (notification) {
        notification.is_read = true
        notification.read_at = new Date().toISOString()
      }
      count.value.unread = Math.max(0, count.value.unread - 1)
    } catch (err) {
      // Error handled by API interceptor
      throw err
    }
  }

  async function markAllAsRead() {
    try {
      await api.put('/notifications/read-all')
      notifications.value.forEach(n => {
        n.is_read = true
        n.read_at = new Date().toISOString()
      })
      count.value.unread = 0
    } catch (err) {
      // Error handled by API interceptor
      throw err
    }
  }

  async function deleteNotification(notificationId) {
    try {
      await api.delete(`/notifications/${notificationId}`)
      const index = notifications.value.findIndex(n => n.id === notificationId)
      if (index !== -1) {
        const notification = notifications.value[index]
        if (!notification.is_read) {
          count.value.unread = Math.max(0, count.value.unread - 1)
        }
        count.value.total = Math.max(0, count.value.total - 1)
        notifications.value.splice(index, 1)
      }
    } catch (err) {
      // Error handled by API interceptor
      throw err
    }
  }

  async function deleteAllRead() {
    try {
      await api.delete('/notifications/')
      notifications.value = notifications.value.filter(n => !n.is_read)
      count.value.total = count.value.unread
    } catch (err) {
      // Error handled by API interceptor
      throw err
    }
  }

  // Start polling for new notifications
  function startPolling(intervalMs = 30000) {
    // Prevent multiple polling intervals
    if (isPollingActive.value) {
      return
    }

    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
    }

    isPollingActive.value = true

    // Fetch immediately
    fetchCount()

    // Then poll at interval
    pollingInterval.value = setInterval(() => {
      // Only poll if still active (prevents zombie intervals)
      if (isPollingActive.value) {
        fetchCount()
      } else {
        clearInterval(pollingInterval.value)
        pollingInterval.value = null
      }
    }, intervalMs)
  }

  function stopPolling() {
    isPollingActive.value = false
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }
  }

  // Cleanup function to be called when store is no longer needed
  function cleanup() {
    stopPolling()
    notifications.value = []
    count.value = { total: 0, unread: 0 }
  }

  // Get notification link based on type
  function getNotificationLink(notification) {
    if (!notification.link_type || !notification.link_id) {
      return null
    }

    switch (notification.link_type) {
      case 'ticket':
        return `/tickets?id=${notification.link_id}`
      case 'equipment':
        return `/inventory?equipment=${notification.link_id}`
      case 'contract':
        return `/contracts?id=${notification.link_id}`
      case 'software':
        return `/software?id=${notification.link_id}`
      case 'article':
        return `/knowledge?article=${notification.link_id}`
      default:
        return null
    }
  }

  // Get notification icon based on type
  function getNotificationIcon(notification) {
    switch (notification.link_type) {
      case 'ticket':
        return 'pi-ticket'
      case 'equipment':
        return 'pi-box'
      case 'contract':
        return 'pi-file'
      case 'software':
        return 'pi-desktop'
      case 'article':
        return 'pi-book'
      default:
        switch (notification.notification_type) {
          case 'error':
            return 'pi-exclamation-circle'
          case 'warning':
            return 'pi-exclamation-triangle'
          case 'success':
            return 'pi-check-circle'
          default:
            return 'pi-info-circle'
        }
    }
  }

  return {
    // State
    notifications,
    count,
    loading,
    isPollingActive,

    // Getters
    unreadNotifications,
    hasUnread,

    // Actions
    fetchNotifications,
    fetchCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    deleteAllRead,
    startPolling,
    stopPolling,
    cleanup,
    getNotificationLink,
    getNotificationIcon
  }
})
