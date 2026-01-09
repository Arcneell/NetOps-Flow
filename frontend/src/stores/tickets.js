import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'
import { useAuthStore } from './auth'

export const useTicketsStore = defineStore('tickets', () => {
  // State
  const tickets = ref([])
  const currentTicket = ref(null)
  const stats = ref({
    total: 0,
    new: 0,
    open: 0,
    pending: 0,
    resolved: 0,
    closed: 0,
    sla_breached: 0,
    by_priority: {},
    by_type: {}
  })
  const loading = ref(false)
  const error = ref(null)

  // Filters
  const filters = ref({
    status: null,
    priority: null,
    ticket_type: null,
    category: null,
    search: '',
    my_tickets: false
  })

  // Getters
  const openTickets = computed(() =>
    tickets.value.filter(t => ['new', 'open', 'pending'].includes(t.status))
  )

  const myTickets = computed(() => {
    // Use auth store for reactive user data instead of localStorage
    const authStore = useAuthStore()
    const userId = authStore.user?.id
    if (!userId) return []
    return tickets.value.filter(t =>
      t.assigned_to_id === userId || t.requester_id === userId
    )
  })

  // Actions
  async function fetchTickets(options = {}) {
    loading.value = true
    error.value = null
    try {
      const params = new URLSearchParams()

      // Apply filters
      if (filters.value.status) params.append('status', filters.value.status)
      if (filters.value.priority) params.append('priority', filters.value.priority)
      if (filters.value.ticket_type) params.append('ticket_type', filters.value.ticket_type)
      if (filters.value.category) params.append('category', filters.value.category)
      if (filters.value.search) params.append('search', filters.value.search)
      if (filters.value.my_tickets) params.append('my_tickets', 'true')

      // Pagination
      if (options.skip) params.append('skip', options.skip)
      if (options.limit) params.append('limit', options.limit)

      const response = await api.get(`/tickets/?${params}`)
      tickets.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch tickets'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTicketStats() {
    try {
      const response = await api.get('/tickets/stats')
      stats.value = response.data
      return response.data
    } catch (err) {
      // Error handled by API interceptor
      throw err
    }
  }

  async function fetchTicket(id) {
    loading.value = true
    error.value = null
    try {
      const response = await api.get(`/tickets/${id}`)
      currentTicket.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch ticket'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createTicket(ticketData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.post('/tickets/', ticketData)
      tickets.value.unshift(response.data)
      await fetchTicketStats()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create ticket'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateTicket(id, ticketData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.put(`/tickets/${id}`, ticketData)
      const index = tickets.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tickets.value[index] = { ...tickets.value[index], ...response.data }
      }
      if (currentTicket.value?.id === id) {
        currentTicket.value = { ...currentTicket.value, ...response.data }
      }
      await fetchTicketStats()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update ticket'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteTicket(id) {
    loading.value = true
    error.value = null
    try {
      await api.delete(`/tickets/${id}`)
      tickets.value = tickets.value.filter(t => t.id !== id)
      if (currentTicket.value?.id === id) {
        currentTicket.value = null
      }
      await fetchTicketStats()
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to delete ticket'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addComment(ticketId, commentData) {
    try {
      const response = await api.post(`/tickets/${ticketId}/comments`, commentData)
      if (currentTicket.value?.id === ticketId) {
        currentTicket.value.comments.push(response.data)
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to add comment'
      throw err
    }
  }

  async function assignTicket(ticketId, userId) {
    try {
      const response = await api.post(`/tickets/${ticketId}/assign?user_id=${userId}`)
      await fetchTicket(ticketId)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to assign ticket'
      throw err
    }
  }

  async function resolveTicket(ticketId, resolution, resolutionCode = 'fixed') {
    try {
      const response = await api.post(
        `/tickets/${ticketId}/resolve?resolution=${encodeURIComponent(resolution)}&resolution_code=${resolutionCode}`
      )
      await fetchTicket(ticketId)
      await fetchTicketStats()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to resolve ticket'
      throw err
    }
  }

  async function closeTicket(ticketId) {
    try {
      const response = await api.post(`/tickets/${ticketId}/close`)
      await fetchTicket(ticketId)
      await fetchTicketStats()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to close ticket'
      throw err
    }
  }

  async function reopenTicket(ticketId, reason = null) {
    try {
      const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
      const response = await api.post(`/tickets/${ticketId}/reopen${params}`)
      await fetchTicket(ticketId)
      await fetchTicketStats()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to reopen ticket'
      throw err
    }
  }

  function setFilter(key, value) {
    filters.value[key] = value
  }

  function clearFilters() {
    filters.value = {
      status: null,
      priority: null,
      ticket_type: null,
      category: null,
      search: '',
      my_tickets: false
    }
  }

  return {
    // State
    tickets,
    currentTicket,
    stats,
    loading,
    error,
    filters,

    // Getters
    openTickets,
    myTickets,

    // Actions
    fetchTickets,
    fetchTicketStats,
    fetchTicket,
    createTicket,
    updateTicket,
    deleteTicket,
    addComment,
    assignTicket,
    resolveTicket,
    closeTicket,
    reopenTicket,
    setFilter,
    clearFilters
  }
})
