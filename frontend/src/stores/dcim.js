/**
 * DCIM Store (Pinia)
 * Manages racks, PDUs and datacenter infrastructure.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useDcimStore = defineStore('dcim', () => {
  // State
  const racks = ref([])
  const pdus = ref([])
  const currentRack = ref(null)
  const currentRackLayout = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const racksByLocation = computed(() => {
    const grouped = {}
    for (const rack of racks.value) {
      const locationId = rack.location_id
      if (!grouped[locationId]) {
        grouped[locationId] = []
      }
      grouped[locationId].push(rack)
    }
    return grouped
  })

  const pdusByRack = computed(() => {
    const grouped = {}
    for (const pdu of pdus.value) {
      const rackId = pdu.rack_id || 'unassigned'
      if (!grouped[rackId]) {
        grouped[rackId] = []
      }
      grouped[rackId].push(pdu)
    }
    return grouped
  })

  // Actions
  async function fetchRacks(locationId = null) {
    isLoading.value = true
    error.value = null
    try {
      const params = locationId ? { location_id: locationId } : {}
      const response = await api.get('/dcim/racks/', { params })
      racks.value = response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch racks'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchRack(rackId) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.get(`/dcim/racks/${rackId}`)
      currentRack.value = response.data
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch rack'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchRackLayout(rackId) {
    isLoading.value = true
    try {
      const response = await api.get(`/dcim/racks/${rackId}/layout`)
      currentRackLayout.value = response.data
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch rack layout'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function createRack(rackData) {
    isLoading.value = true
    try {
      const response = await api.post('/dcim/racks/', rackData)
      racks.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to create rack'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updateRack(rackId, rackData) {
    isLoading.value = true
    try {
      const response = await api.put(`/dcim/racks/${rackId}`, rackData)
      const index = racks.value.findIndex(r => r.id === rackId)
      if (index !== -1) {
        racks.value[index] = response.data
      }
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to update rack'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deleteRack(rackId) {
    isLoading.value = true
    try {
      await api.delete(`/dcim/racks/${rackId}`)
      racks.value = racks.value.filter(r => r.id !== rackId)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to delete rack'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchPdus(rackId = null) {
    isLoading.value = true
    try {
      const params = rackId ? { rack_id: rackId } : {}
      const response = await api.get('/dcim/pdus/', { params })
      pdus.value = response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch PDUs'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function createPdu(pduData) {
    isLoading.value = true
    try {
      const response = await api.post('/dcim/pdus/', pduData)
      pdus.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to create PDU'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updatePdu(pduId, pduData) {
    isLoading.value = true
    try {
      const response = await api.put(`/dcim/pdus/${pduId}`, pduData)
      const index = pdus.value.findIndex(p => p.id === pduId)
      if (index !== -1) {
        pdus.value[index] = response.data
      }
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to update PDU'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deletePdu(pduId) {
    isLoading.value = true
    try {
      await api.delete(`/dcim/pdus/${pduId}`)
      pdus.value = pdus.value.filter(p => p.id !== pduId)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to delete PDU'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchPduPorts(pduId) {
    try {
      const response = await api.get(`/dcim/pdus/${pduId}/ports`)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch PDU ports'
      throw e
    }
  }

  return {
    // State
    racks,
    pdus,
    currentRack,
    currentRackLayout,
    isLoading,
    error,

    // Getters
    racksByLocation,
    pdusByRack,

    // Actions
    fetchRacks,
    fetchRack,
    fetchRackLayout,
    createRack,
    updateRack,
    deleteRack,
    fetchPdus,
    createPdu,
    updatePdu,
    deletePdu,
    fetchPduPorts
  }
})
