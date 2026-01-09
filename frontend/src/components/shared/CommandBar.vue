<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <Transition name="fade">
      <div
        v-if="visible"
        class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
        @click="close"
      ></div>
    </Transition>

    <!-- Command Dialog -->
    <Transition name="slide-up">
      <div
        v-if="visible"
        class="fixed top-1/4 left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 px-4"
      >
        <div class="command-bar-container rounded-xl shadow-2xl overflow-hidden">
          <!-- Search Input -->
          <div class="relative border-b" style="border-color: var(--border-color);">
            <i class="pi pi-search absolute left-4 top-1/2 -translate-y-1/2 text-lg" style="color: var(--text-muted);"></i>
            <input
              ref="searchInput"
              v-model="query"
              type="text"
              :placeholder="t('search.placeholder')"
              class="command-bar-input"
              @keydown="handleKeydown"
            />
            <div class="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
              <kbd class="command-bar-kbd">ESC</kbd>
            </div>
          </div>

          <!-- Results -->
          <div class="max-h-96 overflow-auto">
            <!-- Loading -->
            <div v-if="loading" class="p-4 text-center">
              <i class="pi pi-spinner pi-spin text-2xl"></i>
            </div>

            <!-- No Results -->
            <div v-else-if="query && !loading && results.length === 0" class="p-8 text-center">
              <i class="pi pi-search text-4xl mb-2 opacity-30"></i>
              <p class="text-sm opacity-60">{{ t('search.noResults') }}</p>
            </div>

            <!-- Results by Category -->
            <div v-else-if="results.length > 0">
              <div v-for="(group, category) in groupedResults" :key="category" class="mb-2">
                <!-- Category Header -->
                <div class="command-bar-category">
                  {{ getCategoryLabel(category) }}
                </div>

                <!-- Results -->
                <div
                  v-for="(result, index) in group"
                  :key="`${category}-${result.id}`"
                  :class="[
                    'command-bar-item',
                    selectedIndex === getAbsoluteIndex(category, index) ? 'selected' : ''
                  ]"
                  @click="navigateTo(result)"
                  @mouseenter="selectedIndex = getAbsoluteIndex(category, index)"
                >
                  <i :class="['pi', getResultIcon(result), 'text-lg']"></i>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium truncate">{{ result.title || result.name }}</div>
                    <div class="command-bar-subtitle">{{ getResultSubtitle(result) }}</div>
                  </div>
                  <i class="pi pi-arrow-right text-sm" style="color: var(--text-muted);"></i>
                </div>
              </div>
            </div>

            <!-- Quick Actions (when no query) -->
            <div v-else class="p-2">
              <div class="command-bar-category">
                {{ t('search.quickActions') }}
              </div>
              <div
                v-for="(action, index) in quickActions"
                :key="action.id"
                :class="[
                  'command-bar-item rounded-lg',
                  selectedIndex === index ? 'selected' : ''
                ]"
                @click="executeAction(action)"
                @mouseenter="selectedIndex = index"
              >
                <i :class="['pi', action.icon, 'text-lg']"></i>
                <span class="font-medium">{{ action.label }}</span>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="command-bar-footer">
            <span><kbd class="command-bar-kbd">&uarr;&darr;</kbd> {{ t('search.navigate') }}</span>
            <span><kbd class="command-bar-kbd">Enter</kbd> {{ t('search.open') }}</span>
            <span><kbd class="command-bar-kbd">Esc</kbd> {{ t('search.close') }}</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/auth'
import api from '../../api'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()

// State
const searchInput = ref(null)
const query = ref('')
const results = ref([])
const loading = ref(false)
const selectedIndex = ref(0)

