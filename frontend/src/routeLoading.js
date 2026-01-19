/**
 * État de chargement des changements de route.
 * Utilisé pour afficher un overlay pendant le chargement des pages (chunks lazy, etc.).
 * Délai de 120 ms avant d'afficher l'overlay pour éviter un flash sur les navigations rapides.
 */
import { ref } from 'vue'

export const isRouteLoading = ref(false)
const DELAY_MS = 120
let _timeoutId = null

export function startRouteLoading() {
  if (_timeoutId) {
    clearTimeout(_timeoutId)
    _timeoutId = null
  }
  _timeoutId = setTimeout(() => {
    isRouteLoading.value = true
    _timeoutId = null
  }, DELAY_MS)
}

export function endRouteLoading() {
  if (_timeoutId) {
    clearTimeout(_timeoutId)
    _timeoutId = null
  }
  isRouteLoading.value = false
}
