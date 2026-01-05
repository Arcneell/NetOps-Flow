<template>
  <div class="flex flex-col h-full gap-4">
    <!-- Header with controls -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <!-- View Mode Selector -->
        <SelectButton v-model="viewMode" :options="viewModes" optionLabel="label" optionValue="value"
          :allowEmpty="false" class="view-mode-selector" />

        <!-- Search -->
        <div class="relative">
          <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
          <InputText v-model="searchQuery" :placeholder="t('topology.search')"
            class="pl-10 w-64" @input="handleSearch" />
        </div>
      </div>

      <div class="flex items-center gap-2">
        <!-- Filter by type -->
        <Dropdown v-model="filterType" :options="filterTypes" optionLabel="label" optionValue="value"
          :placeholder="t('topology.filterByType')" showClear class="w-48" />

        <!-- Zoom controls -->
        <div class="flex items-center gap-1 px-2 py-1 rounded-lg" style="background: var(--bg-secondary);">
          <Button icon="pi pi-minus" text rounded size="small" @click="zoomOut" />
          <span class="text-sm w-12 text-center">{{ Math.round(zoomLevel * 100) }}%</span>
          <Button icon="pi pi-plus" text rounded size="small" @click="zoomIn" />
          <Button icon="pi pi-arrows-alt" text rounded size="small" @click="fitToScreen"
            v-tooltip.top="t('topology.fitToScreen')" />
        </div>

        <!-- Actions -->
        <Button icon="pi pi-refresh" rounded @click="loadTopology" :loading="loading"
          v-tooltip.top="t('common.refresh')" />
        <Button icon="pi pi-download" rounded severity="secondary" @click="exportImage"
          v-tooltip.top="t('topology.exportImage')" />
      </div>
    </div>

    <div class="flex gap-4 flex-1 min-h-0">
      <!-- Main Graph Area -->
      <div class="card flex-1 p-0 relative overflow-hidden">
        <!-- Loading overlay -->
        <div v-if="loading" class="absolute inset-0 flex items-center justify-center z-20"
          style="background: var(--bg-card); opacity: 0.9;">
          <div class="flex flex-col items-center gap-3">
            <i class="pi pi-spin pi-spinner text-4xl text-primary"></i>
            <span>{{ t('topology.loadingTopology') }}</span>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="!loading && nodes.length === 0" class="absolute inset-0 flex items-center justify-center">
          <div class="text-center">
            <i class="pi pi-share-alt text-6xl mb-4" style="color: var(--text-muted);"></i>
            <h3 class="text-lg font-semibold mb-2">{{ t('topology.noData') }}</h3>
            <p class="text-sm mb-4" style="color: var(--text-muted);">{{ t('topology.noDataDescription') }}</p>
            <Button :label="t('common.refresh')" icon="pi pi-refresh" @click="loadTopology" />
          </div>
        </div>

        <!-- Network Graph -->
        <div ref="networkContainer" class="w-full h-full network-container"></div>

        <!-- Mini Legend (bottom-left) -->
        <div class="absolute bottom-4 left-4 z-10">
          <div class="legend-panel">
            <div class="text-xs font-semibold mb-2 uppercase tracking-wide" style="color: var(--text-muted);">
              {{ t('topology.legend') }}
            </div>
            <div class="space-y-1.5">
              <template v-if="viewMode === 'logical' || viewMode === 'combined'">
                <div class="legend-item">
                  <span class="legend-dot" style="background: #6366f1;"></span>
                  <span>{{ t('topology.gateway') }}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-dot" style="background: #3b82f6;"></span>
                  <span>{{ t('topology.subnet') }}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-dot" style="background: #10b981;"></span>
                  <span>{{ t('topology.activeIp') }}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-dot" style="background: #6b7280;"></span>
                  <span>{{ t('topology.otherIp') }}</span>
                </div>
              </template>
              <template v-if="viewMode === 'physical' || viewMode === 'combined'">
                <div class="legend-item">
                  <span class="legend-dot" style="background: #10b981;"></span>
                  <span>{{ t('topology.inService') }}</span>
                </div>
                <div class="legend-item">
                  <span class="legend-dot" style="background: #f59e0b;"></span>
                  <span>{{ t('topology.maintenance') }}</span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- Stats & Details Panel -->
      <div class="w-80 flex flex-col gap-4">
        <!-- Statistics Card -->
        <div class="card">
          <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
            <i class="pi pi-chart-bar text-primary"></i>
            {{ t('topology.statistics') }}
          </h3>
          <div class="space-y-3">
            <div class="stat-row">
              <span>{{ t('topology.totalNodes') }}</span>
              <span class="font-bold">{{ nodes.length }}</span>
            </div>
            <div class="stat-row">
              <span>{{ t('topology.totalConnections') }}</span>
              <span class="font-bold">{{ edges.length }}</span>
            </div>
            <template v-if="stats">
              <div class="border-t pt-3 mt-3" style="border-color: var(--border-color);">
                <div class="stat-row">
                  <span>{{ t('topology.subnets') }}</span>
                  <span class="font-bold">{{ stats.subnets }}</span>
                </div>
                <div class="stat-row">
                  <span>{{ t('topology.activeIps') }}</span>
                  <span class="font-bold text-green-500">{{ stats.ips?.active || 0 }}</span>
                </div>
                <div class="stat-row">
                  <span>{{ t('topology.equipment') }}</span>
                  <span class="font-bold">{{ stats.equipment?.total || 0 }}</span>
                </div>
                <div class="stat-row">
                  <span>{{ t('topology.connectedPorts') }}</span>
                  <span class="font-bold">{{ stats.ports?.connected || 0 }}</span>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- Selected Node Details -->
        <div class="card flex-1 overflow-auto">
          <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
            <i class="pi pi-info-circle text-primary"></i>
            {{ t('topology.nodeDetails') }}
          </h3>

          <div v-if="selectedNode" class="space-y-3">
            <!-- Node Header -->
            <div class="flex items-center gap-3 pb-3 border-b" style="border-color: var(--border-color);">
              <div class="w-10 h-10 rounded-lg flex items-center justify-center"
                :style="{ background: selectedNode.color + '20', color: selectedNode.color }">
                <i :class="selectedNode.icon || 'pi pi-circle-fill'" class="text-lg"></i>
              </div>
              <div class="min-w-0 flex-1">
                <div class="font-semibold truncate">{{ selectedNode.label }}</div>
                <div class="text-xs" style="color: var(--text-muted);">{{ selectedNode.sublabel || selectedNode.type }}</div>
              </div>
            </div>

            <!-- Node Data -->
            <div class="space-y-2">
              <template v-for="(value, key) in selectedNode.data" :key="key">
                <div v-if="value !== null && value !== undefined" class="detail-row">
                  <span class="capitalize">{{ formatKey(key) }}</span>
                  <span class="font-medium truncate">{{ formatValue(key, value) }}</span>
                </div>
              </template>
            </div>

            <!-- Actions -->
            <div class="pt-3 border-t flex gap-2" style="border-color: var(--border-color);">
              <Button v-if="selectedNode.type === 'equipment'" :label="t('topology.viewDetails')"
                size="small" outlined class="flex-1" @click="goToEquipment" />
              <Button v-if="selectedNode.type === 'subnet'" :label="t('topology.viewIpam')"
                size="small" outlined class="flex-1" @click="goToIpam" />
              <Button icon="pi pi-search-plus" size="small" outlined @click="focusNode"
                v-tooltip.top="t('topology.focusNode')" />
            </div>
          </div>

          <div v-else class="flex flex-col items-center justify-center py-8 text-center">
            <i class="pi pi-hand-pointer text-3xl mb-3" style="color: var(--text-muted);"></i>
            <p class="text-sm" style="color: var(--text-muted);">{{ t('topology.selectNodeHint') }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { Network } from 'vis-network';
import api from '../api';

const { t } = useI18n();
const router = useRouter();

// State
const loading = ref(false);
const networkContainer = ref(null);
const nodes = ref([]);
const edges = ref([]);
const stats = ref(null);
const selectedNode = ref(null);
const searchQuery = ref('');
const viewMode = ref('physical');
const filterType = ref(null);
const zoomLevel = ref(1);

let network = null;

// View mode options
const viewModes = computed(() => [
  { label: t('topology.logical'), value: 'logical' },
  { label: t('topology.physical'), value: 'physical' },
  { label: t('topology.combined'), value: 'combined' }
]);

// Filter types based on view mode
const filterTypes = computed(() => {
  if (viewMode.value === 'logical') {
    return [
      { label: t('topology.allTypes'), value: null },
      { label: t('topology.subnets'), value: 'subnet' },
      { label: t('topology.activeOnly'), value: 'active' }
    ];
  } else {
    return [
      { label: t('topology.allTypes'), value: null },
      { label: t('topology.servers'), value: 'server' },
      { label: t('topology.switches'), value: 'switch' },
      { label: t('topology.routers'), value: 'router' },
      { label: t('topology.firewalls'), value: 'firewall' }
    ];
  }
});

// Load topology data
const loadTopology = async () => {
  loading.value = true;
  try {
    // Fetch stats
    const statsRes = await api.get('/topology/stats');
    stats.value = statsRes.data;

    // Fetch topology based on view mode
    let endpoint = '/topology/logical';
    if (viewMode.value === 'physical') {
      endpoint = '/topology/physical';
    } else if (viewMode.value === 'combined') {
      endpoint = '/topology/combined';
    }

    const res = await api.get(endpoint);
    nodes.value = res.data.nodes || [];
    edges.value = res.data.edges || [];

    renderNetwork();
  } catch {
    // Error handled by API interceptor
  } finally {
    loading.value = false;
  }
};

// Render vis-network
const renderNetwork = () => {
  if (!networkContainer.value) return;

  // Apply filters
  let filteredNodes = [...nodes.value];
  let filteredEdges = [...edges.value];

  // Apply search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    const matchingNodeIds = new Set();

    filteredNodes = filteredNodes.filter(n => {
      const matches = n.label?.toLowerCase().includes(query) ||
        n.sublabel?.toLowerCase().includes(query) ||
        n.data?.hostname?.toLowerCase().includes(query) ||
        n.data?.address?.toLowerCase().includes(query);
      if (matches) matchingNodeIds.add(n.id);
      return matches;
    });

    // Also include connected nodes
    filteredEdges = filteredEdges.filter(e =>
      matchingNodeIds.has(e.source) || matchingNodeIds.has(e.target)
    );
  }

  // Apply type filter
  if (filterType.value) {
    if (filterType.value === 'active') {
      filteredNodes = filteredNodes.filter(n =>
        n.type === 'gateway' || n.type === 'subnet' || n.data?.status === 'active'
      );
    } else {
      filteredNodes = filteredNodes.filter(n =>
        n.type === filterType.value ||
        n.equipmentType === filterType.value ||
        n.type === 'gateway'
      );
    }

    const nodeIds = new Set(filteredNodes.map(n => n.id));
    filteredEdges = filteredEdges.filter(e =>
      nodeIds.has(e.source) && nodeIds.has(e.target)
    );
  }

  // Transform data for vis-network
  const visNodes = filteredNodes.map(node => ({
    id: node.id,
    label: node.label,
    title: createTooltip(node),
    group: node.type,
    color: {
      background: node.color + '20',
      border: node.color,
      highlight: {
        background: node.color + '40',
        border: node.color
      }
    },
    font: {
      color: getComputedStyle(document.documentElement).getPropertyValue('--text-main') || '#1f2937',
      size: node.size === 50 ? 16 : node.size === 40 ? 14 : 12
    },
    size: node.size || 25,
    borderWidth: 2,
    shape: getNodeShape(node.type),
    _data: node
  }));

  const visEdges = filteredEdges.map(edge => ({
    id: edge.id,
    from: edge.source,
    to: edge.target,
    color: {
      color: edge.color || '#94a3b8',
      highlight: '#3b82f6'
    },
    width: edge.type === 'connection' ? 3 : 2,
    dashes: edge.style === 'dashed' || edge.style === 'dotted',
    smooth: {
      type: 'continuous',
      roundness: 0.3
    },
    label: edge.label || undefined,
    font: {
      size: 10,
      color: getComputedStyle(document.documentElement).getPropertyValue('--text-muted') || '#6b7280',
      strokeWidth: 3,
      strokeColor: getComputedStyle(document.documentElement).getPropertyValue('--bg-card') || '#ffffff'
    },
    arrows: edge.type === 'network' ? { to: { enabled: true, scaleFactor: 0.5 } } : undefined
  }));

  const options = {
    nodes: {
      font: {
        face: 'Inter, system-ui, sans-serif',
        multi: 'html'
      }
    },
    edges: {
      smooth: {
        type: 'continuous',
        roundness: 0.3
      }
    },
    groups: {
      gateway: {
        shape: 'diamond',
        size: 40
      },
      subnet: {
        shape: 'box',
        borderRadius: 8
      },
      ip: {
        shape: 'dot',
        size: 15
      },
      equipment: {
        shape: 'box',
        borderRadius: 4
      },
      rack: {
        shape: 'box',
        borderRadius: 4
      }
    },
    physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -50,
        centralGravity: 0.01,
        springLength: 150,
        springConstant: 0.08,
        damping: 0.4
      },
      stabilization: {
        enabled: true,
        iterations: 200,
        updateInterval: 25
      }
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      zoomView: true,
      dragView: true,
      navigationButtons: false,
      keyboard: {
        enabled: true,
        speed: { x: 10, y: 10, zoom: 0.02 }
      }
    },
    layout: {
      improvedLayout: true,
      hierarchical: viewMode.value === 'logical' ? {
        enabled: true,
        direction: 'UD',
        sortMethod: 'hubsize',
        levelSeparation: 150,
        nodeSpacing: 100
      } : false
    }
  };

  // Destroy existing network
  if (network) {
    network.destroy();
  }

  // Create new network
  network = new Network(
    networkContainer.value,
    { nodes: visNodes, edges: visEdges },
    options
  );

  // Event handlers
  network.on('click', (params) => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      const node = filteredNodes.find(n => n.id === nodeId);
      selectedNode.value = node || null;
    } else {
      selectedNode.value = null;
    }
  });

  network.on('zoom', (params) => {
    zoomLevel.value = params.scale;
  });

  // Fit to screen after stabilization
  network.once('stabilizationIterationsDone', () => {
    network.fit({ animation: { duration: 500 } });
  });
};