// Computed
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Define all possible quick actions with their permission requirements
const allQuickActions = [
  { id: 'new-ticket', icon: 'pi-ticket', label: () => t('search.createTicket'), route: '/tickets', action: 'create', permission: null }, // All users can create tickets
  { id: 'new-equipment', icon: 'pi-box', label: () => t('search.createEquipment'), route: '/inventory', action: 'create', permission: 'inventory' },
  { id: 'dashboard', icon: 'pi-chart-bar', label: () => t('nav.dashboard'), route: '/', permission: null },
  { id: 'tickets', icon: 'pi-ticket', label: () => t('nav.tickets'), route: '/tickets', permission: null },
  { id: 'inventory', icon: 'pi-box', label: () => t('nav.inventory'), route: '/inventory', permission: 'inventory' },
  { id: 'contracts', icon: 'pi-file', label: () => t('nav.contracts'), route: '/contracts', permission: 'contracts' },
  { id: 'ipam', icon: 'pi-sitemap', label: () => t('nav.ipam'), route: '/ipam', permission: 'ipam' },
  { id: 'dcim', icon: 'pi-server', label: () => t('nav.dcim'), route: '/dcim', permission: 'dcim' },
  { id: 'software', icon: 'pi-desktop', label: () => t('nav.software'), route: '/software', permission: 'software' },
  { id: 'knowledge', icon: 'pi-book', label: () => t('nav.knowledge'), route: '/knowledge', permission: 'knowledge' }
]

// Filter quick actions based on user permissions
const quickActions = computed(() => {
  return allQuickActions
    .filter(action => {
      // No permission required = everyone can access
      if (!action.permission) return true
      // Check if user has the required permission
      return authStore.hasPermission(action.permission)
    })
    .map(action => ({
      ...action,
      label: action.label() // Resolve the label function
    }))
})

const groupedResults = computed(() => {
  const groups = {}
  for (const result of results.value) {
    const type = result.type || 'other'
    if (!groups[type]) {
      groups[type] = []
    }
    groups[type].push(result)
  }
  return groups
})

// Methods
const close = () => {
  visible.value = false
  query.value = ''
  results.value = []
  selectedIndex.value = 0
}

const getCategoryLabel = (category) => {
  const labels = {
    equipment: t('inventory.equipment'),
    ticket: t('tickets.title'),
    contract: t('contracts.title'),
    article: t('knowledge.title'),
    software: t('software.title'),
    subnet: t('ipam.subnets'),
    other: t('common.other')
  }
  return labels[category] || category
}

const getResultIcon = (result) => {
  const icons = {
    equipment: 'pi-box',
    ticket: 'pi-ticket',
    contract: 'pi-file',
    article: 'pi-book',
    software: 'pi-desktop',
    subnet: 'pi-sitemap'
  }
  return icons[result.type] || 'pi-search'
}

const getResultSubtitle = (result) => {
  // Use subtitle from backend if available, otherwise fallback to type-specific fields
  if (result.subtitle) {
    return result.subtitle
  }
  switch (result.type) {
    case 'equipment':
      return result.description || ''
    case 'ticket':
      return result.status || ''
    case 'contract':
      return result.description || ''
    case 'article':
      return result.category || ''
    case 'software':
      return result.description || ''
    case 'subnet':
      return result.description || ''
    default:
      return ''
  }
}

const getAbsoluteIndex = (category, indexInCategory) => {
  const categories = Object.keys(groupedResults.value)
  let absoluteIndex = 0
  for (const cat of categories) {
    if (cat === category) {
      return absoluteIndex + indexInCategory
    }
    absoluteIndex += groupedResults.value[cat].length
  }
  return absoluteIndex + indexInCategory
}

const getResultByIndex = (index) => {
  let currentIndex = 0
  for (const category of Object.keys(groupedResults.value)) {
    for (const result of groupedResults.value[category]) {
      if (currentIndex === index) {
        return result
      }
      currentIndex++
    }
  }
  return null
}

const totalResults = computed(() => {
  return results.value.length
})

const navigateTo = (result) => {
  const routes = {
    equipment: `/inventory?equipment=${result.id}`,
    ticket: `/tickets?id=${result.id}`,
    contract: `/contracts?id=${result.id}`,
    article: `/knowledge?article=${result.id}`,
    software: `/software?id=${result.id}`,
    subnet: `/ipam?subnet=${result.id}`
  }
  const route = routes[result.type]
  if (route) {
    router.push(route)
    close()
  }
}

const executeAction = (action) => {
  if (action.route) {
    // If action has 'create' action, append query param to trigger dialog
    if (action.action === 'create') {
      router.push({ path: action.route, query: { action: 'create' } })
    } else {
      router.push(action.route)
    }
  }
  close()
}

