/**
 * Vue 3 Application Entry Point
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import i18n, { initLang } from './i18n/index.js'
// style.css en non-bloquant : si 468 (proxy/WAF) ou autre échec, l'app reste utilisable
import('./style.css').catch(() => {})

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
import ContextMenu from 'primevue/contextmenu'

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

// Initialize theme before mount (prevents flash and ensures consistent state)
const initTheme = () => {
  const savedTheme = localStorage.getItem('theme')
  // Default to light theme for new users
  if (savedTheme === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}
initTheme()

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
app.component('ContextMenu', ContextMenu)

// Initialize language
initLang()

// Mount app
app.mount('#app')
