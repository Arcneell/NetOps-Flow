<template>
  <div class="flex flex-col h-full gap-4">
    <!-- Header -->
    <div class="flex items-center justify-between flex-wrap gap-3">
      <div class="flex items-center gap-3">
        <SelectButton v-model="viewMode" :options="viewModes" optionLabel="label" optionValue="value"
          :allowEmpty="false" />

        <Dropdown v-if="viewMode === 'physical' && sites.length > 0" v-model="selectedSite" :options="siteOptions"
          optionLabel="label" optionValue="value" :placeholder="t('topology.allSites')" showClear class="w-52" />

        <!-- Link Mode Toggle -->
        <Button v-if="viewMode === 'physical'"
          :icon="linkMode ? 'pi pi-times' : 'pi pi-link'"
          :label="linkMode ? t('topology.cancelLink') : t('topology.createLink')"
          :severity="linkMode ? 'danger' : 'secondary'"
          size="small"
          @click="toggleLinkMode" />
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

    <!-- Link Mode Banner -->
    <div v-if="linkMode" class="link-mode-banner">
      <i class="pi pi-info-circle"></i>
      <span v-if="!linkSource">{{ t('topology.selectSource') }}</span>
      <span v-else>{{ t('topology.selectTarget', { source: linkSource.label }) }}</span>
    </div>

    <div class="flex gap-4 flex-1 min-h-0">
      <!-- Graph -->
      <div class="graph-container flex-1 relative" :class="{ 'link-mode-active': linkMode }">
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
        <div v-if="nodes.length > 0 && !linkMode" class="legend-panel">
          <div class="legend-title">{{ t('topology.legend') }}</div>
          <template v-if="viewMode === 'physical'">
            <div class="legend-section">{{ t('topology.equipmentTypes') }}</div>
            <div v-for="legendItem in uniqueEquipmentTypes" :key="legendItem.type" class="legend-item">
              <span class="legend-icon" :style="{ background: legendItem.color }">
                <i :class="formatIconClass(legendItem.icon)"></i>
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
          <span v-if="groups.length > 0"><strong>{{ groups.length }}</strong> Sites</span>
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
                <i :class="formatIconClass(selectedNode.icon)"></i>
              </div>
              <div>
                <div class="node-name">{{ selectedNode.label }}</div>
                <div class="node-type">{{ selectedNode.sublabel || selectedNode.type }}</div>
              </div>
            </div>

            <div class="node-props">
              <template v-for="(value, key) in getDisplayProps(selectedNode.data)" :key="key">
                <div class="prop-row">
                  <span>{{ formatKey(key) }}</span>
                  <span>{{ value }}</span>
                </div>
              </template>
            </div>

            <!-- Connected Equipment -->
            <div v-if="selectedNode.type === 'equipment' && getConnectedNodes(selectedNode.id).length > 0" class="connected-section">
              <div class="connected-title">{{ t('topology.connectedTo') }}</div>
              <div v-for="conn in getConnectedNodes(selectedNode.id)" :key="conn.id" class="connected-item" @click="selectNodeById(conn.id)">
                <i :class="formatIconClass(conn.icon)" :style="{ color: conn.color }"></i>
                <span>{{ conn.label }}</span>
                <Button icon="pi pi-trash" text severity="danger" size="small"
                  @click.stop="confirmDeleteLink(selectedNode, conn)"
                  v-tooltip.top="t('topology.deleteLink')" />
              </div>
            </div>

            <div class="node-actions">
              <Button v-if="selectedNode.type === 'equipment'" :label="t('topology.viewInventory')" icon="pi pi-box"
                size="small" outlined @click="goToEquipment" />
              <Button v-if="selectedNode.type === 'equipment'" icon="pi pi-link" size="small" outlined
                @click="startLinkFrom(selectedNode)" v-tooltip.top="t('topology.createLink')" />
            </div>
          </div>

          <div v-else class="no-selection">
            <i class="pi pi-hand-pointer"></i>
            <p>{{ t('topology.selectNodeHint') }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Link Confirmation Dialog -->
    <Dialog v-model:visible="showDeleteDialog" :header="t('topology.deleteLink')" modal :style="{ width: '400px' }">
      <p>{{ t('topology.confirmDeleteLink', { source: deleteLinkData?.source?.label, target: deleteLinkData?.target?.label }) }}</p>
      <template #footer>
        <Button :label="t('common.cancel')" text @click="showDeleteDialog = false" />
        <Button :label="t('common.delete')" severity="danger" @click="deleteLink" :loading="deletingLink" />
      </template>
    </Dialog>

    <!-- Create Link Dialog -->
    <Dialog v-model:visible="showCreateLinkDialog" :header="t('topology.createLink')" modal :style="{ width: '450px' }">
      <div class="create-link-content">
        <div class="link-preview">
          <div class="link-node">
            <i :class="formatIconClass(createLinkData?.source?.icon)" :style="{ color: createLinkData?.source?.color }"></i>
            <span>{{ createLinkData?.source?.label }}</span>
          </div>
          <i class="pi pi-arrow-right link-arrow"></i>
          <div class="link-node">
            <i :class="formatIconClass(createLinkData?.target?.icon)" :style="{ color: createLinkData?.target?.color }"></i>
            <span>{{ createLinkData?.target?.label }}</span>
          </div>
        </div>

        <div class="link-form">
          <div class="form-field">
            <label>{{ t('topology.linkSpeed') }}</label>
            <Dropdown v-model="newLinkSpeed" :options="speedOptions" optionLabel="label" optionValue="value"
              :placeholder="t('topology.selectSpeed')" class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('topology.linkType') }}</label>
            <Dropdown v-model="newLinkType" :options="typeOptions" optionLabel="label" optionValue="value"
              :placeholder="t('topology.selectType')" class="w-full" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button :label="t('common.cancel')" text @click="cancelCreateLink" />
        <Button :label="t('common.create')" severity="primary" @click="createLink" :loading="creatingLink" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { Network } from 'vis-network';
