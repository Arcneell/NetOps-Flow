/**
 * Vue 3 Application Entry Point
 * Initializes Vue app with Pinia, Vue Router, PrimeVue, and i18n.
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import './style.css'

// PrimeVue
import PrimeVue from 'primevue/config'
import 'primevue/resources/themes/lara-dark-teal/theme.css'
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'
import ToastService from 'primevue/toastservice'
import Tooltip from 'primevue/tooltip'

// PrimeVue Components
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import Card from 'primevue/card'
import Textarea from 'primevue/textarea'
import FileUpload from 'primevue/fileupload'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import Calendar from 'primevue/calendar'
import Checkbox from 'primevue/checkbox'
import Password from 'primevue/password'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import ProgressBar from 'primevue/progressbar'
import Skeleton from 'primevue/skeleton'

// Stores
import { useAuthStore } from './stores/auth'
import { useUIStore } from './stores/ui'

// Create Vue app
const app = createApp(App)

// Create Pinia store
const pinia = createPinia()

// Use plugins
app.use(pinia)
app.use(router)
app.use(i18n)
app.use(PrimeVue, { ripple: true })
app.use(ToastService)

// Register directive
app.directive('tooltip', Tooltip)

// Register global components
app.component('Button', Button)
app.component('InputText', InputText)
app.component('InputNumber', InputNumber)
app.component('DataTable', DataTable)
app.component('Column', Column)
app.component('Dialog', Dialog)
app.component('Dropdown', Dropdown)
app.component('Card', Card)
app.component('Textarea', Textarea)
app.component('FileUpload', FileUpload)
app.component('Tag', Tag)
app.component('Toast', Toast)
app.component('Calendar', Calendar)
app.component('Checkbox', Checkbox)
app.component('Password', Password)
app.component('TabView', TabView)
app.component('TabPanel', TabPanel)
app.component('ProgressBar', ProgressBar)
app.component('Skeleton', Skeleton)

// Initialize stores
const authStore = useAuthStore()
const uiStore = useUIStore()
authStore.init()
uiStore.init()

// Mount app
app.mount('#app')

// Make toast service globally available for API interceptor
app.config.globalProperties.$toast = app.config.globalProperties.$toast
window.$toast = {
  add: (options) => {
    const toastEl = document.querySelector('.p-toast')
    if (toastEl && toastEl.__vueParentComponent) {
      const toast = toastEl.__vueParentComponent.ctx
      if (toast && toast.add) {
        toast.add(options)
      }
    }
  }
}