// Helper functions
const getNodeShape = (type) => {
  const shapes = {
    gateway: 'diamond',
    subnet: 'box',
    ip: 'dot',
    equipment: 'box',
    rack: 'box'
  };
  return shapes[type] || 'dot';
};

const createTooltip = (node) => {
  let html = `<div class="topology-tooltip">`;
  html += `<div class="tooltip-header">${node.label}</div>`;
  if (node.sublabel) {
    html += `<div class="tooltip-sublabel">${node.sublabel}</div>`;
  }
  if (node.data) {
    html += `<div class="tooltip-data">`;
    if (node.data.status) html += `<div>Status: ${node.data.status}</div>`;
    if (node.data.hostname) html += `<div>Hostname: ${node.data.hostname}</div>`;
    if (node.data.address) html += `<div>Address: ${node.data.address}</div>`;
    if (node.data.type) html += `<div>Type: ${node.data.type}</div>`;
    if (node.data.location) html += `<div>Location: ${node.data.location}</div>`;
    html += `</div>`;
  }
  html += `</div>`;
  return html;
};

const formatKey = (key) => {
  return key.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').toLowerCase();
};

const formatValue = (key, value) => {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (key.includes('date') && value) return new Date(value).toLocaleDateString();
  return String(value);
};

// Zoom controls
const zoomIn = () => {
  if (network) {
    const scale = network.getScale() * 1.2;
    network.moveTo({ scale, animation: { duration: 200 } });
  }
};

