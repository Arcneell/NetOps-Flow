<template>
  <div class="flex flex-col h-full">
    <!-- Breadcrumbs -->
    <Breadcrumbs :items="breadcrumbItems" />

    <div class="flex gap-6 flex-1 overflow-hidden">
    <!-- Sidebar -->
    <div class="w-72 flex-shrink-0">
      <div class="card p-4 mb-4">
        <h3 class="font-bold text-lg mb-4">{{ t('knowledge.title') }}</h3>

        <!-- Search -->
        <div class="mb-4">
          <span class="p-input-icon-left w-full">
            <i class="pi pi-search" />
            <InputText v-model="searchQuery" :placeholder="t('knowledge.searchArticles')" class="w-full"
                       @input="debouncedSearch" />
          </span>
        </div>

        <!-- Categories -->
        <div class="mb-4">
          <div class="flex justify-between items-center mb-2">
            <h4 class="text-sm font-semibold opacity-70">{{ t('knowledge.categories') }}</h4>
            <Button v-if="canManageKnowledge" icon="pi pi-cog" text rounded size="small"
                    v-tooltip="t('knowledge.manageCategories')" @click="showCategoryDialog = true" />
          </div>
          <div class="space-y-1">
            <div v-for="cat in categories" :key="cat.id"
                 class="p-2 rounded-lg cursor-pointer transition-all hover:translate-x-1 flex items-center gap-2"
                 :class="selectedCategoryId === cat.id ? 'bg-sky-500/20 text-sky-400' : 'hover:bg-white/5'"
                 @click="selectCategory(cat.id)">
              <i :class="cat.icon || 'pi pi-folder'" :style="{ color: cat.color }"></i>
              <span class="flex-1">{{ cat.name }}</span>
              <span class="text-xs opacity-50">({{ cat.article_count }})</span>
            </div>
            <div v-if="selectedCategoryId"
                 class="p-2 rounded-lg cursor-pointer text-sm opacity-50 hover:opacity-100"
                 @click="selectCategory(null)">
              {{ t('filters.allCategories') }}
            </div>
            <div v-if="categories.length === 0 && canManageKnowledge"
                 class="text-sm opacity-50 text-center py-2">
              {{ t('knowledge.noCategoriesYet') }}
            </div>
          </div>
        </div>

        <!-- Popular Articles -->
        <div v-if="popularArticles.length">
          <h4 class="text-sm font-semibold opacity-70 mb-2">{{ t('knowledge.popular') }}</h4>
          <div class="space-y-2">
            <div v-for="article in popularArticles" :key="article.id"
                 class="p-2 rounded-lg cursor-pointer hover:bg-white/5 transition-all"
                 @click="openArticle(article.slug)">
              <div class="text-sm font-medium truncate">{{ article.title }}</div>
              <div class="text-xs opacity-50">{{ article.view_count }} {{ t('common.views') }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Admin Actions -->
      <div v-if="canManageKnowledge" class="card p-4">
        <Button :label="t('knowledge.newArticle')" icon="pi pi-plus" class="w-full" @click="openArticleDialog()" />
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 overflow-hidden">
      <div v-if="!selectedArticle" class="card h-full flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ t('knowledge.articles') }}</h3>
          <div v-if="canManageKnowledge" class="flex items-center gap-2">
            <Checkbox v-model="showDrafts" :binary="true" inputId="showDrafts" />
            <label for="showDrafts" class="text-sm cursor-pointer">{{ t('knowledge.draft') }}</label>
          </div>
        </div>

        <div class="flex-1 overflow-auto">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div v-for="article in articles" :key="article.id"
                 class="p-4 rounded-xl cursor-pointer transition-all hover:translate-y-[-2px]"
                 style="background-color: var(--bg-app);"
                 @click="openArticle(article.slug)">
              <div class="flex items-start justify-between mb-2">
                <h4 class="font-semibold">{{ article.title }}</h4>
                <div class="flex gap-1">
                  <Tag v-if="!article.is_published" value="Draft" severity="warning" class="text-xs" />
                  <Tag v-if="article.is_internal" value="Internal" severity="secondary" class="text-xs" />
                </div>
              </div>
              <p v-if="article.summary" class="text-sm opacity-70 mb-3 line-clamp-2">{{ article.summary }}</p>
              <div class="flex justify-between items-center text-xs opacity-50">
                <span v-if="article.category_name || article.category" class="bg-white/10 px-2 py-1 rounded">{{ article.category_name || article.category }}</span>
                <span>{{ formatDate(article.created_at) }}</span>
              </div>
            </div>
          </div>

          <div v-if="!articles.length && !loadingArticles" class="text-center py-12 opacity-50">
            {{ t('common.noData') }}
          </div>

          <!-- Load more button -->
          <div v-if="hasMoreArticles" class="text-center py-4">
            <Button :label="t('common.loadMore')" icon="pi pi-chevron-down" :loading="loadingArticles" @click="loadMoreArticles" outlined />
          </div>

          <!-- Loading indicator -->
          <div v-if="loadingArticles && articles.length === 0" class="text-center py-12">
            <i class="pi pi-spin pi-spinner text-2xl"></i>
          </div>
        </div>
      </div>

      <!-- Article Detail View -->
      <div v-else class="card h-full flex flex-col overflow-hidden">
        <div class="flex items-center gap-4 mb-4">
          <Button icon="pi pi-arrow-left" text rounded @click="closeArticle" />
          <div class="flex-1">
            <h2 class="text-xl font-bold">{{ selectedArticle.title }}</h2>
            <div class="flex items-center gap-3 text-sm opacity-50 mt-1">
              <span>{{ selectedArticle.author_name || 'Unknown' }}</span>
              <span>•</span>
              <span>{{ formatDate(selectedArticle.created_at) }}</span>
              <span>•</span>
              <span>{{ selectedArticle.view_count }} views</span>
            </div>
          </div>
          <div v-if="canManageKnowledge" class="flex gap-2">
            <Button icon="pi pi-pencil" text rounded @click="openArticleDialog(selectedArticle)" />
            <Button v-if="!selectedArticle.is_published" icon="pi pi-check" text rounded severity="success"
                    v-tooltip="t('knowledge.publish')" @click="publishArticle(selectedArticle.id)" />
            <Button v-else icon="pi pi-eye-slash" text rounded severity="warning"
                    v-tooltip="t('knowledge.unpublish')" @click="unpublishArticle(selectedArticle.id)" />
            <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmDeleteArticle(selectedArticle)" />
          </div>
        </div>

        <div class="flex gap-2 mb-4">
          <Tag v-if="selectedArticle.category_name || selectedArticle.category" :value="selectedArticle.category_name || selectedArticle.category" />
          <Tag v-for="tag in selectedArticle.tags" :key="tag" :value="tag" severity="secondary" />
        </div>

        <div class="flex-1 overflow-auto prose prose-invert max-w-none">
          <div class="whitespace-pre-wrap">{{ selectedArticle.content }}</div>
        </div>

        <!-- Feedback -->
        <div class="border-t pt-4 mt-4" style="border-color: var(--border-color);">
          <div v-if="!feedbackSubmitted" class="flex items-center gap-4">
            <span class="text-sm opacity-70">{{ t('knowledge.wasHelpful') }}</span>
            <Button :label="t('knowledge.yes')" icon="pi pi-thumbs-up" size="small" outlined
                    @click="submitFeedback(true)" />
            <Button :label="t('knowledge.no')" icon="pi pi-thumbs-down" size="small" outlined severity="secondary"
                    @click="submitFeedback(false)" />
          </div>
          <div v-else class="text-sm text-green-400">
            <i class="pi pi-check mr-2"></i>{{ t('knowledge.feedbackThanks') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Article Dialog -->
    <Dialog v-model:visible="showArticleDialog" modal
            :header="editingArticle ? t('knowledge.editArticle') : t('knowledge.newArticle')"
            :style="{ width: '800px' }">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('knowledge.articleTitle') }} <span class="text-red-500">*</span></label>
          <InputText v-model="articleForm.title" class="w-full" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('knowledge.summary') }}</label>
          <InputText v-model="articleForm.summary" class="w-full" :placeholder="t('knowledge.summaryPlaceholder')" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('knowledge.category') }}</label>
            <Dropdown v-model="articleForm.category_id" :options="categoryOptions" optionLabel="name" optionValue="id" class="w-full" showClear :placeholder="t('knowledge.selectCategory')" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('knowledge.tags') }}</label>
            <Chips v-model="articleForm.tags" class="w-full" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('knowledge.content') }} <span class="text-red-500">*</span></label>
          <Textarea v-model="articleForm.content" rows="12" class="w-full font-mono" />
        </div>
        <div class="flex gap-4">
          <div class="flex items-center gap-2">
            <Checkbox v-model="articleForm.is_published" :binary="true" inputId="published" />
            <label for="published" class="cursor-pointer">{{ t('knowledge.published') }}</label>
          </div>
          <div class="flex items-center gap-2">
            <Checkbox v-model="articleForm.is_internal" :binary="true" inputId="internal" />
            <label for="internal" class="cursor-pointer">{{ t('knowledge.internal') }}</label>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <Button :label="t('common.cancel')" severity="secondary" outlined @click="showArticleDialog = false" />
          <Button :label="t('common.save')" icon="pi pi-check" @click="saveArticle" :loading="saving" />
        </div>
      </template>
    </Dialog>

    <!-- Category Management Dialog -->
    <Dialog v-model:visible="showCategoryDialog" modal :header="t('knowledge.manageCategories')" :style="{ width: '600px' }">
      <div class="space-y-4">
        <!-- Add new category form -->
        <div class="p-4 rounded-lg" style="background-color: var(--bg-app);">
          <h4 class="font-semibold mb-3">{{ editingCategory ? t('knowledge.editCategory') : t('knowledge.addCategory') }}</h4>
          <div class="grid grid-cols-2 gap-4 mb-3">
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('common.name') }} <span class="text-red-500">*</span></label>
              <InputText v-model="categoryForm.name" class="w-full" :placeholder="t('knowledge.categoryName')" />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('common.icon') }}</label>
              <div class="flex gap-2">
                <Dropdown v-model="categoryForm.icon" :options="iconOptions" optionLabel="label" optionValue="value"
                          class="flex-1" :placeholder="t('knowledge.selectIcon')">
                  <template #value="slotProps">
                    <div v-if="slotProps.value" class="flex items-center gap-2">
                      <i :class="slotProps.value"></i>
                      <span>{{ getIconLabel(slotProps.value) }}</span>
                    </div>
                    <span v-else>{{ slotProps.placeholder }}</span>
                  </template>
                  <template #option="slotProps">
                    <div class="flex items-center gap-2">
                      <i :class="slotProps.option.value"></i>
                      <span>{{ slotProps.option.label }}</span>
                    </div>
                  </template>
                </Dropdown>
                <div class="w-10 h-10 rounded border flex-shrink-0 flex items-center justify-center" style="background-color: var(--bg-app);">
                  <i :class="categoryForm.icon" :style="{ color: categoryForm.color, fontSize: '1.25rem' }"></i>
                </div>
              </div>
            </div>
          </div>
          <div class="mb-3">
            <label class="block text-sm font-medium mb-1">{{ t('common.description') }}</label>
            <InputText v-model="categoryForm.description" class="w-full" />
          </div>
          <div class="mb-3">
            <label class="block text-sm font-medium mb-2">{{ t('common.color') }}</label>
            <div class="flex items-center gap-3">
              <div class="flex gap-1 flex-wrap">
                <div v-for="color in colorPresets" :key="color"
                     class="w-7 h-7 rounded cursor-pointer transition-all hover:scale-110 border-2"
                     :class="categoryForm.color === color ? 'border-white ring-2 ring-offset-2 ring-offset-slate-900' : 'border-transparent'"
                     :style="{ backgroundColor: color, '--tw-ring-color': color }"
                     @click="categoryForm.color = color">
                </div>
              </div>
              <div class="flex items-center gap-2">
                <InputText v-model="categoryForm.color" class="w-24 text-sm" placeholder="#0ea5e9" />
              </div>
            </div>
          </div>
          <!-- Preview -->
          <div class="mb-3 p-3 rounded-lg flex items-center gap-3" style="background-color: var(--surface-ground);">
            <span class="text-sm opacity-70">{{ t('knowledge.preview') }}:</span>
            <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg" style="background-color: var(--bg-secondary);">
              <i :class="categoryForm.icon" :style="{ color: categoryForm.color }"></i>
              <span class="font-medium">{{ categoryForm.name || t('knowledge.categoryName') }}</span>
            </div>
          </div>
          <div class="flex justify-end gap-2">
            <Button v-if="editingCategory" :label="t('common.cancel')" size="small" severity="secondary" outlined @click="resetCategoryForm" />
            <Button :label="editingCategory ? t('common.update') : t('common.add')" size="small" icon="pi pi-check" @click="saveCategory" :loading="savingCategory" />
          </div>
        </div>

        <!-- Existing categories list -->
        <div>
          <h4 class="font-semibold mb-3">{{ t('knowledge.existingCategories') }}</h4>
          <div v-if="categories.length === 0" class="text-center py-4 opacity-50">
            {{ t('knowledge.noCategoriesYet') }}
          </div>
          <div v-else class="space-y-2">
            <div v-for="cat in categories" :key="cat.id"
                 class="flex items-center gap-3 p-3 rounded-lg transition-all"
                 style="background-color: var(--bg-app);">
              <i :class="cat.icon || 'pi pi-folder'" :style="{ color: cat.color }"></i>
              <span class="flex-1 font-medium">{{ cat.name }}</span>
              <span class="text-sm opacity-50">{{ cat.article_count }} {{ t('knowledge.articles') }}</span>
              <Button icon="pi pi-pencil" text rounded size="small" @click="editCategory(cat)" />
              <Button icon="pi pi-trash" text rounded size="small" severity="danger"
                      :disabled="cat.article_count > 0" v-tooltip="cat.article_count > 0 ? t('knowledge.cannotDeleteWithArticles') : ''"
                      @click="confirmDeleteCategory(cat)" />
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <Button :label="t('common.close')" severity="secondary" @click="showCategoryDialog = false" />
      </template>
    </Dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useI18n } from 'vue-i18n';
