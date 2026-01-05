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
            <div class="legend-section">{{ t('topology.equipmentTypes') }}</div>
            <div v-for="legendItem in uniqueEquipmentTypes" :key="legendItem.type" class="legend-item">
              <span class="legend-icon" :style="{ background: legendItem.color }">
                <i :class="legendItem.icon"></i>
              </span>
              {{ legendItem.type }}
            </div>
            <div class="legend-divider"></div>
            <div class="legend-section">{{ t('topology.linkSpeeds') }}</div>
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
                <i :class="selectedNode.icon || getNodeIcon(selectedNode)"></i>
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

// Get unique equipment types for legend
const uniqueEquipmentTypes = computed(() => {
  const types = new Map();
  nodes.value.forEach(node => {
    if (node.type === 'equipment' && node.sublabel) {
      if (!types.has(node.sublabel)) {
        types.set(node.sublabel, {
          type: node.sublabel,
          icon: node.icon || 'pi pi-box',
          color: node.color
        });
      }
    }
  });
  return Array.from(types.values());
});

// SVG icon paths for PrimeIcons (simplified versions)
const iconSvgPaths = {
  'pi-server': 'M4 6h16v4H4zm0 8h16v4H4zm2-6h2v2H6zm0 8h2v2H6z',
  'pi-desktop': 'M4 4h16v12H4zm4 14h8v2H8zm2-14v10h8V4z',
  'pi-database': 'M12 2C6.48 2 2 4.02 2 6.5v11C2 19.98 6.48 22 12 22s10-2.02 10-4.5v-11C22 4.02 17.52 2 12 2zm0 2c4.42 0 8 1.79 8 4s-3.58 4-8 4-8-1.79-8-4 3.58-4 8-4zm8 13.5c0 2.21-3.58 4-8 4s-8-1.79-8-4v-3c1.78 1.23 4.61 2 8 2s6.22-.77 8-2v3z',
  'pi-wifi': 'M12 18c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm-4.24-4.24l1.41 1.41c1.52-1.52 4.14-1.52 5.66 0l1.41-1.41c-2.34-2.34-6.14-2.34-8.48 0zM4.93 10.93l1.41 1.41c3.12-3.12 8.2-3.12 11.32 0l1.41-1.41c-3.9-3.9-10.24-3.9-14.14 0zM1.1 7.1l1.41 1.41c4.69-4.69 12.29-4.69 16.98 0l1.41-1.41C15.22 1.42 5.78 1.42 1.1 7.1z',
  'pi-shield': 'M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z',
  'pi-box': 'M21 16.5c0 .38-.21.71-.53.88l-7.9 4.44c-.16.12-.36.18-.57.18s-.41-.06-.57-.18l-7.9-4.44A.991.991 0 013 16.5v-9c0-.38.21-.71.53-.88l7.9-4.44c.16-.12.36-.18.57-.18s.41.06.57.18l7.9 4.44c.32.17.53.5.53.88v9z',
  'pi-sitemap': 'M22 11V3h-7v3H9V3H2v8h7V8h2v10h4v3h7v-8h-7v3h-2V8h2v3h7z',
  'pi-bolt': 'M11 21h-1l1-7H7.5c-.58 0-.57-.32-.38-.66.19-.34.05-.08.07-.12C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-.07.15C12.96 17.55 11 21 11 21z',
  'pi-globe': 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z',
  'pi-print': 'M19 8H5c-1.66 0-3 1.34-3 3v6h4v4h12v-4h4v-6c0-1.66-1.34-3-3-3zm-3 11H8v-5h8v5zm3-7c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm-1-9H6v4h12V3z',
  'pi-mobile': 'M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z',
  'pi-cog': 'M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z',
  'pi-sliders-h': 'M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z',
  'pi-tablet': 'M21 4H3c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h18c1.1 0 1.99-.9 1.99-2L23 6c0-1.1-.9-2-2-2zm-2 14H5V6h14v12z',
  'pi-video': 'M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z',
  'pi-share-alt': 'M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z'
};

