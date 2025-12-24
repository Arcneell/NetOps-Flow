/**
 * Software & Licenses Store (Pinia)
 * Manages software inventory, licenses, and compliance.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useSoftwareStore = defineStore('software', () => {
  // State
  const software = ref([])
  const licenses = ref([])
  const installations = ref([])
  const expiringLicenses = ref([])
  const complianceOverview = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const softwareByCategory = computed(() => {
    const grouped = {}
    for (const sw of software.value) {
      const category = sw.category || 'other'
      if (!grouped[category]) {
        grouped[category] = []
      }
      grouped[category].push(sw)
    }
    return grouped
  })

  const violatedSoftware = computed(() => {
    return software.value.filter(sw => sw.compliance_status === 'violation')
  })

  const warningSoftware = computed(() => {
    return software.value.filter(sw => sw.compliance_status === 'warning')
  })

  // Actions
  async function fetchSoftware(category = null) {
    isLoading.value = true
    error.value = null
    try {
      const params = category ? { category } : {}
      const response = await api.get('/software/', { params })
      software.value = response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch software'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchComplianceOverview() {
    try {
      const response = await api.get('/software/compliance')
      complianceOverview.value = response.data
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch compliance overview'
      throw e
    }
  }

  async function fetchExpiringLicenses(days = 30) {
    try {
      const response = await api.get('/software/licenses/expiring', { params: { days } })
      expiringLicenses.value = response.data
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch expiring licenses'
      throw e
    }
  }

  async function createSoftware(softwareData) {
    isLoading.value = true
    try {
      const response = await api.post('/software/', softwareData)
      software.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to create software'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updateSoftware(softwareId, softwareData) {
    isLoading.value = true
    try {
      const response = await api.put(`/software/${softwareId}`, softwareData)
      const index = software.value.findIndex(s => s.id === softwareId)
      if (index !== -1) {
        software.value[index] = response.data
      }
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to update software'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deleteSoftware(softwareId) {
    isLoading.value = true
    try {
      await api.delete(`/software/${softwareId}`)
      software.value = software.value.filter(s => s.id !== softwareId)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to delete software'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // License actions
  async function fetchLicenses(softwareId) {
    try {
      const response = await api.get(`/software/${softwareId}/licenses`)
      licenses.value = response.data
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch licenses'
      throw e
    }
  }

  async function createLicense(softwareId, licenseData) {
    try {
      const response = await api.post(`/software/${softwareId}/licenses`, licenseData)
      licenses.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to create license'
      throw e
    }
  }

  async function deleteLicense(licenseId) {
    try {
      await api.delete(`/software/licenses/${licenseId}`)
      licenses.value = licenses.value.filter(l => l.id !== licenseId)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to delete license'
      throw e
    }
  }

  // Installation actions
  async function fetchInstallations(softwareId) {
    try {
      const response = await api.get(`/software/${softwareId}/installations`)
      installations.value = response.data
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch installations'
      throw e
    }
  }

  async function createInstallation(softwareId, installationData) {
    try {
      const response = await api.post(`/software/${softwareId}/installations`, installationData)
      installations.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to create installation'
      throw e
    }
  }

  async function deleteInstallation(installationId) {
    try {
      await api.delete(`/software/installations/${installationId}`)
      installations.value = installations.value.filter(i => i.id !== installationId)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to delete installation'
      throw e
    }
  }

  return {
    // State
    software,
    licenses,
    installations,
    expiringLicenses,
    complianceOverview,
    isLoading,
    error,

    // Getters
    softwareByCategory,
    violatedSoftware,
    warningSoftware,

    // Actions
    fetchSoftware,
    fetchComplianceOverview,
    fetchExpiringLicenses,
    createSoftware,
    updateSoftware,
    deleteSoftware,
    fetchLicenses,
    createLicense,
    deleteLicense,
    fetchInstallations,
    createInstallation,
    deleteInstallation
  }
})