import api from '../api';
import Breadcrumbs from '../components/shared/Breadcrumbs.vue';

const { t } = useI18n();
const toast = useToast();

// Breadcrumbs
const breadcrumbItems = computed(() => {
  const items = [{ label: t('knowledge.title'), icon: 'pi-book' }]
  if (selectedArticle.value) {
    items.push({ label: selectedArticle.value.title })
  }
  return items
});

// State
const articles = ref([]);
const popularArticles = ref([]);
const categories = ref([]);
const selectedArticle = ref(null);
const searchQuery = ref('');
const selectedCategoryId = ref(null);
const showDrafts = ref(false);
const feedbackSubmitted = ref(false);
const saving = ref(false);

// Category management state
const showCategoryDialog = ref(false);
const editingCategory = ref(null);
const savingCategory = ref(false);
const categoryForm = ref({
  name: '',
  description: '',
  icon: 'pi pi-folder',
  color: '#0ea5e9'
});

// Color presets for quick selection
const colorPresets = [
  '#0ea5e9', // Sky blue
  '#22c55e', // Green
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#8b5cf6', // Violet
  '#ec4899', // Pink
  '#06b6d4', // Cyan
  '#f97316', // Orange
  '#6366f1', // Indigo
  '#84cc16'  // Lime
];