// Create SVG data URL for an icon
const createIconSvg = (iconClass, color) => {
  const iconName = iconClass.replace('pi ', '').replace('pi-', '');
  const path = iconSvgPaths[`pi-${iconName}`] || iconSvgPaths['pi-box'];

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="48" height="48">
    <circle cx="12" cy="12" r="11" fill="${color}" stroke="white" stroke-width="1"/>
    <g transform="translate(4, 4) scale(0.67)">
      <path d="${path}" fill="white"/>
    </g>
  </svg>`;

  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
};

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

  const visNodes = nodes.value.map((node) => {
    const isEquipment = node.type === 'equipment';

    if (isEquipment) {
      // Use image shape with SVG icon
      const iconClass = node.icon || 'pi-box';
      return {
        id: node.id,
        label: node.label,
        title: createTooltip(node),
        group: node.group,
        shape: 'image',
        image: createIconSvg(iconClass, node.color),
        size: 24,
        font: {
          color: textColor,
          size: 11,
          face: 'Inter, system-ui, sans-serif',
          vadjust: 8
        },
        _data: node
      };
    } else {
      // Logical view - keep original shapes
      return {
        id: node.id,
        label: node.label,
        title: createTooltip(node),
        group: node.group,
        color: {
          background: node.color + '30',
          border: node.color,
          highlight: { background: node.color + '50', border: node.color },
          hover: { background: node.color + '40', border: node.color }
        },
        font: { color: textColor, size: 11 },
        borderWidth: 2,
        shape: node.shape || 'dot',
        size: node.size || 20,
        _data: node
      };
    }
  });

  const visEdges = edges.value.map(edge => ({
    id: edge.id,
    from: edge.source,
    to: edge.target,
    color: { color: edge.color || '#94a3b8', highlight: '#3b82f6', opacity: 0.7 },
    width: edge.width || 1,
    dashes: edge.dashes || false,
    smooth: { type: 'continuous', roundness: 0.2 }
  }));

  const options = {
    nodes: {
      font: {
        face: 'Inter, system-ui, sans-serif',
        strokeWidth: 3,
        strokeColor: 'rgba(255,255,255,0.95)'
      },
      shadow: { enabled: true, color: 'rgba(0,0,0,0.15)', size: 10, x: 0, y: 4 }
    },
    edges: {
      smooth: { type: 'continuous', roundness: 0.2 },
      arrows: { to: { enabled: false } }
    },
    physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -150,
        centralGravity: 0.005,
        springLength: 200,
        springConstant: 0.04,
        damping: 0.7,
        avoidOverlap: 1
      },
      stabilization: { iterations: 250, fit: true },
      maxVelocity: 40,
      minVelocity: 0.2
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      dragNodes: true,
      dragView: true,
      zoomView: true
    },
    layout: {
      improvedLayout: true,
      randomSeed: 42
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
    network.fit({ animation: { duration: 400 } });
    zoomLevel.value = network.getScale();
  });
};

const createTooltip = (node) => {
  let html = `<div style="padding:10px 14px;max-width:260px;">`;
  html += `<div style="font-weight:600;font-size:13px;margin-bottom:4px;">${node.label}</div>`;
  if (node.sublabel) html += `<div style="color:#64748b;font-size:11px;margin-bottom:8px;">${node.sublabel}</div>`;
  if (node.data) {
    const displayKeys = ['status', 'type', 'site', 'room', 'rack', 'ip_address', 'cidr', 'manufacturer', 'model'];
    displayKeys.forEach(key => {
      if (node.data[key]) html += `<div style="font-size:11px;color:#64748b;padding:2px 0;"><span style="color:#94a3b8;">${formatKey(key)}:</span> ${node.data[key]}</div>`;
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
  if (type.includes('access')) return 'pi pi-wifi';
  if (type.includes('workstation')) return 'pi pi-desktop';
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
  padding: 0.75rem 1rem;
  font-size: 0.6875rem;
  z-index: 5;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  max-height: 300px;
  overflow-y: auto;
}

.legend-title {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin-bottom: 0.625rem;
  font-size: 0.625rem;
}

.legend-section {
  font-weight: 500;
  font-size: 0.625rem;
  color: var(--text-muted);
  margin-top: 0.5rem;
  margin-bottom: 0.375rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  color: var(--text-secondary);
  padding: 0.2rem 0;
}

.legend-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 9px;
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
  margin: 0.625rem 0;
}

.legend-line {
  width: 24px;
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
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
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
  border-radius: 8px;
  border: 1px solid var(--border-color, #e2e8f0);
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  font-family: Inter, system-ui, sans-serif;
  font-size: 12px;
}
</style>