const zoomOut = () => {
  if (network) {
    const scale = network.getScale() / 1.2;
    network.moveTo({ scale, animation: { duration: 200 } });
  }
};

const fitToScreen = () => {
  if (network) {
    network.fit({ animation: { duration: 500 } });
  }
};

// Search handler
const handleSearch = () => {
  renderNetwork();
};

// Focus on selected node
const focusNode = () => {
  if (network && selectedNode.value) {
    network.focus(selectedNode.value.id, {
      scale: 1.5,
      animation: { duration: 500 }
    });
  }
};

// Navigation
const goToEquipment = () => {
  if (selectedNode.value?.data?.id) {
    router.push({ path: '/inventory', query: { equipment: selectedNode.value.data.id } });
  }
};

const goToIpam = () => {
  router.push('/ipam');
};

// Export as image
const exportImage = () => {
  if (network) {
    const canvas = networkContainer.value.querySelector('canvas');
    if (canvas) {
      const link = document.createElement('a');
      link.download = `topology-${viewMode.value}-${new Date().toISOString().split('T')[0]}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  }
};

// Watch view mode changes
watch(viewMode, () => {
  filterType.value = null;
  loadTopology();
});

// Watch filter changes
watch(filterType, () => {
  renderNetwork();
});

// Lifecycle
onMounted(() => {
  loadTopology();
});

onUnmounted(() => {
  if (network) {
    network.destroy();
    network = null;
  }
});
</script>

<style scoped>
.network-container {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
}

.view-mode-selector :deep(.p-selectbutton) {
  border-radius: var(--radius-lg);
}

.legend-panel {
  background: var(--bg-card);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 0.75rem 1rem;
  box-shadow: var(--shadow-lg);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
}

.stat-row span:first-child {
  color: var(--text-muted);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8125rem;
  gap: 0.5rem;
}

.detail-row span:first-child {
  color: var(--text-muted);
  flex-shrink: 0;
}

.detail-row span:last-child {
  text-align: right;
  max-width: 60%;
}
</style>

<style>
/* Global styles for vis-network tooltips */
div.vis-tooltip {
  background-color: var(--bg-card);
  color: var(--text-main);
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border-color);
  font-size: 0.8125rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  max-width: 300px;
}

.topology-tooltip .tooltip-header {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.topology-tooltip .tooltip-sublabel {
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-bottom: 0.5rem;
}

.topology-tooltip .tooltip-data {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.topology-tooltip .tooltip-data > div {
  padding: 0.125rem 0;
}
</style>
