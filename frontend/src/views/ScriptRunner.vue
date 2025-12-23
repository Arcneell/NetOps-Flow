<template>
  <div>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      
      <!-- Upload & List -->
      <div class="lg:col-span-1 flex flex-col gap-6">
        <div class="card">
          <h2 class="text-lg font-bold mb-4 flex items-center gap-2">
            <i class="pi pi-cloud-upload"></i> {{ t('uploadTitle').value }}
          </h2>
          <div class="flex flex-col gap-4">
            <div>
               <label class="text-sm font-bold block mb-1">{{ t('name').value }} <span class="text-red-500">*</span></label>
               <InputText v-model="uploadForm.name" :placeholder="t('name').value" class="w-full" />
            </div>
            
            <div class="flex flex-col gap-1">
               <label class="text-sm font-bold block mb-1">{{ t('description').value }}</label>
               <InputText v-model="uploadForm.description" :placeholder="t('description').value" class="w-full" />
            </div>

            <div>
               <label class="text-sm font-bold block mb-1">{{ t('type').value }} <span class="text-red-500">*</span></label>
               <Dropdown v-model="uploadForm.type" :options="['python', 'bash', 'powershell']" :placeholder="t('type').value" class="w-full" />
            </div>
            
            <div class="relative group cursor-pointer border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-6 hover:border-blue-500 transition-colors bg-opacity-50" @click="$refs.fileInput.click()">
               <input type="file" ref="fileInput" @change="onFileSelected" class="hidden" accept=".py,.sh,.ps1" />
               <div class="text-center" v-if="!selectedFile">
                  <i class="pi pi-file text-2xl mb-2 opacity-50"></i>
                  <p class="text-sm opacity-70">{{ t('clickDrag').value }}</p>
               </div>
               <div v-else class="text-center">
                  <i :class="`pi ${getFileIcon} text-green-500 text-3xl mb-2`"></i>
                  <p class="font-bold text-sm truncate px-2">{{ selectedFile.name }}</p>
                  <p class="text-xs opacity-70">{{ (selectedFile.size / 1024).toFixed(2) }} KB</p>
               </div>
            </div>

            <Button :label="t('uploadScript').value" icon="pi pi-upload" @click="uploadScript" :loading="uploading" class="w-full" />
          </div>
        </div>

        <div class="card">
          <h2 class="text-lg font-bold mb-4">{{ t('availableScripts').value }}</h2>
          <div v-if="scripts.length === 0" class="text-sm italic opacity-50">No scripts found.</div>
          <div v-else class="flex flex-col gap-2 max-h-[400px] overflow-y-auto pr-2">
            <div v-for="script in scripts" :key="script.id" class="p-3 border rounded-lg flex flex-col gap-3 transition-colors shadow-sm" style="border-color: var(--border-color);">
              <div class="flex justify-between items-start">
                  <div>
                    <div class="font-bold text-sm">{{ script.name }}</div>
                    <div class="text-xs mt-1 flex gap-2 opacity-70">
                        <span class="px-1.5 rounded uppercase font-mono text-[10px]" style="background-color: rgba(0,0,0,0.1);">{{ script.script_type }}</span>
                    </div>
                  </div>
                  <div class="flex gap-2">
                    <Button icon="pi pi-trash" rounded size="small" severity="danger" text @click="confirmDelete(script)" />
                    <Button icon="pi pi-play" rounded size="small" class="p-button-success" @click="confirmRun(script)" />
                  </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Execution History -->
      <div class="lg:col-span-2">
         <div class="card h-full min-h-[500px] flex flex-col">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-lg font-bold">{{ t('executionHistory').value }}</h2>
                <div class="flex gap-2">
                    <Button icon="pi pi-trash" rounded text severity="danger" v-tooltip.top="t('deleteHistory').value" @click="showClearHistoryDialog = true" />
                    <Button icon="pi pi-refresh" text rounded @click="fetchExecutions" />
                </div>
            </div>
            
            <DataTable :value="executions" paginator :rows="8" dataKey="id" class="p-datatable-sm text-sm" stripedRows>
                <Column field="id" header="#" style="width: 3rem" class="opacity-50"></Column>
                <Column :header="t('targetServer').value">
                     <template #body="slotProps">
                         <span v-if="slotProps.data.server_id" class="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">Remote</span>
                         <span v-else class="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">Local</span>
                     </template>
                </Column>
                <Column field="status" :header="t('status').value">
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.status" :severity="getStatusSeverity(slotProps.data.status)" />
                    </template>
                </Column>
                <Column field="started_at" :header="t('lastScan').value" class="opacity-70">
                    <template #body="slotProps">
                        {{ new Date(slotProps.data.started_at).toLocaleTimeString() }}
                    </template>
                </Column>
                <Column :header="t('actions').value" style="width: 8rem">
                    <template #body="slotProps">
                        <div class="flex gap-1">
                             <Button icon="pi pi-eye" text rounded class="p-button-secondary" @click="showOutput(slotProps.data)" />
                             <Button v-if="['running', 'pending'].includes(slotProps.data.status)" icon="pi pi-stop-circle" text rounded severity="danger" @click="stopExecution(slotProps.data)" v-tooltip.top="t('stop').value" />
                        </div>
                    </template>
                </Column>
            </DataTable>
         </div>
      </div>
    </div>

    <!-- Run Script Dialog -->
    <Dialog v-model:visible="showRunDialog" modal :header="t('runNow').value" :style="{ width: '450px' }">
        <div class="flex flex-col gap-4 mt-2" v-if="selectedScript">
            <p class="font-bold text-lg text-blue-500">{{ selectedScript.name }}</p>
            
            <div class="flex flex-col gap-2">
                <label class="text-sm font-bold">{{ t('targetServer').value }}</label>
                <Dropdown v-model="selectedServerId" :options="serverOptions" optionLabel="name" optionValue="id" :placeholder="t('localhost').value" class="w-full" showClear />
                <small class="opacity-50">{{ t('leaveEmpty').value }}</small>
            </div>

            <div class="flex flex-col gap-2">
                <label class="text-sm font-bold">{{ t('scriptArgs').value }}</label>
                <InputText v-model="scriptArgs" :placeholder="t('scriptArgsPlaceholder').value" class="w-full font-mono text-sm" />
            </div>

            <div class="flex flex-col gap-2 border-t pt-4 border-dashed" style="border-color: var(--border-color);">
                <label class="text-sm font-bold text-red-500">{{ t('enterPasswordConfirm').value }} <span class="text-red-500">*</span></label>
                <InputText v-model="confirmPassword" type="password" class="w-full" placeholder="••••••••" />
            </div>
        </div>
        <template #footer>
            <div class="flex justify-end gap-3">
                <Button :label="t('cancel').value" severity="secondary" outlined @click="showRunDialog = false" />
                <Button :label="t('runNow').value" icon="pi pi-play" @click="runScript" severity="danger" />
            </div>
        </template>
    </Dialog>

    <!-- Delete Script Confirmation Dialog -->
    <Dialog v-model:visible="showDeleteDialog" modal :header="t('confirmDelete').value" :style="{ width: '350px' }">
        <div class="flex items-center gap-3">
            <i class="pi pi-exclamation-triangle text-red-500 text-2xl"></i>
            <span>{{ t('confirmDeleteScript').value }} <b>{{ scriptToDelete?.name }}</b>?</span>
        </div>
        <template #footer>
            <div class="flex justify-end gap-3">
                <Button :label="t('cancel').value" severity="secondary" outlined @click="showDeleteDialog = false" />
                <Button :label="t('delete').value" icon="pi pi-trash" @click="deleteScript" severity="danger" />
            </div>
        </template>
    </Dialog>

    <!-- Clear History Confirmation Dialog -->
    <Dialog v-model:visible="showClearHistoryDialog" modal :header="t('confirmDelete').value" :style="{ width: '350px' }">
        <div class="flex items-center gap-3">
            <i class="pi pi-exclamation-triangle text-red-500 text-2xl"></i>
            <span>{{ t('confirmDeleteHistory').value }}</span>
        </div>
        <template #footer>
            <div class="flex justify-end gap-3">
                <Button :label="t('cancel').value" severity="secondary" outlined @click="showClearHistoryDialog = false" />
                <Button :label="t('delete').value" icon="pi pi-trash" @click="clearHistory" severity="danger" />
            </div>
        </template>
    </Dialog>

    <!-- Access Denied Dialog -->
    <Dialog v-model:visible="showAccessDeniedDialog" modal :header="t('accessDeniedTitle').value" :style="{ width: '350px' }">
        <div class="flex flex-col items-center gap-3 text-center p-4">
            <div class="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mb-2">
                <i class="pi pi-lock text-red-500 text-3xl"></i>
            </div>
            <h3 class="font-bold text-lg text-gray-800 dark:text-white">{{ t('invalidPassword').value }}</h3>
            <p class="text-gray-600 dark:text-gray-400 text-sm">{{ t('invalidPasswordDetail').value }}</p>
        </div>
        <template #footer>
            <Button label="OK" @click="showAccessDeniedDialog = false" class="w-full" />
        </template>
    </Dialog>

    <!-- Output Dialog -->
    <Dialog v-model:visible="showOutputDialog" modal :header="t('executionLog').value" :style="{ width: '60vw' }">
      <div v-if="selectedExecution" class="terminal-output">
        <div v-if="selectedExecution.stdout" class="mb-4">
            <div class="text-gray-500 text-xs mb-1 uppercase tracking-wider">{{ t('stdout').value }}</div>
            <pre class="whitespace-pre-wrap">{{ selectedExecution.stdout }}</pre>
        </div>
        <div v-if="selectedExecution.stderr" class="mb-4">
            <div class="text-red-500 text-xs mb-1 uppercase tracking-wider">{{ t('stderr').value }}</div>
            <pre class="text-red-400 whitespace-pre-wrap">{{ selectedExecution.stderr }}</pre>
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '../api';
import { t } from '../i18n';