import api from '../api';

const { t } = useI18n();
const router = useRouter();
const toast = useToast();

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

// Link creation state
const linkMode = ref(false);
const linkSource = ref(null);
const showCreateLinkDialog = ref(false);
const createLinkData = ref(null);
const newLinkSpeed = ref('1G');
const newLinkType = ref('ethernet');
const creatingLink = ref(false);

// Delete link state
const showDeleteDialog = ref(false);
const deleteLinkData = ref(null);
const deletingLink = ref(false);

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

const speedOptions = [
  { label: '100 Mbps', value: '100M' },
  { label: '1 Gbps', value: '1G' },
  { label: '10 Gbps', value: '10G' },
  { label: '25 Gbps', value: '25G' },
  { label: '40 Gbps', value: '40G' },
  { label: '100 Gbps', value: '100G' }
];

const typeOptions = computed(() => [
  { label: t('topology.ethernet') + ' (' + t('topology.copper') + ')', value: 'ethernet' },
  { label: t('topology.fiber'), value: 'fiber' },
  { label: t('topology.sfp'), value: 'sfp' }
]);

// Format icon class - ensure it has 'pi ' prefix
const formatIconClass = (icon) => {
  if (!icon) return 'pi pi-box';
  if (icon.startsWith('pi ')) return icon;
  if (icon.startsWith('pi-')) return 'pi ' + icon;
  return 'pi pi-' + icon;
};

// Get unique equipment types for legend
const uniqueEquipmentTypes = computed(() => {
  const types = new Map();
  nodes.value.forEach(node => {
    if (node.type === 'equipment' && node.sublabel) {
      if (!types.has(node.sublabel)) {
        types.set(node.sublabel, {
          type: node.sublabel,
          icon: node.icon || 'pi-box',
          color: node.color
        });
      }
    }
  });
  return Array.from(types.values());
});

// Get connected nodes for a given node ID
const getConnectedNodes = (nodeId) => {
  const connectedIds = new Set();
  edges.value.forEach(edge => {
    if (edge.source === nodeId) connectedIds.add(edge.target);
    if (edge.target === nodeId) connectedIds.add(edge.source);
  });
  return nodes.value.filter(n => connectedIds.has(n.id));
};