// Pagination state
const articlesTotal = ref(0);
const articlesLimit = ref(20);
const loadingArticles = ref(false);
const hasMoreArticles = computed(() => articles.value.length < articlesTotal.value);

// Dialog
const showArticleDialog = ref(false);
const editingArticle = ref(null);
const articleForm = ref({
  title: '',
  summary: '',
  content: '',
  category_id: null,
  tags: [],
  is_published: false,
  is_internal: false
});

// Category options from API
const categoryOptions = computed(() => categories.value);

// Icon options for category selector (validated PrimeIcons)
const iconOptions = [
  { label: 'Dossier', value: 'pi pi-folder' },
  { label: 'Dossier ouvert', value: 'pi pi-folder-open' },
  { label: 'Fichier', value: 'pi pi-file' },
  { label: 'Livre', value: 'pi pi-book' },
  { label: 'Question', value: 'pi pi-question-circle' },
  { label: 'Info', value: 'pi pi-info-circle' },
  { label: 'Idée', value: 'pi pi-bolt' },
  { label: 'Outils', value: 'pi pi-wrench' },
  { label: 'Paramètres', value: 'pi pi-cog' },
  { label: 'Serveur', value: 'pi pi-server' },
  { label: 'Base de données', value: 'pi pi-database' },
  { label: 'Réseau', value: 'pi pi-sitemap' },
  { label: 'Cloud', value: 'pi pi-cloud' },
  { label: 'Sécurité', value: 'pi pi-shield' },
  { label: 'Cadenas', value: 'pi pi-lock' },
  { label: 'Utilisateurs', value: 'pi pi-users' },
  { label: 'Utilisateur', value: 'pi pi-user' },
  { label: 'Code', value: 'pi pi-code' },
  { label: 'Desktop', value: 'pi pi-desktop' },
  { label: 'Alerte', value: 'pi pi-exclamation-triangle' },
  { label: 'Check', value: 'pi pi-check-circle' },
  { label: 'Étoile', value: 'pi pi-star' },
  { label: 'Favori', value: 'pi pi-star-fill' },
  { label: 'Cœur', value: 'pi pi-heart' },
  { label: 'Tag', value: 'pi pi-tag' },
  { label: 'Bookmark', value: 'pi pi-bookmark' },
  { label: 'Calendrier', value: 'pi pi-calendar' },
  { label: 'Horloge', value: 'pi pi-clock' },
  { label: 'Email', value: 'pi pi-envelope' },
  { label: 'Téléphone', value: 'pi pi-phone' },
  { label: 'Globe', value: 'pi pi-globe' },
  { label: 'Maison', value: 'pi pi-home' },
  { label: 'Flèche', value: 'pi pi-arrow-right' },
  { label: 'Lien', value: 'pi pi-link' },
  { label: 'Commentaire', value: 'pi pi-comment' },
  { label: 'Liste', value: 'pi pi-list' }
];

