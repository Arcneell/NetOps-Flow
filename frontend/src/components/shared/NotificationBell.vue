<template>
  <div class="notification-bell-wrapper">
    <Button icon="pi pi-bell" text rounded class="header-icon-btn"
            @click="togglePanel" v-badge.danger="unreadCount || null" />

    <!-- Backdrop (must be before panel for correct stacking) -->
    <Teleport to="body">
      <div v-if="showPanel" class="notification-backdrop" @click="showPanel = false"></div>
    </Teleport>

    <!-- Notification Panel -->
    <Teleport to="body">
      <transition name="notification-slide">
        <div v-if="showPanel" class="notification-panel">
          <div class="notification-header">
            <h3 class="font-semibold">{{ t('notifications.title') }}</h3>
            <Button v-if="notifications.length" :label="t('notifications.markAllRead')" text size="small"
                    class="!text-xs" @click="markAllRead" />
          </div>

          <div class="notification-list custom-scrollbar">
            <div v-for="notification in notifications" :key="notification.id"
                 class="notification-item"
                 :class="{ 'unread': !notification.is_read }"
                 @click="handleNotificationClick(notification)">
              <div class="flex items-start gap-3">
                <i :class="getNotificationIcon(notification)" class="text-lg mt-1"></i>
                <div class="flex-1 min-w-0">
                  <div class="font-medium text-sm">{{ notification.title }}</div>
                  <div class="text-xs opacity-70 mt-1 line-clamp-2">{{ notification.message }}</div>
                  <div class="text-xs opacity-50 mt-1">{{ formatTime(notification.created_at) }}</div>
                </div>
                <Button v-if="!notification.is_read" icon="pi pi-circle-fill" text rounded size="small"
                        class="!text-sky-500 !w-6 !h-6" @click.stop="markAsRead(notification.id)" />
              </div>
            </div>

            <div v-if="!notifications.length" class="notification-empty">
              <i class="pi pi-bell-slash text-3xl mb-2"></i>
              <p>{{ t('notifications.noNotifications') }}</p>
            </div>
          </div>

          <div v-if="notifications.length" class="notification-footer">
            <Button :label="t('notifications.deleteRead')" text size="small" class="!text-xs" @click="deleteRead" />
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useNotificationsStore } from '../../stores/notifications';

const { t } = useI18n();
const router = useRouter();
const notificationsStore = useNotificationsStore();

const showPanel = ref(false);

const notifications = computed(() => notificationsStore.notifications);
const unreadCount = computed(() => notificationsStore.count.unread);

const togglePanel = async () => {
  showPanel.value = !showPanel.value;
  if (showPanel.value) {
    await notificationsStore.fetchNotifications();
  }
};

const formatTime = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = (now - date) / 1000;

  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return date.toLocaleDateString();
};

const getNotificationIcon = (notification) => {
  switch (notification.notification_type) {
    case 'ticket': return 'pi pi-ticket text-sky-500';
    case 'success': return 'pi pi-check-circle text-green-500';
    case 'warning': return 'pi pi-exclamation-triangle text-yellow-500';
    case 'error': return 'pi pi-times-circle text-red-500';
    default: return 'pi pi-info-circle text-blue-500';
  }
};

const handleNotificationClick = async (notification) => {
  await notificationsStore.markAsRead(notification.id);
  showPanel.value = false;

  const link = notificationsStore.getNotificationLink(notification);
  if (link) {
    router.push(link);
  }
};

const markAsRead = async (id) => {
  await notificationsStore.markAsRead(id);
};

const markAllRead = async () => {
  await notificationsStore.markAllAsRead();
};

const deleteRead = async () => {
  await notificationsStore.deleteAllRead();
};

onMounted(() => {
  notificationsStore.startPolling(30000);
});

onUnmounted(() => {
  notificationsStore.stopPolling();
});
</script>

<style scoped>
.notification-bell-wrapper {
  position: relative;
}

.header-icon-btn {
  width: 2.25rem;
  height: 2.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.header-icon-btn:hover {
  background: var(--bg-hover);
  color: var(--primary);
}
</style>

<style>
/* Global styles for teleported elements */
.notification-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9998;
  background: transparent;
}

.notification-panel {
  position: fixed;
  top: 4.5rem;
  right: 1.5rem;
  width: 22rem;
  max-height: calc(100vh - 6rem);
  background: var(--bg-card-solid);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl), 0 0 40px rgba(0, 0, 0, 0.15);
  z-index: 9999;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.notification-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.notification-list {
  flex: 1;
  overflow-y: auto;
  max-height: 24rem;
}

.notification-item {
  padding: 0.875rem 1.25rem;
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.notification-item:hover {
  background: var(--bg-hover);
}

.notification-item.unread {
  background: rgba(14, 165, 233, 0.08);
}

.notification-item:last-child {
  border-bottom: none;
}

.notification-empty {
  padding: 3rem 1.25rem;
  text-align: center;
  color: var(--text-muted);
}

.notification-footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--border-default);
  text-align: center;
  flex-shrink: 0;
  background: var(--bg-secondary);
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Animation */
.notification-slide-enter-active,
.notification-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.notification-slide-enter-from,
.notification-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}
</style>
