import { defineStore } from 'pinia'
import { ref, computed, shallowRef } from 'vue'
import api from '../api'

/**
 * Inventory Store with Local Caching
 *
 * Features:
 * - Local cache with TTL to reduce redundant API calls
 * - Optimistic updates for better UX
 * - Smart invalidation on mutations
 * - Debounced fetch to prevent rapid successive calls
 */

// Cache configuration
const CACHE_TTL_MS = 2 * 60 * 1000 // 2 minutes cache TTL (matches backend Redis TTL)
const DEBOUNCE_MS = 300 // Debounce rapid fetch calls

export const useInventoryStore = defineStore('inventory', () => {
  // State - use shallowRef for large arrays to reduce reactivity overhead
  // Only the array reference triggers updates, not deep changes
  const equipment = shallowRef([])
  const manufacturers = shallowRef([])
  const models = shallowRef([])
  const types = shallowRef([])
  const locations = shallowRef([])
  const suppliers = shallowRef([])

  const loading = ref(false)
  const error = ref(null)

  // Cache metadata
  const cacheTimestamps = ref({
    equipment: null,
    manufacturers: null,
    models: null,
    types: null,
    locations: null,
    suppliers: null
  })

  // Debounce timer refs
  let fetchDebounceTimer = null

  // Memoization cache for expensive computed operations
  // Invalidated when equipment array reference changes
  const memoCache = ref({
    byStatus: null,
    byLocation: null,
    equipmentVersion: 0
  })

  // Track equipment version to invalidate memo cache
  const equipmentVersion = computed(() => equipment.value.length)

  // Getters
  const activeEquipment = computed(() =>
    equipment.value.filter(e => e.status === 'in_service')
  )

  // Memoized grouping - only recalculates when equipment changes
  const equipmentByStatus = computed(() => {
    // Use version to detect changes
    if (memoCache.value.byStatus && memoCache.value.equipmentVersion === equipmentVersion.value) {
      return memoCache.value.byStatus
    }

    const grouped = {
      in_service: [],
      in_stock: [],
      maintenance: [],
      retired: []
    }
    equipment.value.forEach(e => {
      if (grouped[e.status]) {
        grouped[e.status].push(e)
      }
    })

    // Cache result
    memoCache.value.byStatus = grouped
    memoCache.value.equipmentVersion = equipmentVersion.value
    return grouped
  })

  const equipmentByLocation = computed(() => {
    // Use version to detect changes
    if (memoCache.value.byLocation && memoCache.value.equipmentVersion === equipmentVersion.value) {
      return memoCache.value.byLocation
    }

    const grouped = {}
    equipment.value.forEach(e => {
      const locKey = e.location?.site || 'Unassigned'
      if (!grouped[locKey]) grouped[locKey] = []
      grouped[locKey].push(e)
    })

    // Cache result
    memoCache.value.byLocation = grouped
    return grouped
  })

  // Cache utilities
  function isCacheValid(key) {
    const timestamp = cacheTimestamps.value[key]
    if (!timestamp) return false
    return Date.now() - timestamp < CACHE_TTL_MS
  }

  function invalidateCache(key = null) {
    if (key) {
      cacheTimestamps.value[key] = null
    } else {
      // Invalidate all caches
      Object.keys(cacheTimestamps.value).forEach(k => {
        cacheTimestamps.value[k] = null
      })
    }
  }

  // Actions
  async function fetchEquipment(options = {}) {
    const { forceRefresh = false, debounce = true } = options

    // Return cached data if valid and not forcing refresh
    if (!forceRefresh && isCacheValid('equipment') && equipment.value.length > 0) {
      return equipment.value
    }

    // Debounce rapid calls
    if (debounce && fetchDebounceTimer) {
      return equipment.value
    }

    if (debounce) {
      fetchDebounceTimer = setTimeout(() => {
        fetchDebounceTimer = null
      }, DEBOUNCE_MS)
    }

    loading.value = true
    error.value = null
    try {
      const response = await api.get('/inventory/equipment/')
      equipment.value = response.data
      cacheTimestamps.value.equipment = Date.now()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch equipment'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchManufacturers(forceRefresh = false) {
    if (!forceRefresh && isCacheValid('manufacturers') && manufacturers.value.length > 0) {
      return manufacturers.value
    }

    try {
      const response = await api.get('/inventory/manufacturers/')
      manufacturers.value = response.data
      cacheTimestamps.value.manufacturers = Date.now()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch manufacturers'
      throw err
    }
  }

  async function fetchModels(forceRefresh = false) {
    if (!forceRefresh && isCacheValid('models') && models.value.length > 0) {
      return models.value
    }

    try {
      const response = await api.get('/inventory/models/')
      models.value = response.data
      cacheTimestamps.value.models = Date.now()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch models'
      throw err
    }
  }

  async function fetchTypes(forceRefresh = false) {
    if (!forceRefresh && isCacheValid('types') && types.value.length > 0) {
      return types.value
    }

    try {
      const response = await api.get('/inventory/types/')
      types.value = response.data
      cacheTimestamps.value.types = Date.now()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch types'
      throw err
    }
  }

  async function fetchLocations(forceRefresh = false) {
    if (!forceRefresh && isCacheValid('locations') && locations.value.length > 0) {
      return locations.value
    }

    try {
      const response = await api.get('/inventory/locations/')
      locations.value = response.data
      cacheTimestamps.value.locations = Date.now()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch locations'
      throw err
    }
  }

  async function fetchSuppliers(forceRefresh = false) {
    if (!forceRefresh && isCacheValid('suppliers') && suppliers.value.length > 0) {
      return suppliers.value
    }

    try {
      const response = await api.get('/inventory/suppliers/')
      suppliers.value = response.data
      cacheTimestamps.value.suppliers = Date.now()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch suppliers'
      throw err
    }
  }

  // Fetch all reference data in parallel (efficient initialization)
  async function fetchReferenceData(forceRefresh = false) {
    await Promise.all([
      fetchManufacturers(forceRefresh),
      fetchModels(forceRefresh),
      fetchTypes(forceRefresh),
      fetchLocations(forceRefresh),
      fetchSuppliers(forceRefresh)
    ])
  }

  // CRUD operations with optimistic updates and cache invalidation

  async function createEquipment(equipmentData) {
    loading.value = true
    error.value = null
    try {
      const response = await api.post('/inventory/equipment/', equipmentData)
      // Add to local state immediately
      equipment.value.unshift(response.data)
      // Invalidate cache to ensure consistency on next fetch
      invalidateCache('equipment')
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create equipment'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateEquipment(id, equipmentData) {
    loading.value = true
    error.value = null

    // Optimistic update
    const index = equipment.value.findIndex(e => e.id === id)
    const originalItem = index !== -1 ? { ...equipment.value[index] } : null

    if (index !== -1) {
      equipment.value[index] = { ...equipment.value[index], ...equipmentData }
    }

    try {
      const response = await api.put(`/inventory/equipment/${id}`, equipmentData)
      // Update with server response
      if (index !== -1) {
        equipment.value[index] = response.data
      }
      invalidateCache('equipment')
      return response.data
    } catch (err) {
      // Rollback optimistic update on error
      if (originalItem && index !== -1) {
        equipment.value[index] = originalItem
      }
      error.value = err.response?.data?.detail || 'Failed to update equipment'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteEquipment(id) {
    loading.value = true
    error.value = null

    // Optimistic removal
    const index = equipment.value.findIndex(e => e.id === id)
    const removedItem = index !== -1 ? equipment.value.splice(index, 1)[0] : null

    try {
      await api.delete(`/inventory/equipment/${id}`)
      invalidateCache('equipment')
    } catch (err) {
      // Rollback on error
      if (removedItem) {
        equipment.value.splice(index, 0, removedItem)
      }
      error.value = err.response?.data?.detail || 'Failed to delete equipment'
      throw err
    } finally {
      loading.value = false
    }
  }

  // Utility to get equipment by ID from cache
  function getEquipmentById(id) {
    return equipment.value.find(e => e.id === id) || null
  }

  // Clear all state (e.g., on logout)
  function clearState() {
    equipment.value = []
    manufacturers.value = []
    models.value = []
    types.value = []
    locations.value = []
    suppliers.value = []
    invalidateCache()
    error.value = null
    // Clear memo cache
    memoCache.value = { byStatus: null, byLocation: null, equipmentVersion: 0 }
    // Clear debounce timer
    if (fetchDebounceTimer) {
      clearTimeout(fetchDebounceTimer)
      fetchDebounceTimer = null
    }
  }

  return {
    // State
    equipment,
    manufacturers,
    models,
    types,
    locations,
    suppliers,
    loading,
    error,

    // Getters
    activeEquipment,
    equipmentByStatus,
    equipmentByLocation,

    // Actions
    fetchEquipment,
    fetchManufacturers,
    fetchModels,
    fetchTypes,
    fetchLocations,
    fetchSuppliers,
    fetchReferenceData,
    createEquipment,
    updateEquipment,
    deleteEquipment,
    getEquipmentById,
    invalidateCache,
    clearState
  }
})
