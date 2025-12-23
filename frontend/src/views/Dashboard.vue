<template>
  <div>
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        <div class="card flex items-center p-4 border-l-4 border-blue-500">
            <div class="p-3 rounded-full bg-blue-50 text-blue-600 mr-4">
                <i class="pi pi-sitemap text-xl"></i>
            </div>
            <div>
                <span class="block text-sm font-medium opacity-70">{{ t('totalSubnets') }}</span>
                <span class="block text-2xl font-bold">{{ stats.subnets }}</span>
            </div>
        </div>

        <div class="card flex items-center p-4 border-l-4 border-green-500">
            <div class="p-3 rounded-full bg-green-50 text-green-600 mr-4">
                <i class="pi pi-desktop text-xl"></i>
            </div>
            <div>
                <span class="block text-sm font-medium opacity-70">{{ t('activeIps') }}</span>
                <span class="block text-2xl font-bold">{{ stats.ips }}</span>
            </div>
        </div>

        <div class="card flex items-center p-4 border-l-4 border-purple-500">
            <div class="p-3 rounded-full bg-purple-50 text-purple-600 mr-4">
                <i class="pi pi-file text-xl"></i>
            </div>
            <div>
                <span class="block text-sm font-medium opacity-70">{{ t('scripts') }}</span>
                <span class="block text-2xl font-bold">{{ stats.scripts }}</span>
            </div>
        </div>

        <div class="card flex items-center p-4 border-l-4 border-orange-500">
            <div class="p-3 rounded-full bg-orange-50 text-orange-600 mr-4">
                <i class="pi pi-cog text-xl"></i>
            </div>
            <div>
                <span class="block text-sm font-medium opacity-70">{{ t('executions') }}</span>
                <span class="block text-2xl font-bold">{{ stats.executions }}</span>
            </div>
        </div>

        <div class="card flex items-center p-4 border-l-4 border-cyan-500">
            <div class="p-3 rounded-full bg-cyan-50 text-cyan-600 mr-4">
                <i class="pi pi-box text-xl"></i>
            </div>
            <div>
                <span class="block text-sm font-medium opacity-70">{{ t('totalEquipment') }}</span>
                <span class="block text-2xl font-bold">{{ stats.equipment }}</span>
            </div>
        </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="card">
            <h3 class="text-lg font-bold mb-4">{{ t('quickActions') }}</h3>
            <div class="flex flex-wrap gap-4">
                <router-link to="/ipam">
                    <Button :label="t('newSubnet')" icon="pi pi-plus" class="p-button-outlined" />
                </router-link>
                <router-link to="/scripts">
                    <Button :label="t('uploadScript')" icon="pi pi-upload" severity="secondary" class="p-button-outlined" />
                </router-link>
            </div>
        </div>
        
        <div class="card">
            <h3 class="text-lg font-bold mb-4">{{ t('systemStatus') }}</h3>
            <div class="flex items-center gap-2 text-sm mb-2">
                <i class="pi pi-check-circle text-green-500"></i>
                <span>{{ t('dbConnected') }}</span>
            </div>
            <div class="flex items-center gap-2 text-sm">
                <i class="pi pi-check-circle text-green-500"></i>
                <span>{{ t('workerActive') }}</span>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api';
import { t } from '../i18n';

const stats = ref({ subnets: 0, ips: 0, scripts: 0, executions: 0, equipment: 0 });

onMounted(async () => {
  try {
    const res = await api.get('/dashboard/stats');
    stats.value = res.data;
  } catch (e) {
    console.error("Failed to fetch stats", e);
  }
});
</script>
