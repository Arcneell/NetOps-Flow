/**
 * Network Ports Store (Pinia)
 * Manages physical port connectivity and patching.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useNetworkPortsStore = defineStore('networkPorts', () => {
  // State
  const ports = ref([])
  const connections = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const portsByEquipment = computed(() => {
    const grouped = {}
    for (const port of ports.value) {
      const equipmentId = port.equipment_id
      if (!grouped[equipmentId]) {
        grouped[equipmentId] = []
      }
      grouped[equipmentId].push(port)
    }
    return grouped
  })

  const connectedPorts = computed(() => {
    return ports.value.filter(p => p.connected_to_id !== null)
  })

  const availablePorts = computed(() => {
    return ports.value.filter(p => p.connected_to_id === null)
  })

  // Actions
  async function fetchPorts(equipmentId = null) {
    isLoading.value = true
    error.value = null
    try {
      const params = equipmentId ? { equipment_id: equipmentId } : {}
      const response = await api.get('/network-ports/', { params })
      ports.value = response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch ports'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchEquipmentPorts(equipmentId) {
    isLoading.value = true
    try {
      const response = await api.get(`/network-ports/equipment/${equipmentId}`)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch equipment ports'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAllConnections() {
    isLoading.value = true
    try {
      const response = await api.get('/network-ports/connections/all')
      connections.value = response.data.connections
      return response.data.connections
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch connections'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function createPort(portData) {
    isLoading.value = true
    try {
      const response = await api.post('/network-ports/', portData)
      ports.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to create port'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updatePort(portId, portData) {
    isLoading.value = true
    try {
      const response = await api.put(`/network-ports/${portId}`, portData)
      const index = ports.value.findIndex(p => p.id === portId)
      if (index !== -1) {
        ports.value[index] = response.data
      }
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to update port'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deletePort(portId) {
    isLoading.value = true
    try {
      await api.delete(`/network-ports/${portId}`)
      ports.value = ports.value.filter(p => p.id !== portId)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to delete port'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function connectPorts(sourcePortId, targetPortId) {
    isLoading.value = true
    try {
      const response = await api.post(`/network-ports/${sourcePortId}/connect/${targetPortId}`)
      // Refresh ports to get updated connections
      await fetchPorts()
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to connect ports'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function disconnectPort(portId) {
    isLoading.value = true
    try {
      await api.delete(`/network-ports/${portId}/disconnect`)
      // Refresh ports
      await fetchPorts()
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to disconnect port'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    ports,
    connections,
    isLoading,
    error,

    // Getters
    portsByEquipment,
    connectedPorts,
    availablePorts,

    // Actions
    fetchPorts,
    fetchEquipmentPorts,
    fetchAllConnections,
    createPort,
    updatePort,
    deletePort,
    connectPorts,
    disconnectPort
  }
})
