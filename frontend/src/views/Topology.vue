<template>
  <div class="flex flex-col h-full gap-4">
    <!-- Header -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <div class="flex items-center gap-3">
        <SelectButton v-model="viewMode" :options="viewModes" optionLabel="label" optionValue="value"
          :allowEmpty="false" />

        <Dropdown v-if="viewMode === 'physical' && sites.length > 0" v-model="selectedSite" :options="siteOptions"
          optionLabel="label" optionValue="value" :placeholder="t('topology.allSites')" showClear class="w-52" />
      </div>

      <div class="flex items-center gap-2">
        <div class="zoom-controls">
          <Button icon="pi pi-minus" text size="small" @click="zoomOut" />
          <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
          <Button icon="pi pi-plus" text size="small" @click="zoomIn" />
        </div>
        <Button icon="pi pi-arrows-alt" text @click="fitToScreen" v-tooltip.top="t('topology.fitToScreen')" />
        <Button icon="pi pi-refresh" text @click="loadTopology" :loading="loading" v-tooltip.top="t('common.refresh')" />
        <Button icon="pi pi-download" text @click="exportImage" v-tooltip.top="t('topology.exportImage')" />
      </div>
    </div>

    <div class="flex gap-4 flex-1 min-h-0">
      <!-- Graph -->
      <div class="graph-container flex-1 relative">
        <div v-if="loading" class="loading-overlay">
          <i class="pi pi-spin pi-spinner text-3xl"></i>
          <span>{{ t('topology.loadingTopology') }}</span>
        </div>

        <div v-else-if="nodes.length === 0" class="empty-state">
          <i class="pi pi-share-alt text-5xl mb-4" style="color: var(--text-muted);"></i>
          <h3>{{ t('topology.noData') }}</h3>
          <p>{{ t('topology.noDataDescription') }}</p>
        </div>

        <div ref="networkContainer" class="network-canvas"></div>

        <!-- Legend -->
        <div v-if="nodes.length > 0" class="legend-panel">
          <div class="legend-title">{{ t('topology.legend') }}</div>
          <template v-if="viewMode === 'physical'">
            <div class="legend-item"><span class="legend-color" style="background: #7c3aed;"></span> Router</div>
            <div class="legend-item"><span class="legend-color" style="background: #2563eb;"></span> Switch</div>
            <div class="legend-item"><span class="legend-color" style="background: #dc2626;"></span> Firewall</div>
            <div class="legend-item"><span class="legend-color" style="background: #059669;"></span> Server</div>
            <div class="legend-item"><span class="legend-color" style="background: #0891b2;"></span> Storage</div>
            <div class="legend-item"><span class="legend-color" style="background: #f59e0b;"></span> Access Point</div>
            <div class="legend-divider"></div>
            <div class="legend-item"><span class="legend-line thick"></span> 10G+</div>
            <div class="legend-item"><span class="legend-line medium"></span> 1G</div>
            <div class="legend-item"><span class="legend-line thin"></span> &lt;1G</div>
          </template>
          <template v-else>
            <div class="legend-item"><span class="legend-shape diamond"></span> {{ t('topology.gateway') }}</div>
            <div class="legend-item"><span class="legend-shape box"></span> {{ t('topology.subnet') }}</div>
            <div class="legend-item"><span class="legend-color" style="background: #10b981;"></span> {{ t('topology.activeIp') }}</div>
          </template>
        </div>

        <!-- Stats overlay -->
        <div v-if="nodes.length > 0" class="stats-overlay">
          <span><strong>{{ nodes.length }}</strong> {{ t('topology.nodes') }}</span>
          <span><strong>{{ edges.length }}</strong> {{ t('topology.links') }}</span>
          <span v-if="groups.length > 0"><strong>{{ groups.length }}</strong> {{ viewMode === 'physical' ? 'Sites' : 'Groups' }}</span>
        </div>
      </div>

      <!-- Details Panel -->
      <div class="details-panel">
        <div class="panel-card">
          <h3><i class="pi pi-chart-bar"></i> {{ t('topology.statistics') }}</h3>
          <div class="stats-grid" v-if="stats">
            <div class="stat-item">
              <span class="stat-value">{{ stats.subnets }}</span>
              <span class="stat-label">{{ t('topology.subnets') }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-value text-green-500">{{ stats.ips?.active || 0 }}</span>
              <span class="stat-label">{{ t('topology.activeIps') }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ stats.equipment?.total || 0 }}</span>
              <span class="stat-label">{{ t('topology.equipment') }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-value text-blue-500">{{ stats.ports?.connected || 0 }}</span>
              <span class="stat-label">{{ t('topology.connectedPorts') }}</span>
            </div>
          </div>
        </div>

        <div class="panel-card flex-1">
          <h3><i class="pi pi-info-circle"></i> {{ t('topology.nodeDetails') }}</h3>

          <div v-if="selectedNode" class="node-details">
            <div class="node-header">
              <div class="node-icon" :style="{ background: selectedNode.color + '20', color: selectedNode.color }">
                <i :class="getNodeIcon(selectedNode)"></i>
              </div>
              <div>
                <div class="node-name">{{ selectedNode.label }}</div>
                <div class="node-type">{{ selectedNode.sublabel || selectedNode.type }}</div>
              </div>
            </div>

            <div class="node-props">
              <template v-for="(value, key) in selectedNode.data" :key="key">
                <div v-if="value != null && value !== ''" class="prop-row">
                  <span>{{ formatKey(key) }}</span>
                  <span>{{ value }}</span>
                </div>
              </template>
            </div>

            <div class="node-actions">
              <Button v-if="selectedNode.type === 'equipment'" :label="t('topology.viewInventory')" icon="pi pi-box"
                size="small" outlined @click="goToEquipment" />
              <Button v-if="selectedNode.type === 'subnet'" :label="t('topology.viewIpam')" icon="pi pi-sitemap"
                size="small" outlined @click="goToIpam" />
            </div>
          </div>

          <div v-else class="no-selection">
            <i class="pi pi-hand-pointer"></i>
            <p>{{ t('topology.selectNodeHint') }}</p>
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

const loading = ref(false);
const networkContainer = ref(null);
const nodes = ref([]);
const edges = ref([]);
const groups = ref([]);
const stats = ref(null);
const sites = ref([]);
const selectedSite = ref(null);
const selectedNode = ref(null);
const viewMode = ref('physical');
const zoomLevel = ref(1);

let network = null;

const viewModes = computed(() => [
  { label: t('topology.logical'), value: 'logical' },
  { label: t('topology.physical'), value: 'physical' },
  { label: t('topology.combined'), value: 'combined' }
]);

const siteOptions = computed(() => [
  { label: t('topology.allSites'), value: null },
  ...sites.value.map(s => ({ label: `${s.name} (${s.equipment_count})`, value: s.name }))
]);

const loadTopology = async () => {
  loading.value = true;
  selectedNode.value = null;

  try {
    const [statsRes, sitesRes] = await Promise.all([
      api.get('/topology/stats'),
      viewMode.value === 'physical' ? api.get('/topology/sites').catch(() => ({ data: [] })) : Promise.resolve({ data: [] })
    ]);

    stats.value = statsRes.data;
    sites.value = sitesRes.data || [];

    let endpoint = '/topology/logical';
    if (viewMode.value === 'physical') {
      endpoint = selectedSite.value ? `/topology/site/${encodeURIComponent(selectedSite.value)}` : '/topology/physical';
    } else if (viewMode.value === 'combined') {
      endpoint = '/topology/combined';
    }

    const res = await api.get(endpoint);
    nodes.value = res.data.nodes || [];
    edges.value = res.data.edges || [];
    groups.value = res.data.groups || [];

    renderNetwork();
  } catch {
    nodes.value = [];
    edges.value = [];
    groups.value = [];
  } finally {
    loading.value = false;
  }
};

const renderNetwork = () => {
  if (!networkContainer.value || nodes.value.length === 0) return;

  const style = getComputedStyle(document.documentElement);
  const textColor = style.getPropertyValue('--text-main')?.trim() || '#1f2937';

  // Group colors for clustering
  const groupColors = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#06b6d4', '#84cc16'];

  const visNodes = nodes.value.map((node, idx) => {
    const groupIndex = groups.value.findIndex(g => g.id === node.group);
    const groupColor = groupIndex >= 0 ? groupColors[groupIndex % groupColors.length] : null;

    return {
      id: node.id,
      label: node.label,
      title: createTooltip(node),
      group: node.group,
      color: {
        background: node.color + '18',
        border: node.color,
        highlight: { background: node.color + '35', border: node.color },
        hover: { background: node.color + '28', border: node.color }
      },
      font: { color: textColor, size: 12 },
      borderWidth: 2,
      shape: node.shape || 'box',
      size: node.size || 25,
      margin: node.shape === 'box' ? 8 : undefined,
      _data: node
    };
  });

  const visEdges = edges.value.map(edge => ({
    id: edge.id,
    from: edge.source,
    to: edge.target,
    color: { color: edge.color || '#94a3b8', highlight: '#3b82f6' },
    width: edge.width || 1,
    dashes: edge.dashes || false,
    label: edge.label || undefined,
    font: { size: 9, color: '#64748b', strokeWidth: 2, strokeColor: '#ffffff' },
    smooth: { type: 'continuous', roundness: 0.2 }
  }));

  // Create group configuration for clustering
  const groupConfig = {};
  groups.value.forEach((g, idx) => {
    groupConfig[g.id] = {
      color: { background: groupColors[idx % groupColors.length] + '15', border: groupColors[idx % groupColors.length] }
    };
  });

  const options = {
    nodes: {
      font: { face: 'Inter, system-ui, sans-serif' },
      shadow: { enabled: true, color: 'rgba(0,0,0,0.08)', size: 6, x: 1, y: 2 }
    },
    edges: {
      smooth: { type: 'continuous', roundness: 0.2 }
    },
    groups: groupConfig,
    physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -80,
        centralGravity: 0.015,
        springLength: 120,
        springConstant: 0.1,
        damping: 0.5
      },
      stabilization: { iterations: 150, fit: true }
    },
    interaction: {
      hover: true,
      tooltipDelay: 100,
      dragNodes: true,
      dragView: true,
      zoomView: true
    }
  };

  if (network) network.destroy();

  network = new Network(networkContainer.value, { nodes: visNodes, edges: visEdges }, options);

  network.on('click', params => {
    if (params.nodes.length > 0) {
      const node = nodes.value.find(n => n.id === params.nodes[0]);
      selectedNode.value = node || null;
    } else {
      selectedNode.value = null;
    }
  });

  network.on('zoom', params => {
    zoomLevel.value = params.scale;
  });

  network.on('doubleClick', params => {
    if (params.nodes.length > 0) {
      const node = nodes.value.find(n => n.id === params.nodes[0]);
      if (node?.type === 'equipment') goToEquipment(node.data?.id);
      else if (node?.type === 'subnet') goToIpam();
    }
  });

  network.once('stabilizationIterationsDone', () => {
    network.fit({ animation: { duration: 300 } });
    zoomLevel.value = network.getScale();
  });
};