const toast = useToast();
const scripts = ref([]);
const executions = ref([]);
const servers = ref([]);
const uploading = ref(false);
const fileInput = ref(null);
const selectedFile = ref(null);
const showOutputDialog = ref(false);
const showRunDialog = ref(false);
const showDeleteDialog = ref(false);
const showClearHistoryDialog = ref(false);
const showAccessDeniedDialog = ref(false);
const selectedExecution = ref(null);
const selectedScript = ref(null);
const scriptToDelete = ref(null);
const selectedServerId = ref(null);
const scriptArgs = ref('');
const confirmPassword = ref('');
let refreshInterval = null;

const uploadForm = ref({
    name: '',
    description: '',
    type: 'python'
});

const serverOptions = computed(() => {
    return servers.value.map(s => ({ name: `${s.name} (${s.ip_address})`, id: s.id }));
});

const onFileSelected = (event) => {
    const file = event.target.files[0];
    if (file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['py', 'sh', 'ps1'].includes(ext)) {
            toast.add({ severity: 'error', summary: t('error').value, detail: t('invalidFileType').value });
            event.target.value = null;
            selectedFile.value = null;
            return;
        }
        selectedFile.value = file;
        
        // Auto-detect type
        if (ext === 'py') uploadForm.value.type = 'python';
        if (ext === 'sh') uploadForm.value.type = 'bash';
        if (ext === 'ps1') uploadForm.value.type = 'powershell';
    }
};