const handleKeydown = (event) => {
  const maxIndex = query.value ? totalResults.value - 1 : quickActions.value.length - 1

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, maxIndex)
      break
    case 'ArrowUp':
      event.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
      break
    case 'Enter':
      event.preventDefault()
      if (query.value && results.value.length > 0) {
        const result = getResultByIndex(selectedIndex.value)
        if (result) navigateTo(result)
      } else if (!query.value && quickActions.value[selectedIndex.value]) {
        executeAction(quickActions.value[selectedIndex.value])
      }
      break
    case 'Escape':
      event.preventDefault()
      close()
      break
  }
}

// Map search result types to required permissions
const resultTypePermissions = {
  equipment: 'inventory',
  ticket: null, // All users can access tickets
  contract: 'contracts',
  article: 'knowledge',
  software: 'software',
  subnet: 'ipam'
}

// Filter search results based on user permissions
const filterResultsByPermission = (searchResults) => {
  return searchResults.filter(result => {
    const requiredPermission = resultTypePermissions[result.type]
    // No permission required = everyone can access
    if (!requiredPermission) return true
    // Check if user has the required permission
    return authStore.hasPermission(requiredPermission)
  })
}

// Search debounce and abort controller
let searchTimeout = null
let abortController = null
let currentSearchId = 0

const search = async () => {
  if (!query.value || query.value.length < 1) {
    results.value = []
    return
  }

  // Cancel any pending request
  if (abortController) {
    abortController.abort()
  }

  // Create new abort controller for this request
  abortController = new AbortController()
  const searchId = ++currentSearchId

  loading.value = true
  try {
    const response = await api.get('/search/', {
      params: { q: query.value, limit: 30 },
      signal: abortController.signal
    })

    // Ignore results if a newer search has started
    if (searchId !== currentSearchId) {
      return
    }

    const rawResults = response.data.results || response.data || []
    // Filter results based on user permissions
    results.value = filterResultsByPermission(rawResults)
    selectedIndex.value = 0
  } catch (error) {
    // Ignore abort errors
    if (error.name === 'AbortError' || error.name === 'CanceledError') {
      return
    }
    console.error('Search error:', error)
    results.value = []
  } finally {
    // Only clear loading if this is still the current search
    if (searchId === currentSearchId) {
      loading.value = false
    }
  }
}

watch(query, () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(search, 300)
})

watch(visible, (isVisible) => {
  if (isVisible) {
    nextTick(() => {
      searchInput.value?.focus()
    })
  } else {
    query.value = ''
    results.value = []
    selectedIndex.value = 0
  }
})

// Global keyboard shortcut (Cmd+K / Ctrl+K)
const handleGlobalKeydown = (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
    event.preventDefault()
    visible.value = !visible.value
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeydown)
  if (searchTimeout) clearTimeout(searchTimeout)
  // Cancel any pending search request
  if (abortController) {
    abortController.abort()
  }
})
</script>

<style scoped>
.command-bar-container {
  background-color: var(--bg-card-solid);
  border: 1px solid var(--border-default);
}

.command-bar-input {
  width: 100%;
  padding: 1rem 1rem 1rem 3rem;
  background: transparent;
  font-size: 1.125rem;
  color: var(--text-primary);
  border: none;
  outline: none;
}

.command-bar-input::placeholder {
  color: var(--text-muted);
}

.command-bar-category {
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-muted);
  position: sticky;
  top: 0;
  background-color: var(--bg-card-solid);
}

.command-bar-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: all var(--transition-fast);
  color: var(--text-primary);
}

.command-bar-item:hover {
  background-color: var(--bg-hover);
}

.command-bar-item.selected {
  background-color: var(--primary);
  color: white;
}

.command-bar-item.selected .command-bar-subtitle {
  color: rgba(255, 255, 255, 0.7);
}

.command-bar-item.selected i {
  color: white !important;
}

.command-bar-subtitle {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.command-bar-footer {
  padding: 0.5rem 1rem;
  border-top: 1px solid var(--border-default);
  font-size: 0.75rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 1rem;
  background-color: var(--bg-secondary);
}

.command-bar-kbd {
  display: inline-block;
  padding: 0.125rem 0.375rem;
  font-size: 0.75rem;
  font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  margin-right: 0.25rem;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translate(-50%, -10px);
}
</style>
