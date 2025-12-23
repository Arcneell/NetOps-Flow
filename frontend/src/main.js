import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

import PrimeVue from 'primevue/config'
// Changement pour un thème sombre de base
import 'primevue/resources/themes/lara-dark-teal/theme.css' 
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'

// PrimeVue Components
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Dialog from 'primevue/dialog';
import Dropdown from 'primevue/dropdown';
import Card from 'primevue/card';
import Textarea from 'primevue/textarea';
import FileUpload from 'primevue/fileupload';
import Tag from 'primevue/tag';
import Toast from 'primevue/toast';
import ToastService from 'primevue/toastservice';
import Calendar from 'primevue/calendar';

const app = createApp(App)

app.use(router)
app.use(PrimeVue, { ripple: true }) // Enable ripple effect for iOS feel
app.use(ToastService)

app.component('Button', Button)
app.component('InputText', InputText)
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

app.mount('#app')