const getFileIcon = computed(() => {
    if (!selectedFile.value) return 'pi-file';
    const ext = selectedFile.value.name.split('.').pop().toLowerCase();
    if (ext === 'py') return 'pi-box'; // Python-ish
    if (ext === 'sh') return 'pi-cog'; // Shell
    if (ext === 'ps1') return 'pi-microsoft'; // PowerShell
    return 'pi-file';
});

const loadData = async () => {
    try {
        const [scRes, exRes, svRes] = await Promise.all([
            api.get('/scripts/'),
            api.get('/executions/'),
            api.get('/servers/')
        ]);
        scripts.value = scRes.data;
        executions.value = exRes.data;
        servers.value = svRes.data;
    } catch (e) { console.error(e); }
};

const fetchExecutions = async () => {
    try {
        const res = await api.get('/executions/');
        executions.value = res.data;
    } catch (e) { console.error(e); }
};

const uploadScript = async () => {
    if (!selectedFile.value || !uploadForm.value.name || !uploadForm.value.type) {
        toast.add({ severity: 'warn', summary: t('error').value, detail: 'Please fill all mandatory fields' });
        return;
    }
    uploading.value = true;
    const formData = new FormData();
    formData.append('name', uploadForm.value.name);
    formData.append('description', uploadForm.value.description);
    formData.append('script_type', uploadForm.value.type);
    formData.append('file', selectedFile.value);

    try {
        await api.post('/scripts/', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
        toast.add({ severity: 'success', summary: t('uploaded').value });
        uploadForm.value = { name: '', description: '', type: 'python' };
        selectedFile.value = null;
        fileInput.value.value = null; 
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: t('error').value });
    } finally {
        uploading.value = false;
    }
};