const getIconLabel = (iconValue) => {
  const option = iconOptions.find(o => o.value === iconValue);
  return option ? option.label : iconValue;
};

// Computed - Check if user can manage knowledge (tech with permission, admin, superadmin)
const canManageKnowledge = computed(() => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  if (['admin', 'superadmin'].includes(user.role)) return true;
  if (user.role === 'tech') {
    const permissions = user.permissions || [];
    return permissions.includes('knowledge');
  }
  return false;
});

// Helpers
const formatDate = (dateStr) => {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString();
};

// Debounced search
let searchTimeout = null;
const debouncedSearch = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    articles.value = []; // Reset for new search
    loadArticles();
  }, 300);
};

// Data loading
const loadArticles = async (loadMore = false) => {
  loadingArticles.value = true;
  try {
    const params = new URLSearchParams();
    params.append('limit', articlesLimit.value);
    if (loadMore) {
      params.append('skip', articles.value.length);
    }
    if (searchQuery.value) params.append('search', searchQuery.value);
    if (selectedCategoryId.value) params.append('category_id', selectedCategoryId.value);
    if (!showDrafts.value) params.append('published_only', 'true');

    const response = await api.get(`/knowledge/articles?${params}`);
    if (loadMore) {
      articles.value = [...articles.value, ...response.data.items];
    } else {
      articles.value = response.data.items;
    }
    articlesTotal.value = response.data.total;
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || 'Failed to load articles' });
  } finally {
    loadingArticles.value = false;
  }
};

