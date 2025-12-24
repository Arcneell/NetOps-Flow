<template>
  <Tag
    :value="labelWithIcon"
    :severity="severity"
    :class="['status-tag', `status-${status}`]"
  >
    <template #default>
      <div class="flex items-center gap-1.5">
        <i :class="icon" class="text-xs"></i>
        <span>{{ label }}</span>
      </div>
    </template>
  </Tag>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import Tag from 'primevue/tag';

const { t } = useI18n();

const props = defineProps({
  status: {
    type: String,
    required: true
  },
  type: {
    type: String,
    default: 'equipment' // equipment, contract, license, etc.
  }
});

const statusConfig = {
  equipment: {
    in_service: {
      label: t('status.inService'),
      severity: 'success',
      icon: 'pi pi-check-circle'
    },
    in_stock: {
      label: t('status.inStock'),
      severity: 'info',
      icon: 'pi pi-inbox'
    },
    retired: {
      label: t('status.retired'),
      severity: 'secondary',
      icon: 'pi pi-ban'
    },
    maintenance: {
      label: t('status.maintenance'),
      severity: 'warning',
      icon: 'pi pi-wrench'
    }
  },
  contract: {
    active: {
      label: t('status.active'),
      severity: 'success',
      icon: 'pi pi-check-circle'
    },
    expiring_soon: {
      label: t('status.expiringSoon'),
      severity: 'warning',
      icon: 'pi pi-exclamation-triangle'
    },
    expired: {
      label: t('status.expired'),
      severity: 'danger',
      icon: 'pi pi-times-circle'
    },
    renewed: {
      label: t('status.renewed'),
      severity: 'info',
      icon: 'pi pi-refresh'
    }
  },
  license: {
    compliant: {
      label: t('status.compliant'),
      severity: 'success',
      icon: 'pi pi-shield'
    },
    violation: {
      label: t('status.violation'),
      severity: 'danger',
      icon: 'pi pi-exclamation-circle'
    },
    expiring_soon: {
      label: t('status.expiringSoon'),
      severity: 'warning',
      icon: 'pi pi-clock'
    }
  }
};

const config = computed(() => {
  return statusConfig[props.type]?.[props.status] || {
    label: props.status,
    severity: 'secondary',
    icon: 'pi pi-circle'
  };
});

const label = computed(() => config.value.label);
const severity = computed(() => config.value.severity);
const icon = computed(() => config.value.icon);
const labelWithIcon = computed(() => `${label.value}`);
</script>

<style scoped>
.status-tag {
  font-weight: 500;
  font-size: 0.8125rem;
  padding: 0.375rem 0.75rem;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  transition: all 0.2s ease;
}

.status-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Custom status colors using Modern Slate palette */
.status-in_service {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 0 1px 3px rgba(16, 185, 129, 0.3);
}

.status-in_stock {
  background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
  color: white;
  box-shadow: 0 1px 3px rgba(14, 165, 233, 0.3);
}

.status-retired {
  background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
  color: white;
  box-shadow: 0 1px 3px rgba(107, 114, 128, 0.3);
}

.status-maintenance {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  box-shadow: 0 1px 3px rgba(245, 158, 11, 0.3);
}

.status-active,
.status-compliant {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 0 1px 3px rgba(16, 185, 129, 0.3);
}

.status-expiring_soon {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  box-shadow: 0 1px 3px rgba(245, 158, 11, 0.3);
}

.status-expired,
.status-violation {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  box-shadow: 0 1px 3px rgba(239, 68, 68, 0.3);
}

.status-renewed {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  color: white;
  box-shadow: 0 1px 3px rgba(139, 92, 246, 0.3);
}
</style>