const createTooltip = (node) => {
  let html = `<div style="padding:8px 12px;max-width:220px;">`;
  html += `<div style="font-weight:600;margin-bottom:4px;">${node.label}</div>`;
  if (node.sublabel) html += `<div style="color:#64748b;font-size:11px;margin-bottom:6px;">${node.sublabel}</div>`;
  if (node.data) {
    ['status', 'type', 'site', 'room', 'ip_address', 'cidr'].forEach(key => {
      if (node.data[key]) html += `<div style="font-size:10px;color:#94a3b8;">${formatKey(key)}: ${node.data[key]}</div>`;
    });
  }
  return html + '</div>';
};

const getNodeIcon = (node) => {
  if (!node) return 'pi pi-circle';
  const type = (node.equipmentType || node.type || '').toLowerCase();
  if (type.includes('router')) return 'pi pi-share-alt';
  if (type.includes('switch')) return 'pi pi-sitemap';
  if (type.includes('firewall')) return 'pi pi-shield';
  if (type.includes('server')) return 'pi pi-server';
  if (type.includes('storage')) return 'pi pi-database';
  if (type === 'gateway') return 'pi pi-globe';
  if (type === 'subnet') return 'pi pi-sitemap';
  return 'pi pi-box';
};

const formatKey = (key) => key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

