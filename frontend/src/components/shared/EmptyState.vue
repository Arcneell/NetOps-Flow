<template>
  <div class="empty-state flex flex-col items-center justify-center py-12 px-4 text-center">
    <!-- Icon -->
    <div
      class="icon-container w-20 h-20 rounded-full flex items-center justify-center mb-6"
      :class="iconBgClass"
    >
      <i :class="['pi', icon, 'text-3xl', iconColorClass]"></i>
    </div>

    <!-- Title -->
    <h3 class="text-xl font-semibold mb-2">{{ title }}</h3>

    <!-- Description -->
    <p class="text-sm opacity-60 max-w-md mb-6">{{ description }}</p>

    <!-- Action Button -->
    <Button
      v-if="actionLabel"
      :label="actionLabel"
      :icon="actionIcon"
      @click="$emit('action')"
      class="action-button"
    />

    <!-- Secondary Actions -->
    <div v-if="$slots.default" class="mt-4">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: {
    type: String,
    default: 'pi-inbox'
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  actionLabel: {
    type: String,
    default: ''
  },
  actionIcon: {
    type: String,
    default: 'pi-plus'
  },
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'info', 'warning', 'error'].includes(v)
  }
})

defineEmits(['action'])

const iconBgClass = computed(() => {
  switch (props.variant) {
    case 'info':
      return 'bg-blue-100 dark:bg-blue-900/30'
    case 'warning':
      return 'bg-yellow-100 dark:bg-yellow-900/30'
    case 'error':
      return 'bg-red-100 dark:bg-red-900/30'
    default:
      return 'bg-gray-100 dark:bg-gray-800'
  }
})

const iconColorClass = computed(() => {
  switch (props.variant) {
    case 'info':
      return 'text-blue-500'
    case 'warning':
      return 'text-yellow-500'
    case 'error':
      return 'text-red-500'
    default:
      return 'opacity-50'
  }
})
</script>

<style scoped>
.empty-state {
  min-height: 300px;
}

.icon-container {
  animation: pulse-slow 3s ease-in-out infinite;
}

@keyframes pulse-slow {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.05);
  }
}

.action-button {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.action-button:hover {
  transform: translateY(-1px);
}
</style>