const confirmRun = (script) => {
    selectedScript.value = script;
    selectedServerId.value = null;
    scriptArgs.value = '';
    confirmPassword.value = '';
    showRunDialog.value = true;
};

const runScript = async () => {
    if (!selectedScript.value || !confirmPassword.value) {
        toast.add({ severity: 'warn', summary: t('passwordRequired').value, detail: t('confirmPasswordDetail').value });
        return;
    }

    // Parse script arguments safely
    let argsArray = [];
    if (scriptArgs.value && scriptArgs.value.trim()) {
        const matches = scriptArgs.value.match(/(?:[^\s"]+|"[^"]*")+/g);
        if (matches) {
            argsArray = matches.map(s => s.replace(/^"|"$/g, ''));
        }
    }

    try {
        await api.post(`/scripts/${selectedScript.value.id}/run`, {
            server_id: selectedServerId.value,
            password: confirmPassword.value,
            script_args: argsArray
        });
        
        toast.add({ severity: 'info', summary: t('started').value, detail: t('scriptQueued').value });
        showRunDialog.value = false;
        fetchExecutions();
    } catch (e) {
        if (e.response && e.response.status === 403) {
             showAccessDeniedDialog.value = true;
        } else {
             const msg = e.response?.data?.detail || t('executionFailed').value;
             toast.add({ severity: 'error', summary: t('error').value, detail: msg });
        }
    }
};

const stopExecution = async (execution) => {
    try {
        await api.post(`/executions/${execution.id}/stop`);
        toast.add({ severity: 'info', summary: t('executionStopped').value });
        fetchExecutions();
    } catch (e) {
        toast.add({ severity: 'error', summary: t('error').value, detail: 'Failed to stop' });
    }
};

const clearHistory = async () => {
    try {
        await api.delete('/executions/');
        toast.add({ severity: 'success', summary: t('historyDeleted').value });
        showClearHistoryDialog.value = false;
        fetchExecutions();
    } catch (e) {
         toast.add({ severity: 'error', summary: t('error').value });
    }
};

const confirmDelete = (script) => {
    scriptToDelete.value = script;
    showDeleteDialog.value = true;
};

const deleteScript = async () => {
    if (!scriptToDelete.value) return;
    try {
        await api.delete(`/scripts/${scriptToDelete.value.id}`);
        toast.add({ severity: 'success', summary: t('deleted').value, detail: t('scriptDeleted').value });
        showDeleteDialog.value = false;
        loadData();
    } catch (e) {
        const msg = e.response?.data?.detail || t('error').value;
        toast.add({ severity: 'error', summary: t('error').value, detail: msg });
    }
};

const showOutput = (execution) => {
    selectedExecution.value = execution;
    showOutputDialog.value = true;
};

const getStatusSeverity = (status) => {
    switch (status) {
        case 'success': return 'success';
        case 'failure': return 'danger';
        case 'cancelled': return 'warning';
        case 'running': return 'info';
        default: return 'warning';
    }
};

onMounted(() => {
    loadData();
    refreshInterval = setInterval(fetchExecutions, 5000);
});

onUnmounted(() => {
    if (refreshInterval) clearInterval(refreshInterval);
});
</script>