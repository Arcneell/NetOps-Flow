/**
 * Vue I18n Configuration
 * Standard internationalization using vue-i18n library.
 */
import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import fr from './locales/fr.json'

const messages = {
  en,
  fr
}

// Get saved language or default to English
const savedLang = localStorage.getItem('lang') || 'en'

const i18n = createI18n({
  legacy: false, // Use Composition API mode
  locale: savedLang,
  fallbackLocale: 'en',
  messages,
  globalInjection: true,
  silentTranslationWarn: true,
  silentFallbackWarn: true
})

/**
 * Set the current locale.
 */
export function setLocale(locale) {
  if (locale === 'en' || locale === 'fr') {
    i18n.global.locale.value = locale
    localStorage.setItem('lang', locale)
    document.documentElement.setAttribute('lang', locale)
  }
}

/**
 * Toggle between EN and FR.
 */
export function toggleLocale() {
  const newLocale = i18n.global.locale.value === 'en' ? 'fr' : 'en'
  setLocale(newLocale)
  return newLocale
}

/**
 * Get current locale.
 */
export function getLocale() {
  return i18n.global.locale.value
}

export default i18n
