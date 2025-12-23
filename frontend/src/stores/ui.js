/**
 * UI Store (Pinia)
 * Manages UI state: theme, language, sidebar, notifications.
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export const useUIStore = defineStore('ui', () => {
  // Theme State
  const isDark = ref(localStorage.getItem('theme') === 'dark')

  // Language State
  const currentLang = ref(localStorage.getItem('lang') || 'en')

  // Sidebar State
  const sidebarCollapsed = ref(localStorage.getItem('sidebarCollapsed') === 'true')

  // Loading State
  const globalLoading = ref(false)
  const loadingMessage = ref('')

  // Computed
  const themeClass = computed(() => isDark.value ? 'dark' : 'light')
  const langIcon = computed(() => currentLang.value === 'en' ? '🇫🇷' : '🇺🇸')

  /**
   * Toggle dark/light theme.
   */
  function toggleTheme() {
    isDark.value = !isDark.value
    updateThemeClass()
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  }

  /**
   * Set specific theme.
   */
  function setTheme(dark) {
    isDark.value = dark
    updateThemeClass()
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }

  /**
   * Update document theme class.
   */
  function updateThemeClass() {
    if (isDark.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  /**
   * Toggle language between EN and FR.
   */
  function toggleLang() {
    currentLang.value = currentLang.value === 'en' ? 'fr' : 'en'
    localStorage.setItem('lang', currentLang.value)
  }

  /**
   * Set specific language.
   */
  function setLang(lang) {
    if (lang === 'en' || lang === 'fr') {
      currentLang.value = lang
      localStorage.setItem('lang', lang)
    }
  }

  /**
   * Toggle sidebar collapsed state.
   */
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem('sidebarCollapsed', sidebarCollapsed.value)
  }

  /**
   * Set global loading state.
   */
  function setLoading(loading, message = '') {
    globalLoading.value = loading
    loadingMessage.value = message
  }

  /**
   * Initialize UI state from localStorage.
   */
  function init() {
    // Theme
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme === 'dark') {
      isDark.value = true
    } else if (savedTheme === 'light') {
      isDark.value = false
    } else {
      // Default to system preference
      isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    updateThemeClass()

    // Language
    const savedLang = localStorage.getItem('lang')
    if (savedLang) {
      currentLang.value = savedLang
    }

    // Sidebar
    const savedSidebar = localStorage.getItem('sidebarCollapsed')
    if (savedSidebar) {
      sidebarCollapsed.value = savedSidebar === 'true'
    }
  }

  // Watch for system theme changes
  if (typeof window !== 'undefined') {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem('theme')) {
        isDark.value = e.matches
        updateThemeClass()
      }
    })
  }

  return {
    // State
    isDark,
    currentLang,
    sidebarCollapsed,
    globalLoading,
    loadingMessage,

    // Computed
    themeClass,
    langIcon,

    // Actions
    toggleTheme,
    setTheme,
    toggleLang,
    setLang,
    toggleSidebar,
    setLoading,
    init
  }
})
