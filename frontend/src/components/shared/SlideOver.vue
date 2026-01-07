<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <Transition name="fade">
      <div
        v-if="modelValue"
        class="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
        @click="$emit('update:modelValue', false)"
      ></div>
    </Transition>

    <!-- Panel -->
    <Transition name="slide">
      <div
        v-if="modelValue"
        :class="[
          'fixed top-0 bottom-0 z-50 flex flex-col shadow-2xl',
          sizeClass,
          position === 'right' ? 'right-0' : 'left-0'
        ]"
        style="background-color: var(--bg-card);"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b" style="border-color: var(--border-color);">
          <div class="flex items-center gap-3 min-w-0">
            <i v-if="icon" :class="['pi', icon, 'text-xl text-blue-500']"></i>
            <div class="min-w-0">
              <h2 class="text-lg font-semibold truncate">{{ title }}</h2>
              <p v-if="subtitle" class="text-sm opacity-60 truncate">{{ subtitle }}</p>
            </div>
          </div>
          <Button
            icon="pi pi-times"
            text
            rounded
            @click="$emit('update:modelValue', false)"
            v-tooltip.left="'Close'"
          />
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto p-6">
          <slot></slot>
        </div>

        <!-- Footer -->
        <div v-if="$slots.footer" class="px-6 py-4 border-t" style="border-color: var(--border-color);">
          <slot name="footer"></slot>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  title: {
    type: String,
    default: ''
  },
  subtitle: {
    type: String,
    default: ''
  },
  icon: {
    type: String,
    default: ''
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg', 'xl', 'full'].includes(v)
  },
  position: {
    type: String,
    default: 'right',
    validator: (v) => ['left', 'right'].includes(v)
  }
})

defineEmits(['update:modelValue'])

const sizeClass = computed(() => {
  const sizes = {
    sm: 'w-80',
    md: 'w-96',
    lg: 'w-[32rem]',
    xl: 'w-[40rem]',
    full: 'w-full max-w-3xl'
  }
  return sizes[props.size] || sizes.md
})

// Lock body scroll when open
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

[data-position="left"] .slide-enter-from,
[data-position="left"] .slide-leave-to {
  transform: translateX(-100%);
}
</style>