// Select a node by ID
const selectNodeById = (nodeId) => {
  const node = nodes.value.find(n => n.id === nodeId);
  if (node) {
    selectedNode.value = node;
    network?.selectNodes([nodeId]);
    network?.focus(nodeId, { animation: { duration: 300 }, scale: 1 });
  }
};

// Filter display props
const getDisplayProps = (data) => {
  if (!data) return {};
  const displayKeys = ['status', 'type', 'site', 'room', 'rack', 'ip_address', 'manufacturer', 'model', 'ports_connected', 'ports_total'];
  const result = {};
  displayKeys.forEach(key => {
    if (data[key] != null && data[key] !== '') {
      result[key] = data[key];
    }
  });
  return result;
};

// SVG icon paths for vis-network nodes
const iconSvgPaths = {
  'server': 'M4 6h16v4H4zm0 8h16v4H4zm2-6h2v2H6zm0 8h2v2H6z',
  'desktop': 'M4 4h16v12H4zm4 14h8v2H8z',
  'database': 'M12 2C6.48 2 2 4.02 2 6.5v11C2 19.98 6.48 22 12 22s10-2.02 10-4.5v-11C22 4.02 17.52 2 12 2zm0 2c4.42 0 8 1.79 8 4s-3.58 4-8 4-8-1.79-8-4 3.58-4 8-4z',
  'wifi': 'M12 18c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm-4.24-4.24l1.41 1.41c1.52-1.52 4.14-1.52 5.66 0l1.41-1.41c-2.34-2.34-6.14-2.34-8.48 0zM4.93 10.93l1.41 1.41c3.12-3.12 8.2-3.12 11.32 0l1.41-1.41c-3.9-3.9-10.24-3.9-14.14 0z',
  'shield': 'M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z',
  'box': 'M21 16.5c0 .38-.21.71-.53.88l-7.9 4.44c-.16.12-.36.18-.57.18s-.41-.06-.57-.18l-7.9-4.44A.991.991 0 013 16.5v-9c0-.38.21-.71.53-.88l7.9-4.44c.16-.12.36-.18.57-.18s.41.06.57.18l7.9 4.44c.32.17.53.5.53.88v9z',
  'sitemap': 'M22 11V3h-7v3H9V3H2v8h7V8h2v10h4v3h7v-8h-7v3h-2V8h2v3h7z',
  'bolt': 'M11 21h-1l1-7H7.5c-.58 0-.57-.32-.38-.66C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51C12.96 17.55 11 21 11 21z',
  'globe': 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z',
  'print': 'M19 8H5c-1.66 0-3 1.34-3 3v6h4v4h12v-4h4v-6c0-1.66-1.34-3-3-3zm-3 11H8v-5h8v5zm3-7c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z',
  'mobile': 'M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z',
  'cog': 'M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z'
};