// Load more articles
const loadMoreArticles = () => {
  if (hasMoreArticles.value && !loadingArticles.value) {
    loadArticles(true);
  }
};

const loadPopularArticles = async () => {
  try {
    const response = await api.get('/knowledge/articles/popular?limit=5');
    popularArticles.value = response.data;
  } catch {
    // Silent fail - non-critical data
  }
};

const loadCategories = async () => {
  try {
    const response = await api.get('/knowledge/categories');
    categories.value = response.data;
  } catch {
    // Silent fail - non-critical data
  }
};

const selectCategory = (categoryId) => {
  selectedCategoryId.value = categoryId;
  articles.value = []; // Reset for new category
  loadArticles();
};

// Article actions
const openArticle = async (slug) => {
  try {
    const response = await api.get(`/knowledge/articles/${slug}`);
    selectedArticle.value = response.data;
    feedbackSubmitted.value = false;
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || 'Article not found' });
  }
};

const closeArticle = () => {
  selectedArticle.value = null;
};

const openArticleDialog = (article = null) => {
  editingArticle.value = article;
  if (article) {
    articleForm.value = {
      title: article.title,
      summary: article.summary || '',
      content: article.content,
      category_id: article.category_id,
      tags: article.tags || [],
      is_published: article.is_published,
      is_internal: article.is_internal
    };
  } else {
    articleForm.value = {
      title: '',
      summary: '',
      content: '',
      category_id: null,
      tags: [],
      is_published: false,
      is_internal: false
    };
  }
  showArticleDialog.value = true;
};

