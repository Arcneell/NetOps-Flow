/**
 * Attachments Store (Pinia)
 * Manages file attachments for equipment.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useAttachmentsStore = defineStore('attachments', () => {
  // State
  const attachments = ref([])
  const isLoading = ref(false)
  const isUploading = ref(false)
  const uploadProgress = ref(0)
  const error = ref(null)

  // Getters
  const attachmentsByCategory = computed(() => {
    const grouped = {}
    for (const att of attachments.value) {
      const category = att.category || 'other'
      if (!grouped[category]) {
        grouped[category] = []
      }
      grouped[category].push(att)
    }
    return grouped
  })

  const totalSize = computed(() => {
    return attachments.value.reduce((sum, att) => sum + (att.file_size || 0), 0)
  })

  // Actions
  async function fetchAttachments(equipmentId, category = null) {
    isLoading.value = true
    error.value = null
    try {
      const params = category ? { category } : {}
      const response = await api.get(`/attachments/equipment/${equipmentId}`, { params })
      attachments.value = response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to fetch attachments'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function uploadAttachment(equipmentId, file, category = null, description = null) {
    isUploading.value = true
    uploadProgress.value = 0
    error.value = null

    try {
      const formData = new FormData()
      formData.append('file', file)
      if (category) formData.append('category', category)
      if (description) formData.append('description', description)

      const response = await api.post(`/attachments/equipment/${equipmentId}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          uploadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        }
      })

      attachments.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to upload attachment'
      throw e
    } finally {
      isUploading.value = false
      uploadProgress.value = 0
    }
  }

  async function updateAttachment(attachmentId, data) {
    isLoading.value = true
    try {
      const response = await api.put(`/attachments/${attachmentId}`, null, {
        params: data
      })
      const index = attachments.value.findIndex(a => a.id === attachmentId)
      if (index !== -1) {
        attachments.value[index] = response.data
      }
      return response.data
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to update attachment'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deleteAttachment(attachmentId) {
    isLoading.value = true
    try {
      await api.delete(`/attachments/${attachmentId}`)
      attachments.value = attachments.value.filter(a => a.id !== attachmentId)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to delete attachment'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function getDownloadUrl(attachmentId) {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const token = localStorage.getItem('token')
    return `${apiUrl}/attachments/${attachmentId}/download?token=${token}`
  }

  async function downloadAttachment(attachmentId) {
    try {
      const response = await api.get(`/attachments/${attachmentId}/download`, {
        responseType: 'blob'
      })

      // Find attachment to get filename
      const attachment = attachments.value.find(a => a.id === attachmentId)
      const filename = attachment?.original_filename || `attachment-${attachmentId}`

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to download attachment'
      throw e
    }
  }

  function formatFileSize(bytes) {
    if (!bytes) return '-'
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`
  }

  return {
    // State
    attachments,
    isLoading,
    isUploading,
    uploadProgress,
    error,

    // Getters
    attachmentsByCategory,
    totalSize,

    // Actions
    fetchAttachments,
    uploadAttachment,
    updateAttachment,
    deleteAttachment,
    getDownloadUrl,
    downloadAttachment,
    formatFileSize
  }
})
