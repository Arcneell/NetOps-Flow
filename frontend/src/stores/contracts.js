/**
 * Contracts Store (Pinia)
 * Manages maintenance, insurance, and leasing contracts.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useContractsStore = defineStore('contracts', () => {
  // State
  const contracts = ref([])
  const expiringContracts = ref([])
  const currentContract = ref(null)
  const contractEquipment = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const contractsByType = computed(() => {
    const grouped = {}
    for (const contract of contracts.value) {
      const type = contract.contract_type
      if (!grouped[type]) {
        grouped[type] = []
      }
      grouped[type].push(contract)
    }
    return grouped
  })

  const activeContracts = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    return contracts.value.filter(c => c.start_date <= today && c.end_date >= today)
  })

  const criticalAlerts = computed(() => {
    return expiringContracts.value.filter(a => a.severity === 'critical')
  })

  // Actions
  async function fetchContracts(options = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.get('/contracts/', { params: options })
      contracts.value = response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch contracts'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchExpiringContracts(days = 30) {
    try {
      const response = await api.get('/contracts/expiring', { params: { days } })
      expiringContracts.value = response.data
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch expiring contracts'
      throw e
    }
  }

  async function fetchContract(contractId) {
    isLoading.value = true
    try {
      const response = await api.get(`/contracts/${contractId}`)
      currentContract.value = response.data
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch contract'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchContractEquipment(contractId) {
    try {
      const response = await api.get(`/contracts/${contractId}/equipment`)
      contractEquipment.value = response.data.equipment
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch contract equipment'
      throw e
    }
  }

  async function createContract(contractData) {
    isLoading.value = true
    try {
      const response = await api.post('/contracts/', contractData)
      contracts.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to create contract'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updateContract(contractId, contractData) {
    isLoading.value = true
    try {
      const response = await api.put(`/contracts/${contractId}`, contractData)
      const index = contracts.value.findIndex(c => c.id === contractId)
      if (index !== -1) {
        contracts.value[index] = response.data
      }
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to update contract'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deleteContract(contractId) {
    isLoading.value = true
    try {
      await api.delete(`/contracts/${contractId}`)
      contracts.value = contracts.value.filter(c => c.id !== contractId)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to delete contract'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function linkEquipment(contractId, equipmentId, notes = null) {
    try {
      await api.post(`/contracts/${contractId}/equipment/${equipmentId}`, null, {
        params: { notes }
      })
      await fetchContractEquipment(contractId)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to link equipment'
      throw e
    }
  }

  async function unlinkEquipment(contractId, equipmentId) {
    try {
      await api.delete(`/contracts/${contractId}/equipment/${equipmentId}`)
      contractEquipment.value = contractEquipment.value.filter(e => e.id !== equipmentId)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to unlink equipment'
      throw e
    }
  }

  return {
    // State
    contracts,
    expiringContracts,
    currentContract,
    contractEquipment,
    isLoading,
    error,

    // Getters
    contractsByType,
    activeContracts,
    criticalAlerts,

    // Actions
    fetchContracts,
    fetchExpiringContracts,
    fetchContract,
    fetchContractEquipment,
    createContract,
    updateContract,
    deleteContract,
    linkEquipment,
    unlinkEquipment
  }
})