const saveArticle = async () => {
  if (!articleForm.value.title || !articleForm.value.content) {
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.fillRequiredFields') });
    return;
  }
  saving.value = true;
  try {
    if (editingArticle.value) {
      await api.put(`/knowledge/articles/${editingArticle.value.id}`, articleForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('knowledge.articleUpdated') });
      if (selectedArticle.value?.id === editingArticle.value.id) {
        await openArticle(selectedArticle.value.slug);
      }
    } else {
      await api.post('/knowledge/articles', articleForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('knowledge.articleCreated') });
    }
    showArticleDialog.value = false;
    loadArticles();
    loadCategories();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  } finally {
    saving.value = false;
  }
};

const confirmDeleteArticle = async (article) => {
  if (!confirm(t('common.confirmDeleteItem'))) return;
  try {
    await api.delete(`/knowledge/articles/${article.id}`);
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('knowledge.articleDeleted') });
    selectedArticle.value = null;
    loadArticles();
    loadCategories();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail });
  }
};

const publishArticle = async (id) => {
  try {
    await api.post(`/knowledge/articles/${id}/publish`);
    toast.add({ severity: 'success', summary: t('common.success'), detail: 'Article published' });
    if (selectedArticle.value?.id === id) {
      selectedArticle.value.is_published = true;
    }
    loadArticles();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail });
  }
};

const unpublishArticle = async (id) => {
  try {
    await api.post(`/knowledge/articles/${id}/unpublish`);
    toast.add({ severity: 'success', summary: t('common.success'), detail: 'Article unpublished' });
    if (selectedArticle.value?.id === id) {
      selectedArticle.value.is_published = false;
    }
    loadArticles();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail });
  }
};

const submitFeedback = async (helpful) => {
  try {
    await api.post(`/knowledge/articles/${selectedArticle.value.id}/feedback`, { helpful });
    feedbackSubmitted.value = true;
    if (helpful) {
      selectedArticle.value.helpful_count++;
    } else {
      selectedArticle.value.not_helpful_count++;
    }
  } catch {
    // Silent fail - feedback is non-critical
  }
};

// Category management functions
const resetCategoryForm = () => {
  editingCategory.value = null;
  categoryForm.value = {
    name: '',
    description: '',
    icon: 'pi pi-folder',
    color: '#0ea5e9'
  };
};

const editCategory = (cat) => {
  editingCategory.value = cat;
  // Normalize icon format - add 'pi ' prefix if missing
  let icon = cat.icon || 'pi pi-folder';
  if (icon && !icon.startsWith('pi ')) {
    icon = 'pi ' + icon;
  }
  categoryForm.value = {
    name: cat.name,
    description: cat.description || '',
    icon: icon,
    color: cat.color || '#0ea5e9'
  };
};

const saveCategory = async () => {
  if (!categoryForm.value.name) {
    toast.add({ severity: 'warn', summary: t('validation.error'), detail: t('validation.fillRequiredFields') });
    return;
  }
  savingCategory.value = true;
  try {
    if (editingCategory.value) {
      await api.put(`/knowledge/categories/${editingCategory.value.id}`, categoryForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('knowledge.categoryUpdated') });
    } else {
      await api.post('/knowledge/categories', categoryForm.value);
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('knowledge.categoryCreated') });
    }
    resetCategoryForm();
    loadCategories();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail || t('common.error') });
  } finally {
    savingCategory.value = false;
  }
};

const confirmDeleteCategory = async (cat) => {
  if (!confirm(t('common.confirmDeleteItem'))) return;
  try {
    await api.delete(`/knowledge/categories/${cat.id}`);
    toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('knowledge.categoryDeleted') });
    loadCategories();
  } catch (e) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: e.response?.data?.detail });
  }
};

onMounted(() => {
  loadArticles();
  loadPopularArticles();
  loadCategories();
});
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