// Create SVG data URL for an icon - improved with shadow and better visibility
const createIconSvg = (iconClass, color) => {
  const iconName = iconClass.replace(/^pi[- ]?/, '').replace('pi-', '');
  const path = iconSvgPaths[iconName] || iconSvgPaths['box'];

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 56 56" width="56" height="56">
    <defs>
      <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.3"/>
      </filter>
      <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style="stop-color:${color};stop-opacity:1"/>
        <stop offset="100%" style="stop-color:${adjustColor(color, -20)};stop-opacity:1"/>
      </linearGradient>
    </defs>
    <circle cx="28" cy="28" r="24" fill="url(#grad)" stroke="white" stroke-width="2.5" filter="url(#shadow)"/>
    <g transform="translate(14, 14) scale(1.17)">
      <path d="${path}" fill="white" fill-opacity="0.95"/>
    </g>
  </svg>`;

  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
};

// Helper function to darken/lighten a color
const adjustColor = (color, amount) => {
  const clamp = (val) => Math.min(255, Math.max(0, val));
  let hex = color.replace('#', '');
  if (hex.length === 3) {
    hex = hex.split('').map(c => c + c).join('');
  }
  const r = clamp(parseInt(hex.slice(0, 2), 16) + amount);
  const g = clamp(parseInt(hex.slice(2, 4), 16) + amount);
  const b = clamp(parseInt(hex.slice(4, 6), 16) + amount);
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
};

const loadTopology = async () => {
  loading.value = true;
  selectedNode.value = null;
  linkMode.value = false;
  linkSource.value = null;

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

// Get hierarchy level from API data (configured in equipment type settings)
const getHierarchyLevel = (node) => {
  // Use the level directly from API if available
  if (typeof node.level === 'number') return node.level;
  // Fallback to data.hierarchy_level if present
  if (node.data?.hierarchy_level !== undefined) return node.data.hierarchy_level;
  // Default to level 3 (middle) for non-equipment nodes
  return 3;
};

const renderNetwork = () => {
  if (!networkContainer.value || nodes.value.length === 0) return;

  // Detect dark mode for proper text styling
  const isDark = document.documentElement.classList.contains('dark');
  const labelColor = isDark ? '#f1f5f9' : '#1e293b';
  const labelStrokeColor = isDark ? '#0f172a' : '#ffffff';

  // For physical topology, use hierarchical layout
  const isPhysical = viewMode.value === 'physical' || viewMode.value === 'combined';

  // Pre-calculate positions for hierarchical layout to avoid slow physics
  const levelNodes = {};
  nodes.value.forEach(node => {
    const level = getHierarchyLevel(node);
    if (!levelNodes[level]) levelNodes[level] = [];
    levelNodes[level].push(node);
  });

  const sortedLevels = Object.keys(levelNodes).map(Number).sort((a, b) => a - b);
  const levelSpacing = 150; // Vertical spacing between levels
  const nodeSpacing = 200;  // Horizontal spacing between nodes

  const visNodes = nodes.value.map((node) => {
    const isEquipment = node.type === 'equipment';
    const level = getHierarchyLevel(node);

    // Calculate fixed position for hierarchical layout
    let x, y;
    if (isPhysical) {
      const levelIndex = sortedLevels.indexOf(level);
      const nodesInLevel = levelNodes[level];
      const nodeIndex = nodesInLevel.indexOf(node);
      const levelWidth = nodesInLevel.length * nodeSpacing;

      x = (nodeIndex * nodeSpacing) - (levelWidth / 2) + (nodeSpacing / 2);
      y = levelIndex * levelSpacing;
    }

    if (isEquipment) {
      const iconClass = node.icon || 'pi-box';
      return {
        id: node.id,
        label: node.label,
        title: createTooltip(node),
        group: node.group,
        level: level,
        x: isPhysical ? x : undefined,
        y: isPhysical ? y : undefined,
        fixed: isPhysical ? { x: false, y: false } : undefined,
        shape: 'image',
        image: createIconSvg(iconClass, node.color),
        size: 30,
        font: {
          color: labelColor,
          size: 13,
          face: 'Inter, system-ui, sans-serif',
          strokeWidth: 4,
          strokeColor: labelStrokeColor,
          vadjust: 10,
          bold: true
        },
        _data: node
      };
    } else {
      return {
        id: node.id,
        label: node.label,
        title: createTooltip(node),
        group: node.group,
        level: level,
        x: isPhysical ? x : undefined,
        y: isPhysical ? y : undefined,
        color: {
          background: node.color + '30',
          border: node.color,
          highlight: { background: node.color + '50', border: node.color },
          hover: { background: node.color + '40', border: node.color }
        },
        font: {
          color: labelColor,
          size: 12,
          strokeWidth: 3,
          strokeColor: labelStrokeColor
        },
        borderWidth: 2,
        shape: node.shape || 'dot',
        size: node.size || 18,
        _data: node
      };
    }
  });

  // Edge colors adapted to theme
  const edgeColor = isDark ? '#475569' : '#94a3b8';
  const edgeHoverColor = isDark ? '#60a5fa' : '#3b82f6';

  const visEdges = edges.value.map(edge => {
    const sourceNode = nodes.value.find(n => n.id === edge.source);
    const targetNode = nodes.value.find(n => n.id === edge.target);
    const tooltipText = sourceNode && targetNode
      ? `${sourceNode.label} ↔ ${targetNode.label}${edge.label ? '\n' + edge.label : ''}\n${t('topology.clickToDelete')}`
      : '';

    // Determine edge width based on speed
    let width = 2;
    if (edge.label) {
      if (edge.label.includes('10G') || edge.label.includes('25G') || edge.label.includes('40G') || edge.label.includes('100G')) {
        width = 4;
      } else if (edge.label.includes('1G')) {
        width = 2.5;
      }
    }

    return {
      id: edge.id,
      from: edge.source,
      to: edge.target,
      label: edge.label || '',
      title: tooltipText,
      color: {
        color: edge.color || edgeColor,
        highlight: '#ef4444',
        hover: edgeHoverColor,
        opacity: 0.9
      },
      width: edge.width || width,
      dashes: edge.dashes || false,
      hoverWidth: 1.5,
      selectionWidth: 2,
      chosen: {
        edge: (values) => {
          values.width = values.width * 1.5;
          values.color = '#ef4444';
        }
      }
    };
  });

  const options = {
    nodes: {
      font: {
        face: 'Inter, system-ui, sans-serif',
        size: 13,
        strokeWidth: 4,
        strokeColor: labelStrokeColor,
        color: labelColor
      },
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.15)',
        size: 8,
        x: 0,
        y: 3
      }
    },
    edges: {
      smooth: isPhysical
        ? { type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.4 }
        : { type: 'dynamic', roundness: 0.5 },
      arrows: { to: { enabled: false } },
      font: {
        size: 10,
        color: labelColor,
        strokeWidth: 3,
        strokeColor: labelStrokeColor,
        align: 'middle',
        background: isDark ? 'rgba(15, 23, 42, 0.8)' : 'rgba(255, 255, 255, 0.8)'
      },
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.1)',
        size: 4,
        x: 0,
        y: 2
      }
    },
    physics: isPhysical ? {
      // Minimal physics for hierarchical - just prevent overlap
      enabled: true,
      solver: 'repulsion',
      repulsion: {
        centralGravity: 0.0,
        springLength: 200,
        springConstant: 0.05,
        nodeDistance: 150,
        damping: 0.9
      },
      stabilization: {
        enabled: true,
        iterations: 50,
        updateInterval: 10,
        fit: true
      },
      maxVelocity: 50,
      minVelocity: 0.75,
      timestep: 0.5
    } : {
      // Logical view - force-directed with fast stabilization
      enabled: true,
      solver: 'barnesHut',
      barnesHut: {
        gravitationalConstant: -3000,
        centralGravity: 0.3,
        springLength: 150,
        springConstant: 0.04,
        damping: 0.9,
        avoidOverlap: 0.5
      },
      stabilization: {
        enabled: true,
        iterations: 100,
        updateInterval: 10,
        fit: true
      },
      maxVelocity: 50,
      minVelocity: 0.75,
      timestep: 0.5
    },
    interaction: {
      hover: true,
      tooltipDelay: 100,
      dragNodes: true,
      dragView: true,
      zoomView: true,
      hideEdgesOnDrag: false,
      hideEdgesOnZoom: false,
      selectConnectedEdges: true,
      multiselect: false,
      selectable: true,
      navigationButtons: false,
      keyboard: {
        enabled: true,
        speed: { x: 10, y: 10, zoom: 0.05 }
      }
    },
    layout: isPhysical ? {
      hierarchical: {
        enabled: true,
        direction: 'UD',
        sortMethod: 'directed',
        levelSeparation: levelSpacing,
        nodeSpacing: nodeSpacing,
        treeSpacing: 250,
        blockShifting: true,
        edgeMinimization: true,
        parentCentralization: true,
        shakeTowards: 'roots'
      }
    } : {
      improvedLayout: true,
      clusterThreshold: 150,
      randomSeed: 42
    }
  };

  if (network) network.destroy();

  network = new Network(networkContainer.value, { nodes: visNodes, edges: visEdges }, options);

  network.on('click', params => {
    if (linkMode.value && params.nodes.length > 0) {
      handleLinkModeClick(params.nodes[0]);
    } else if (params.nodes.length > 0) {
      const node = nodes.value.find(n => n.id === params.nodes[0]);
      selectedNode.value = node || null;
    } else if (params.edges.length > 0) {
      // Edge clicked - prompt for deletion
      const edgeId = params.edges[0];
      const edge = edges.value.find(e => e.id === edgeId);
      if (edge) {
        const sourceNode = nodes.value.find(n => n.id === edge.source);
        const targetNode = nodes.value.find(n => n.id === edge.target);
        if (sourceNode && targetNode) {
          confirmDeleteLink(sourceNode, targetNode);
        }
      }
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
    }
  });

  // Handle stabilization completion
  network.once('stabilizationIterationsDone', () => {
    // Disable physics after stabilization for better performance
    network.setOptions({ physics: { enabled: false } });
    network.fit({ animation: { duration: 300, easingFunction: 'easeInOutQuad' } });
    setTimeout(() => {
      zoomLevel.value = network.getScale();
    }, 350);
  });

  // Show stabilization progress (optional visual feedback)
  network.on('stabilizationProgress', (params) => {
    const progress = Math.round((params.iterations / params.total) * 100);
    if (progress % 25 === 0) {
      console.debug(`Topology stabilization: ${progress}%`);
    }
  });

  // Change cursor to pointer when hovering over edges
  network.on('hoverEdge', () => {
    networkContainer.value.style.cursor = 'pointer';
  });

  network.on('blurEdge', () => {
    networkContainer.value.style.cursor = 'default';
  });

  // Re-enable physics temporarily when dragging nodes for better repositioning
  network.on('dragStart', () => {
    network.setOptions({
      physics: {
        enabled: true,
        solver: 'repulsion',
        repulsion: {
          centralGravity: 0.0,
          springLength: 200,
          springConstant: 0.05,
          nodeDistance: 150,
          damping: 0.9
        }
      }
    });
  });

  // Disable physics after drag ends and stabilize
  network.on('dragEnd', () => {
    setTimeout(() => {
      network.setOptions({ physics: { enabled: false } });
    }, 500);
  });
};

// Link mode functions
const toggleLinkMode = () => {
  linkMode.value = !linkMode.value;
  linkSource.value = null;
  if (!linkMode.value) {
    selectedNode.value = null;
  }
};

const startLinkFrom = (node) => {
  linkMode.value = true;
  linkSource.value = node;
};

const handleLinkModeClick = (nodeId) => {
  const clickedNode = nodes.value.find(n => n.id === nodeId);
  if (!clickedNode || clickedNode.type !== 'equipment') return;

  if (!linkSource.value) {
    linkSource.value = clickedNode;
  } else if (linkSource.value.id !== clickedNode.id) {
    // Check if link already exists
    const existingLink = edges.value.find(e =>
      (e.source === linkSource.value.id && e.target === clickedNode.id) ||
      (e.target === linkSource.value.id && e.source === clickedNode.id)
    );

    if (existingLink) {
      toast.add({ severity: 'warn', summary: t('topology.linkExists'), life: 3000 });
      return;
    }

    createLinkData.value = { source: linkSource.value, target: clickedNode };
    showCreateLinkDialog.value = true;
  }
};

const cancelCreateLink = () => {
  showCreateLinkDialog.value = false;
  createLinkData.value = null;
  linkMode.value = false;
  linkSource.value = null;
};

const createLink = async () => {
  if (!createLinkData.value) return;

  creatingLink.value = true;
  try {
    await api.post('/topology/link', {
      source_equipment_id: createLinkData.value.source.data.id,
      target_equipment_id: createLinkData.value.target.data.id,
      speed: newLinkSpeed.value,
      port_type: newLinkType.value
    });

    toast.add({ severity: 'success', summary: t('topology.linkCreated'), life: 3000 });
    showCreateLinkDialog.value = false;
    createLinkData.value = null;
    linkMode.value = false;
    linkSource.value = null;
    newLinkSpeed.value = '1G';
    newLinkType.value = 'ethernet';

    await loadTopology();
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: error.response?.data?.detail || error.message, life: 5000 });
  } finally {
    creatingLink.value = false;
  }
};

const confirmDeleteLink = (source, target) => {
  deleteLinkData.value = { source, target };
  showDeleteDialog.value = true;
};

const deleteLink = async () => {
  if (!deleteLinkData.value) return;

  deletingLink.value = true;
  try {
    await api.delete('/topology/link', {
      data: {
        source_equipment_id: deleteLinkData.value.source.data.id,
        target_equipment_id: deleteLinkData.value.target.data.id
      }
    });

    toast.add({ severity: 'success', summary: t('topology.linkDeleted'), life: 3000 });
    showDeleteDialog.value = false;
    deleteLinkData.value = null;

    await loadTopology();
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: error.response?.data?.detail || error.message, life: 5000 });
  } finally {
    deletingLink.value = false;
  }
};

const createTooltip = (node) => {
  let html = `<div style="padding:10px 14px;max-width:260px;">`;
  html += `<div style="font-weight:600;font-size:13px;margin-bottom:4px;">${node.label}</div>`;
  if (node.sublabel) html += `<div style="color:#64748b;font-size:11px;margin-bottom:8px;">${node.sublabel}</div>`;
  if (node.data) {
    const displayKeys = ['status', 'site', 'room', 'rack', 'ip_address'];
    displayKeys.forEach(key => {
      if (node.data[key]) html += `<div style="font-size:11px;color:#64748b;"><span style="color:#94a3b8;">${formatKey(key)}:</span> ${node.data[key]}</div>`;
    });
  }
  return html + '</div>';
};

const formatKey = (key) => key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

const zoomIn = () => {
  if (!network) return;
  const newScale = network.getScale() * 1.25;
  network.moveTo({ scale: newScale, animation: { duration: 150 } });
  zoomLevel.value = newScale;
};

const zoomOut = () => {
  if (!network) return;
  const newScale = network.getScale() / 1.25;
  network.moveTo({ scale: newScale, animation: { duration: 150 } });
  zoomLevel.value = newScale;
};

const fitToScreen = () => {
  if (!network) return;
  network.fit({ animation: { duration: 300 } });
  // Update zoom level after animation completes
  setTimeout(() => {
    zoomLevel.value = network.getScale();
  }, 350);
};

const goToEquipment = (id) => {
  const eqId = id || selectedNode.value?.data?.id;
  if (eqId) router.push({ path: '/inventory', query: { equipment: eqId } });
};

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
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-card) 100%);
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 500px;
  position: relative;
  transition: box-shadow 0.2s, border-color 0.2s;
  border: 1px solid var(--border-color);
}

.graph-container.link-mode-active {
  box-shadow: inset 0 0 0 2px var(--primary-color), 0 0 20px rgba(14, 165, 233, 0.15);
  border-color: var(--primary-color);
}

.network-canvas {
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at 50% 50%, transparent 0%, var(--bg-secondary) 100%);
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
  backdrop-filter: blur(4px);
}

.empty-state h3 { font-size: 1rem; font-weight: 600; color: var(--text-main); margin: 0; }
.empty-state p { font-size: 0.8125rem; max-width: 280px; text-align: center; margin: 0; }

.link-mode-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: var(--primary-color);
  color: white;
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
}

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
  border-radius: 50%;
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

.connected-section {
  padding-top: 0.625rem;
  border-top: 1px solid var(--border-color);
}

.connected-title {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.connected-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  margin: 0.25rem 0;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.75rem;
  transition: background 0.15s;
}

.connected-item:hover {
  background: var(--bg-hover);
}

.connected-item span {
  flex: 1;
  color: var(--text-main);
}

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

/* Create Link Dialog */
.create-link-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.link-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.link-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.link-node i {
  font-size: 1.5rem;
}

.link-node span {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-main);
}

.link-arrow {
  color: var(--text-muted);
  font-size: 1.25rem;
}

.link-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-field label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
}
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