const zoomIn = () => network?.moveTo({ scale: network.getScale() * 1.25, animation: { duration: 150 } });
const zoomOut = () => network?.moveTo({ scale: network.getScale() / 1.25, animation: { duration: 150 } });
const fitToScreen = () => network?.fit({ animation: { duration: 300 } });

const goToEquipment = (id) => {
  const eqId = id || selectedNode.value?.data?.id;
  if (eqId) router.push({ path: '/inventory', query: { equipment: eqId } });
};

const goToIpam = () => router.push('/ipam');

const exportImage = () => {
  const canvas = networkContainer.value?.querySelector('canvas');
  if (canvas) {
    const link = document.createElement('a');
    link.download = `topology-${viewMode.value}-${new Date().toISOString().split('T')[0]}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }
};

watch(viewMode, () => { selectedSite.value = null; loadTopology(); });
watch(selectedSite, loadTopology);

onMounted(loadTopology);
onUnmounted(() => network?.destroy());
</script>

<style scoped>
.graph-container {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 500px;
  position: relative;
}

.network-canvas {
  width: 100%;
  height: 100%;
}

.loading-overlay, .empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-secondary);
}

.empty-state h3 { font-size: 1rem; font-weight: 600; color: var(--text-main); margin: 0; }
.empty-state p { font-size: 0.8125rem; max-width: 280px; text-align: center; margin: 0; }

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
}

.zoom-level {
  font-size: 0.75rem;
  min-width: 2.5rem;
  text-align: center;
  color: var(--text-secondary);
}

.legend-panel {
  position: absolute;
  bottom: 1rem;
  left: 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0.625rem 0.875rem;
  font-size: 0.6875rem;
  z-index: 5;
}

.legend-title {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-secondary);
  padding: 0.125rem 0;
}

.legend-color {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-shape {
  width: 10px;
  height: 10px;
}

.legend-shape.diamond {
  background: #6366f1;
  transform: rotate(45deg);
  width: 8px;
  height: 8px;
}

.legend-shape.box {
  background: #3b82f6;
  border-radius: 2px;
}

.legend-divider {
  height: 1px;
  background: var(--border-color);
  margin: 0.375rem 0;
}

.legend-line {
  width: 20px;
  border-radius: 1px;
}

.legend-line.thick { height: 4px; background: #3b82f6; }
.legend-line.medium { height: 2px; background: #64748b; }
.legend-line.thin { height: 1px; background: #94a3b8; }

.stats-overlay {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  gap: 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0.5rem 0.875rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
  z-index: 5;
}

.details-panel {
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1rem;
}

.panel-card h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 600;
  margin: 0 0 0.75rem 0;
  color: var(--text-main);
}

.panel-card h3 i { color: var(--primary-color); font-size: 0.875rem; }

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.625rem;
}

.stat-item {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 0.625rem;
  text-align: center;
}

.stat-value { font-size: 1.125rem; font-weight: 700; color: var(--text-main); }
.stat-label { font-size: 0.625rem; text-transform: uppercase; color: var(--text-muted); }

.node-details { display: flex; flex-direction: column; gap: 0.75rem; }

.node-header {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding-bottom: 0.625rem;
  border-bottom: 1px solid var(--border-color);
}

.node-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.node-name { font-weight: 600; font-size: 0.875rem; color: var(--text-main); }
.node-type { font-size: 0.6875rem; color: var(--text-muted); }

.node-props { display: flex; flex-direction: column; gap: 0.375rem; }

.prop-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
}

.prop-row span:first-child { color: var(--text-muted); }
.prop-row span:last-child { color: var(--text-main); font-weight: 500; text-align: right; max-width: 60%; word-break: break-word; }

.node-actions {
  display: flex;
  gap: 0.5rem;
  padding-top: 0.625rem;
  border-top: 1px solid var(--border-color);
}

.no-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem 1rem;
  text-align: center;
  color: var(--text-muted);
}

.no-selection i { font-size: 1.5rem; margin-bottom: 0.5rem; opacity: 0.5; }
.no-selection p { font-size: 0.8125rem; margin: 0; }
</style>

<style>
div.vis-tooltip {
  background: var(--bg-card, #fff);
  color: var(--text-main, #1f2937);
  border-radius: 6px;
  border: 1px solid var(--border-color, #e2e8f0);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  font-family: Inter, system-ui, sans-serif;
  font-size: 12px;
}
</style>
