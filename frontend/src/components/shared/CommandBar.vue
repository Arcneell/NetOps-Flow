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
            <i class="pi pi-search absolute left-4 top-1/2 -translate-y-1/2 text-lg opacity-50"></i>
            <input
              ref="searchInput"
              v-model="query"
              type="text"
              :placeholder="t('search.placeholder')"
              class="w-full py-4 pl-12 pr-4 bg-transparent text-lg focus:outline-none"
              @keydown="handleKeydown"
            />
            <div class="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
              <kbd class="px-2 py-1 text-xs rounded bg-gray-200 dark:bg-gray-700">ESC</kbd>
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
                <div class="px-4 py-2 text-xs font-semibold uppercase opacity-50 sticky top-0" style="background-color: var(--bg-card);">
                  {{ getCategoryLabel(category) }}
                </div>

                <!-- Results -->
                <div
                  v-for="(result, index) in group"
                  :key="`${category}-${result.id}`"
                  :class="[
                    'flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors',
                    selectedIndex === getAbsoluteIndex(category, index) ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                  ]"
                  @click="navigateTo(result)"
                  @mouseenter="selectedIndex = getAbsoluteIndex(category, index)"
                >
                  <i :class="['pi', getResultIcon(result), 'text-lg']"></i>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium truncate">{{ result.title || result.name }}</div>
                    <div class="text-sm opacity-60 truncate">{{ getResultSubtitle(result) }}</div>
                  </div>
                  <i class="pi pi-arrow-right text-sm opacity-50"></i>
                </div>
              </div>
            </div>

            <!-- Quick Actions (when no query) -->
            <div v-else class="p-2">
              <div class="px-4 py-2 text-xs font-semibold uppercase opacity-50">
                {{ t('search.quickActions') }}
              </div>
              <div
                v-for="(action, index) in quickActions"
                :key="action.id"
                :class="[
                  'flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors rounded-lg',
                  selectedIndex === index ? 'bg-blue-500 text-white' : 'hover:bg-gray-100 dark:hover:bg-gray-800'
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
          <div class="px-4 py-2 border-t text-xs opacity-50 flex items-center gap-4" style="border-color: var(--border-color); background-color: var(--bg-app);">
            <span><kbd class="px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 mr-1">&uarr;&darr;</kbd> {{ t('search.navigate') }}</span>
            <span><kbd class="px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 mr-1">Enter</kbd> {{ t('search.open') }}</span>
            <span><kbd class="px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 mr-1">Esc</kbd> {{ t('search.close') }}</span>
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
import api from '../../api'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const router = useRouter()
const { t } = useI18n()

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

const quickActions = computed(() => [
  { id: 'new-ticket', icon: 'pi-ticket', label: t('search.createTicket'), route: '/tickets', action: 'create-ticket' },
  { id: 'new-equipment', icon: 'pi-box', label: t('search.createEquipment'), route: '/inventory', action: 'create-equipment' },
  { id: 'dashboard', icon: 'pi-chart-bar', label: t('nav.dashboard'), route: '/' },
  { id: 'tickets', icon: 'pi-ticket', label: t('nav.tickets'), route: '/tickets' },
  { id: 'inventory', icon: 'pi-box', label: t('nav.inventory'), route: '/inventory' },
  { id: 'contracts', icon: 'pi-file', label: t('nav.contracts'), route: '/contracts' }
])

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
  switch (result.type) {
    case 'equipment':
      return result.serial_number || result.asset_tag || ''
    case 'ticket':
      return result.ticket_number || ''
    case 'contract':
      return result.contract_number || result.contract_type || ''
    case 'article':
      return result.category || ''
    case 'software':
      return result.publisher || ''
    case 'subnet':
      return result.cidr || ''
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
    router.push(action.route)
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

// Search debounce
let searchTimeout = null
const search = async () => {
  if (!query.value || query.value.length < 2) {
    results.value = []
    return
  }

  loading.value = true
  try {
    const response = await api.get('/search/', {
      params: { q: query.value, limit: 20 }
    })
    results.value = response.data.results || response.data || []
    selectedIndex.value = 0
  } catch (error) {
    console.error('Search error:', error)
    results.value = []
  } finally {
    loading.value = false
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
})
</script>

<style scoped>
.command-bar-container {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
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

kbd {
  font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
}
</style>
