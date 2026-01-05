<template>
  <div class="flex flex-col h-full gap-4">
    <!-- Header with controls -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <div class="flex items-center gap-3">
        <!-- View Mode Selector -->
        <SelectButton v-model="viewMode" :options="viewModes" optionLabel="label" optionValue="value"
          :allowEmpty="false" class="view-mode-selector" />

        <!-- Site Selector (for physical view) -->
        <Dropdown v-if="viewMode === 'physical' && sites.length > 0" v-model="selectedSite" :options="siteOptions"
          optionLabel="label" optionValue="value" :placeholder="t('topology.allSites')" showClear class="w-48" />
      </div>

      <div class="flex items-center gap-2">
        <!-- Zoom controls -->
        <div class="zoom-controls">
          <Button icon="pi pi-minus" text size="small" @click="zoomOut" v-tooltip.top="t('topology.zoomOut')" />
          <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
          <Button icon="pi pi-plus" text size="small" @click="zoomIn" v-tooltip.top="t('topology.zoomIn')" />
        </div>

        <div class="action-divider"></div>

        <Button icon="pi pi-arrows-alt" text @click="fitToScreen" v-tooltip.top="t('topology.fitToScreen')" />
        <Button icon="pi pi-refresh" text @click="loadTopology" :loading="loading" v-tooltip.top="t('common.refresh')" />
        <Button icon="pi pi-download" text @click="exportImage" v-tooltip.top="t('topology.exportImage')" />
      </div>
    </div>

    <div class="flex gap-4 flex-1 min-h-0">
      <!-- Main Graph Area -->
      <div class="graph-container flex-1 relative">
        <!-- Loading overlay -->
        <div v-if="loading" class="loading-overlay">
          <i class="pi pi-spin pi-spinner text-3xl"></i>
          <span>{{ t('topology.loadingTopology') }}</span>
        </div>

        <!-- Empty state -->
        <div v-else-if="nodes.length === 0" class="empty-state">
          <div class="empty-icon">
            <i class="pi pi-share-alt"></i>
          </div>
          <h3>{{ t('topology.noData') }}</h3>
          <p>{{ t('topology.noDataDescription') }}</p>
          <Button :label="t('common.refresh')" icon="pi pi-refresh" size="small" @click="loadTopology" />
        </div>

        <!-- Network Graph -->
        <div ref="networkContainer" class="network-canvas"></div>

        <!-- Legend -->
        <div class="legend-panel" v-if="nodes.length > 0">
          <div class="legend-title">{{ t('topology.legend') }}</div>
          <div class="legend-content">
            <template v-if="viewMode === 'logical'">
              <div class="legend-item">
                <span class="legend-shape diamond" style="background: #6366f1;"></span>
                <span>{{ t('topology.gateway') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-shape box" style="background: #3b82f6;"></span>
                <span>{{ t('topology.subnet') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-dot" style="background: #10b981;"></span>
                <span>{{ t('topology.activeIp') }}</span>
              </div>
            </template>
            <template v-else-if="viewMode === 'physical'">
              <div class="legend-section">{{ t('topology.equipmentTypes') }}</div>
              <div class="legend-item">
                <span class="legend-shape diamond" style="background: #7c3aed;"></span>
                <span>{{ t('topology.router') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-shape box" style="background: #2563eb;"></span>
                <span>{{ t('topology.switch') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-shape hexagon" style="background: #dc2626;"></span>
                <span>{{ t('topology.firewall') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-shape box" style="background: #059669;"></span>
                <span>{{ t('topology.server') }}</span>
              </div>
              <div class="legend-section">{{ t('topology.linkSpeeds') }}</div>
              <div class="legend-item">
                <span class="legend-line" style="background: #10b981; height: 4px;"></span>
                <span>100G</span>
              </div>
              <div class="legend-item">
                <span class="legend-line" style="background: #3b82f6; height: 3px;"></span>
                <span>10G</span>
              </div>
              <div class="legend-item">
                <span class="legend-line" style="background: #64748b; height: 2px;"></span>
                <span>1G</span>
              </div>
            </template>
            <template v-else>
              <div class="legend-item">
                <span class="legend-shape diamond" style="background: #6366f1;"></span>
                <span>{{ t('topology.gateway') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-shape box" style="background: #3b82f6;"></span>
                <span>{{ t('topology.subnet') }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-shape box" style="background: #059669;"></span>
                <span>{{ t('topology.equipment') }}</span>
              </div>
            </template>
          </div>
        </div>

        <!-- Stats Mini Panel -->
        <div class="stats-mini" v-if="stats && nodes.length > 0">
          <div class="stat-item">
            <span class="stat-value">{{ nodes.length }}</span>
            <span class="stat-label">{{ t('topology.nodes') }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ edges.length }}</span>
            <span class="stat-label">{{ t('topology.links') }}</span>
          </div>
        </div>
      </div>

      <!-- Details Panel -->
      <div class="details-panel">
        <!-- Statistics -->
        <div class="panel-section">
          <h3 class="panel-title">
            <i class="pi pi-chart-bar"></i>
            {{ t('topology.statistics') }}
          </h3>
          <div class="stats-grid" v-if="stats">
            <div class="stat-box">
              <div class="stat-number">{{ stats.subnets }}</div>
              <div class="stat-name">{{ t('topology.subnets') }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-number text-green-500">{{ stats.ips?.active || 0 }}</div>
              <div class="stat-name">{{ t('topology.activeIps') }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-number">{{ stats.equipment?.total || 0 }}</div>
              <div class="stat-name">{{ t('topology.equipment') }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-number text-blue-500">{{ stats.ports?.connected || 0 }}</div>
              <div class="stat-name">{{ t('topology.connectedPorts') }}</div>
            </div>
          </div>
        </div>

        <!-- Selected Node -->
        <div class="panel-section flex-1">
          <h3 class="panel-title">
            <i class="pi pi-info-circle"></i>
            {{ t('topology.nodeDetails') }}
          </h3>

          <div v-if="selectedNode" class="node-details">
            <!-- Header -->
            <div class="node-header">
              <div class="node-icon" :style="{ background: selectedNode.color + '20', color: selectedNode.color }">
                <i :class="getNodeIcon(selectedNode)"></i>
              </div>
              <div class="node-info">
                <div class="node-name">{{ selectedNode.label }}</div>
                <div class="node-type">{{ selectedNode.sublabel || selectedNode.type }}</div>
              </div>
            </div>

            <!-- Properties -->
            <div class="node-properties">
              <template v-for="(value, key) in selectedNode.data" :key="key">
                <div v-if="value !== null && value !== undefined && value !== ''" class="property-row">
                  <span class="property-key">{{ formatKey(key) }}</span>
                  <span class="property-value">{{ formatValue(key, value) }}</span>
                </div>
              </template>
            </div>

            <!-- Actions -->
            <div class="node-actions">
              <Button v-if="selectedNode.type === 'equipment'" :label="t('topology.viewInventory')" icon="pi pi-box"
                size="small" outlined class="flex-1" @click="goToEquipment" />
              <Button v-if="selectedNode.type === 'subnet'" :label="t('topology.viewIpam')" icon="pi pi-sitemap"
                size="small" outlined class="flex-1" @click="goToIpam" />
              <Button icon="pi pi-search-plus" size="small" outlined @click="focusNode"
                v-tooltip.top="t('topology.focusNode')" />
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

// State
const loading = ref(false);
const networkContainer = ref(null);
const nodes = ref([]);
const edges = ref([]);
const stats = ref(null);
const sites = ref([]);
const selectedSite = ref(null);
const selectedNode = ref(null);
const viewMode = ref('physical');
const zoomLevel = ref(1);

let network = null;

// View mode options
const viewModes = computed(() => [
  { label: t('topology.logical'), value: 'logical' },
  { label: t('topology.physical'), value: 'physical' },
  { label: t('topology.combined'), value: 'combined' }
]);

// Site options for dropdown
const siteOptions = computed(() => [
  { label: t('topology.allSites'), value: null },
  ...sites.value.map(s => ({ label: `${s.name} (${s.equipment_count})`, value: s.name }))
]);

// Load topology data
const loadTopology = async () => {
  loading.value = true;
  selectedNode.value = null;

  try {
    // Fetch stats
    const statsRes = await api.get('/topology/stats');
    stats.value = statsRes.data;

    // Fetch sites for physical view
    if (viewMode.value === 'physical') {
      try {
        const sitesRes = await api.get('/topology/sites');
        sites.value = sitesRes.data || [];
      } catch {
        sites.value = [];
      }
    }

    // Fetch topology based on view mode and selected site
    let endpoint = '/topology/logical';
    if (viewMode.value === 'physical') {
      if (selectedSite.value) {
        endpoint = `/topology/site/${encodeURIComponent(selectedSite.value)}`;
      } else {
        endpoint = '/topology/physical';
      }
    } else if (viewMode.value === 'combined') {
      endpoint = '/topology/combined';
    }

    const res = await api.get(endpoint);
    nodes.value = res.data.nodes || [];
    edges.value = res.data.edges || [];

    renderNetwork();
  } catch {
    nodes.value = [];
    edges.value = [];
  } finally {
    loading.value = false;
  }
};

// Render vis-network
const renderNetwork = () => {
  if (!networkContainer.value || nodes.value.length === 0) return;

  // Get CSS variables for theming
  const style = getComputedStyle(document.documentElement);
  const textColor = style.getPropertyValue('--text-main')?.trim() || '#1f2937';
  const bgColor = style.getPropertyValue('--bg-secondary')?.trim() || '#f8fafc';

  // Transform nodes for vis-network
  const visNodes = nodes.value.map(node => {
    const baseNode = {
      id: node.id,
      label: node.label,
      title: createTooltip(node),
      color: {
        background: node.color + '15',
        border: node.color,
        highlight: {
          background: node.color + '30',
          border: node.color
        },
        hover: {
          background: node.color + '25',
          border: node.color
        }
      },
      font: {
        color: textColor,
        size: node.size > 35 ? 14 : 12,
        face: 'Inter, system-ui, sans-serif'
      },
      borderWidth: 2,
      borderWidthSelected: 3,
      level: node.level,
      _data: node
    };

    // Shape-specific properties
    switch (node.shape) {
      case 'diamond':
        return { ...baseNode, shape: 'diamond', size: node.size || 30 };
      case 'hexagon':
        return { ...baseNode, shape: 'hexagon', size: node.size || 25 };
      case 'box':
        return {
          ...baseNode,
          shape: 'box',
          margin: 10,
          widthConstraint: { minimum: 80, maximum: 150 }
        };
      case 'dot':
        return { ...baseNode, shape: 'dot', size: node.size || 15 };
      default:
        return { ...baseNode, shape: 'ellipse', size: node.size || 25 };
    }
  });

  // Transform edges for vis-network
  const visEdges = edges.value.map(edge => ({
    id: edge.id,
    from: edge.source,
    to: edge.target,
    color: {
      color: edge.color || '#94a3b8',
      highlight: '#3b82f6',
      hover: '#64748b'
    },
    width: edge.width || 2,
    dashes: edge.dashes || false,
    smooth: {
      type: 'curvedCW',
      roundness: 0.1
    },
    label: edge.label || undefined,
    font: {
      size: 10,
      color: '#64748b',
      strokeWidth: 2,
      strokeColor: bgColor,
      align: 'middle'
    },
    arrows: edge.type === 'network' ? { to: { enabled: true, scaleFactor: 0.5 } } : undefined
  }));

  // Network options
  const options = {
    nodes: {
      font: {
        face: 'Inter, system-ui, sans-serif'
      },
      shadow: {
        enabled: true,
        color: 'rgba(0, 0, 0, 0.1)',
        size: 8,
        x: 2,
        y: 2
      }
    },
    edges: {
      smooth: {
        type: 'curvedCW',
        roundness: 0.1
      },
      shadow: false
    },
    physics: {
      enabled: true,
      solver: 'hierarchicalRepulsion',
      hierarchicalRepulsion: {
        centralGravity: 0.2,
        springLength: 150,
        springConstant: 0.01,
        nodeDistance: 180,
        damping: 0.09
      },
      stabilization: {
        enabled: true,
        iterations: 150,
        updateInterval: 25,
        fit: true
      }
    },
    layout: {
      hierarchical: {
        enabled: true,
        direction: 'UD',
        sortMethod: 'directed',
        levelSeparation: 120,
        nodeSpacing: 150,
        treeSpacing: 200,
        blockShifting: true,
        edgeMinimization: true,
        parentCentralization: true
      }
    },
    interaction: {
      hover: true,
      tooltipDelay: 150,
      zoomView: true,
      dragView: true,
      dragNodes: true,
      selectConnectedEdges: true,
      hoverConnectedEdges: true,
      keyboard: {
        enabled: true,
        speed: { x: 10, y: 10, zoom: 0.02 }
      }
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
      const node = nodes.value.find(n => n.id === nodeId);
      selectedNode.value = node || null;
    } else {
      selectedNode.value = null;
    }
  });

  network.on('zoom', (params) => {
    zoomLevel.value = params.scale;
  });

  network.on('doubleClick', (params) => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      const node = nodes.value.find(n => n.id === nodeId);
      if (node) {
        if (node.type === 'equipment') {
          goToEquipment(node.data.id);
        } else if (node.type === 'subnet') {
          goToIpam();
        }
      }
    }
  });

  // Fit to screen after stabilization
  network.once('stabilizationIterationsDone', () => {
    network.fit({ animation: { duration: 300, easingFunction: 'easeOutQuad' } });
    zoomLevel.value = network.getScale();
  });
};

// Helper functions
const createTooltip = (node) => {
  let html = `<div style="padding: 8px 12px; max-width: 250px;">`;
  html += `<div style="font-weight: 600; margin-bottom: 4px;">${node.label}</div>`;
  if (node.sublabel) {
    html += `<div style="color: #64748b; font-size: 12px; margin-bottom: 8px;">${node.sublabel}</div>`;
  }
  if (node.data) {
    const importantKeys = ['status', 'type', 'location', 'ip_address', 'cidr'];
    for (const key of importantKeys) {
      if (node.data[key]) {
        html += `<div style="font-size: 11px; color: #94a3b8;">${formatKey(key)}: ${node.data[key]}</div>`;
      }
    }
  }
  html += `</div>`;
  return html;
};

const getNodeIcon = (node) => {
  if (!node) return 'pi pi-circle';
  const type = node.type || '';
  const eqType = (node.equipmentType || '').toLowerCase();

  if (type === 'gateway') return 'pi pi-globe';
  if (type === 'subnet') return 'pi pi-sitemap';
  if (type === 'ip') return 'pi pi-circle-fill';
  if (eqType.includes('router')) return 'pi pi-share-alt';
  if (eqType.includes('switch')) return 'pi pi-sitemap';
  if (eqType.includes('firewall')) return 'pi pi-shield';
  if (eqType.includes('server')) return 'pi pi-server';
  if (eqType.includes('storage')) return 'pi pi-database';
  return 'pi pi-box';
};

const formatKey = (key) => {
  return key.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

const formatValue = (key, value) => {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (key.includes('date') && value) return new Date(value).toLocaleDateString();
  return String(value);
};

// Controls
const zoomIn = () => {
  if (network) {
    const scale = network.getScale() * 1.25;
    network.moveTo({ scale, animation: { duration: 150 } });
  }
};

const zoomOut = () => {
  if (network) {
    const scale = network.getScale() / 1.25;
    network.moveTo({ scale, animation: { duration: 150 } });
  }
};

const fitToScreen = () => {
  if (network) {
    network.fit({ animation: { duration: 300 } });
  }
};

const focusNode = () => {
  if (network && selectedNode.value) {
    network.focus(selectedNode.value.id, {
      scale: 1.5,
      animation: { duration: 300 }
    });
  }
};

// Navigation
const goToEquipment = (id) => {
  const eqId = id || selectedNode.value?.data?.id;
  if (eqId) {
    router.push({ path: '/inventory', query: { equipment: eqId } });
  }
};

const goToIpam = () => {
  router.push('/ipam');
};

// Export as image
const exportImage = () => {
  if (network) {
    const canvas = networkContainer.value?.querySelector('canvas');
    if (canvas) {
      const link = document.createElement('a');
      link.download = `topology-${viewMode.value}-${new Date().toISOString().split('T')[0]}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  }
};

// Watchers
watch(viewMode, () => {
  selectedSite.value = null;
  loadTopology();
});

watch(selectedSite, () => {
  loadTopology();
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
.graph-container {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 500px;
}

.network-canvas {
  width: 100%;
  height: 100%;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  background: var(--bg-secondary);
  color: var(--text-muted);
  z-index: 10;
}

.empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem;
  text-align: center;
}

.empty-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-icon i {
  font-size: 2.5rem;
  color: var(--text-muted);
}

.empty-state h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}

.empty-state p {
  color: var(--text-muted);
  font-size: 0.875rem;
  max-width: 300px;
  margin: 0;
}

/* Controls */
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
  font-weight: 500;
  min-width: 3rem;
  text-align: center;
  color: var(--text-secondary);
}

.action-divider {
  width: 1px;
  height: 24px;
  background: var(--border-color);
  margin: 0 0.25rem;
}

/* Legend */
.legend-panel {
  position: absolute;
  bottom: 1rem;
  left: 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 0.75rem 1rem;
  box-shadow: var(--shadow-lg);
  z-index: 5;
  max-width: 180px;
}

.legend-title {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.legend-content {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.legend-section {
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-color);
}

.legend-section:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
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

.legend-shape {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.legend-shape.box {
  border-radius: 2px;
}

.legend-shape.diamond {
  transform: rotate(45deg);
  width: 10px;
  height: 10px;
}

.legend-shape.hexagon {
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
}

.legend-line {
  width: 24px;
  border-radius: 1px;
  flex-shrink: 0;
}

/* Stats Mini */
.stats-mini {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  gap: 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 0.5rem 1rem;
  box-shadow: var(--shadow-md);
  z-index: 5;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.125rem;
}

.stat-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-main);
}

.stat-label {
  font-size: 0.625rem;
  text-transform: uppercase;
  color: var(--text-muted);
}

/* Details Panel */
.details-panel {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1rem;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-main);
  margin: 0 0 0.75rem 0;
}

.panel-title i {
  color: var(--primary-color);
  font-size: 0.875rem;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.stat-box {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 0.75rem;
  text-align: center;
}

.stat-number {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-main);
}

.stat-name {
  font-size: 0.6875rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.025em;
  margin-top: 0.125rem;
}

/* Node Details */
.node-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-color);
}

.node-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.node-icon i {
  font-size: 1.125rem;
}

.node-info {
  min-width: 0;
  flex: 1;
}

.node-name {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-type {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.node-properties {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.property-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  font-size: 0.8125rem;
}

.property-key {
  color: var(--text-muted);
  flex-shrink: 0;
}

.property-value {
  color: var(--text-main);
  font-weight: 500;
  text-align: right;
  word-break: break-word;
  max-width: 60%;
}

.node-actions {
  display: flex;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}

.no-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  text-align: center;
  color: var(--text-muted);
}

.no-selection i {
  font-size: 2rem;
  margin-bottom: 0.75rem;
  opacity: 0.5;
}

.no-selection p {
  font-size: 0.875rem;
  margin: 0;
}

/* View Mode Selector */
.view-mode-selector :deep(.p-selectbutton) {
  border-radius: var(--radius-lg);
}

.view-mode-selector :deep(.p-button) {
  padding: 0.5rem 1rem;
  font-size: 0.8125rem;
}
</style>

<style>
/* Global vis-network tooltip styles */
div.vis-tooltip {
  background-color: var(--bg-card, #ffffff);
  color: var(--text-main, #1f2937);
  border-radius: 8px;
  border: 1px solid var(--border-color, #e2e8f0);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  font-family: Inter, system-ui, sans-serif;
  font-size: 13px;
}
</style>
