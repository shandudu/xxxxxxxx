<script lang="ts" setup>
import type {
  EquipmentCategoryForm,
  EquipmentCategoryTreeNode,
  EquipmentForm,
  EquipmentItem,
  EquipmentStatus,
  EquipmentType,
} from '../api';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { message } from 'antdv-next';

import { $t } from '#/locales';

import {
  createEquipmentApi,
  createEquipmentCategoryApi,
  getEquipmentApi,
  getEquipmentCategoryTreeApi,
  getEquipmentListApi,
  updateEquipmentApi,
  updateEquipmentCategoryApi,
  updateEquipmentEnabledApi,
  updateEquipmentStatusApi,
} from '../api';

interface ViewCategoryNode extends EquipmentCategoryTreeNode {
  key: string;
  title: string;
  children: ViewCategoryNode[];
}

interface CategorySelectNode {
  children: CategorySelectNode[];
  disabled?: boolean;
  title: string;
  value: number;
}

interface EquipmentPage {
  items: EquipmentItem[];
  links: Record<string, unknown>;
  page: number;
  size: number;
  total: number;
  total_pages: number;
}

const defaultPage = (): EquipmentPage => ({
  items: [],
  page: 1,
  size: 20,
  total: 0,
  total_pages: 0,
  links: {},
});

const createEmptyEquipmentForm = (): EquipmentForm => ({
  equipment_code: '',
  equipment_name: '',
  category_id: 0,
  equipment_type: 'PRODUCTION',
  model: undefined,
  manufacturer: undefined,
  serial_number: undefined,
  factory_code: undefined,
  area_code: undefined,
  installation_location: undefined,
  enabled: true,
  production_enabled: true,
  data_collection_enabled: false,
  maintenance_enabled: true,
  commission_date: undefined,
  service_date: undefined,
  rated_capacity: undefined,
  capacity_unit: undefined,
  remark: undefined,
});

const createEmptyCategoryForm = (): EquipmentCategoryForm => ({
  category_code: '',
  category_name: '',
  parent_id: undefined,
  status: 'ACTIVE',
  sort_no: 0,
  remark: undefined,
});

const equipmentTypes = computed(() =>
  ['PRODUCTION', 'INSPECTION', 'LOGISTICS', 'UTILITY', 'TOOL', 'OTHER'].map((value) => ({
    label: $t(`equipment.equipmentType.${value}`),
    value,
  })),
);

const statusOptions = computed(() =>
  ['IDLE', 'RUNNING', 'DOWN', 'MAINTENANCE', 'OFFLINE'].map((value) => ({
    label: $t(`equipment.status.${value}`),
    value,
  })),
);

const categoryStatusOptions = computed(() =>
  ['ACTIVE', 'DISABLED'].map((value) => ({
    label: $t(`equipment.categoryStatus.${value}`),
    value,
  })),
);

const yesNoOptions = computed(() => [
  { label: $t('equipment.filter.yes'), value: 'true' },
  { label: $t('equipment.filter.no'), value: 'false' },
]);

const categoryKeyword = ref('');
const categoryTree = ref<ViewCategoryNode[]>([]);
const selectedCategoryId = ref<number>();
const selectedEquipmentId = ref<number>();
const selectedEquipment = ref<EquipmentItem>();
const equipmentPage = ref<EquipmentPage>(defaultPage());
const loading = ref(false);
const detailLoading = ref(false);
const equipmentDrawerOpen = ref(false);
const categoryModalOpen = ref(false);
const saving = ref(false);
const categorySaving = ref(false);
const equipmentForm = ref<EquipmentForm>(createEmptyEquipmentForm());
const categoryForm = ref<EquipmentCategoryForm>(createEmptyCategoryForm());

const filters = reactive<{
  data_collection_enabled?: boolean;
  enabled?: boolean;
  equipment_type?: EquipmentType;
  keyword: string;
  maintenance_enabled?: boolean;
  production_enabled?: boolean;
  status?: EquipmentStatus;
}>({ keyword: '' });

const filteredCategoryTree = computed(() => {
  const keyword = categoryKeyword.value.trim().toLocaleLowerCase();
  if (!keyword) return categoryTree.value;

  function filter(nodes: ViewCategoryNode[]): ViewCategoryNode[] {
    return nodes.reduce<ViewCategoryNode[]>((result, node) => {
      const children = filter(node.children);
      if (node.title.toLocaleLowerCase().includes(keyword) || children.length > 0) {
        result.push({ ...node, children });
      }
      return result;
    }, []);
  }
  return filter(categoryTree.value);
});

const categorySelectTree = computed<CategorySelectNode[]>(() => {
  function map(nodes: ViewCategoryNode[]): CategorySelectNode[] {
    return nodes.map((node) => ({
      value: node.id,
      title: `${node.name} (${node.code})`,
      disabled: node.status === 'DISABLED',
      children: map(node.children),
    }));
  }
  return map(categoryTree.value);
});

const selectedCategory = computed(() =>
  selectedCategoryId.value ? findCategory(selectedCategoryId.value) : undefined,
);
const selectedCategoryName = computed(
  () => selectedCategory.value?.name ?? $t('equipment.allEquipment'),
);

function createBooleanFilter(
  key: 'data_collection_enabled' | 'enabled' | 'maintenance_enabled' | 'production_enabled',
) {
  return computed<string | undefined>({
    get: () => (filters[key] === undefined ? undefined : String(filters[key])),
    set: (value) => {
      filters[key] = value === undefined ? undefined : value === 'true';
      loadEquipment(1);
    },
  });
}

const enabledFilter = createBooleanFilter('enabled');
const productionEnabledFilter = createBooleanFilter('production_enabled');
const dataCollectionEnabledFilter = createBooleanFilter('data_collection_enabled');
const maintenanceEnabledFilter = createBooleanFilter('maintenance_enabled');

const tableColumns = computed(() => [
  { title: $t('equipment.field.code'), dataIndex: 'equipment_code', key: 'equipment_code', width: 140 },
  { title: $t('equipment.field.name'), dataIndex: 'equipment_name', key: 'equipment_name', width: 155 },
  { title: $t('equipment.field.category'), dataIndex: 'category_name', key: 'category_name', width: 120 },
  { title: $t('equipment.field.type'), dataIndex: 'equipment_type', key: 'equipment_type', width: 110 },
  { title: $t('equipment.field.model'), dataIndex: 'model', key: 'model', width: 110 },
  { title: $t('equipment.field.installationLocation'), dataIndex: 'installation_location', key: 'installation_location', ellipsis: true },
  { title: $t('equipment.field.status'), dataIndex: 'status', key: 'status', width: 90 },
  { title: $t('equipment.field.enabled'), dataIndex: 'enabled', key: 'enabled', width: 80 },
]);

function buildCategoryTree(nodes: EquipmentCategoryTreeNode[]): ViewCategoryNode[] {
  return nodes.map((node) => ({
    ...node,
    key: String(node.id),
    title: `${node.name} (${node.code})`,
    children: buildCategoryTree(node.children ?? []),
  }));
}

function findCategory(id: number, nodes = categoryTree.value): undefined | ViewCategoryNode {
  for (const node of nodes) {
    if (node.id === id) return node;
    const child = findCategory(id, node.children);
    if (child) return child;
  }
  return undefined;
}

function typeLabel(type: EquipmentType) {
  return $t(`equipment.equipmentType.${type}`);
}

function statusLabel(status: EquipmentStatus) {
  return $t(`equipment.status.${status}`);
}

function yesNo(value: boolean) {
  return value ? $t('equipment.filter.yes') : $t('equipment.filter.no');
}

function statusColor(status: EquipmentStatus) {
  const colors: Record<EquipmentStatus, string> = {
    DISABLED: 'default',
    DOWN: 'red',
    IDLE: 'blue',
    MAINTENANCE: 'orange',
    OFFLINE: 'default',
    RUNNING: 'green',
  };
  return colors[status];
}

async function loadTree() {
  categoryTree.value = buildCategoryTree(await getEquipmentCategoryTreeApi());
}

async function loadEquipment(page = 1, size = equipmentPage.value.size) {
  loading.value = true;
  try {
    const data = await getEquipmentListApi({
      page,
      size,
      keyword: filters.keyword.trim() || undefined,
      category_id: selectedCategoryId.value,
      equipment_type: filters.equipment_type,
      status: filters.status,
      enabled: filters.enabled,
      production_enabled: filters.production_enabled,
      data_collection_enabled: filters.data_collection_enabled,
      maintenance_enabled: filters.maintenance_enabled,
    });
    equipmentPage.value = data;
    const current = data.items.find((item) => item.id === selectedEquipmentId.value) ?? data.items[0];
    if (current) await selectEquipment(current);
    else {
      selectedEquipmentId.value = undefined;
      selectedEquipment.value = undefined;
    }
  } finally {
    loading.value = false;
  }
}

async function selectEquipment(item: EquipmentItem) {
  selectedEquipmentId.value = item.id;
  detailLoading.value = true;
  try {
    selectedEquipment.value = await getEquipmentApi(item.id);
  } finally {
    detailLoading.value = false;
  }
}

function selectCategory(keys: Array<number | string>) {
  selectedCategoryId.value = keys[0] ? Number(keys[0]) : undefined;
  loadEquipment(1);
}

function clearFilters() {
  filters.keyword = '';
  filters.equipment_type = undefined;
  filters.status = undefined;
  filters.enabled = undefined;
  filters.production_enabled = undefined;
  filters.data_collection_enabled = undefined;
  filters.maintenance_enabled = undefined;
  loadEquipment(1);
}

function createEquipment() {
  equipmentForm.value = createEmptyEquipmentForm();
  const activeCategory = selectedCategory.value?.status === 'ACTIVE'
    ? selectedCategory.value
    : categoryTree.value.find((item) => item.status === 'ACTIVE');
  if (activeCategory) equipmentForm.value.category_id = activeCategory.id;
  equipmentDrawerOpen.value = true;
}

function editEquipment() {
  if (!selectedEquipment.value) return;
  const item = selectedEquipment.value;
  equipmentForm.value = {
    id: item.id,
    equipment_code: item.equipment_code,
    equipment_name: item.equipment_name,
    category_id: item.category_id,
    equipment_type: item.equipment_type,
    model: item.model,
    manufacturer: item.manufacturer,
    serial_number: item.serial_number,
    factory_code: item.factory_code,
    area_code: item.area_code,
    installation_location: item.installation_location,
    enabled: item.enabled,
    production_enabled: item.production_enabled,
    data_collection_enabled: item.data_collection_enabled,
    maintenance_enabled: item.maintenance_enabled,
    commission_date: item.commission_date,
    service_date: item.service_date,
    rated_capacity: item.rated_capacity,
    capacity_unit: item.capacity_unit,
    remark: item.remark,
  };
  equipmentDrawerOpen.value = true;
}

async function saveEquipment() {
  if (!equipmentForm.value.equipment_code.trim() || !equipmentForm.value.equipment_name.trim()) {
    message.warning($t('equipment.message.requiredBasic'));
    return;
  }
  if (!equipmentForm.value.category_id || findCategory(equipmentForm.value.category_id)?.status !== 'ACTIVE') {
    message.warning($t('equipment.message.requiredCategory'));
    return;
  }
  saving.value = true;
  try {
    const saved = equipmentForm.value.id
      ? await updateEquipmentApi(equipmentForm.value.id, equipmentForm.value)
      : await createEquipmentApi(equipmentForm.value);
    equipmentDrawerOpen.value = false;
    selectedEquipmentId.value = saved.id;
    await loadEquipment(equipmentPage.value.page);
    message.success($t('equipment.message.saved'));
  } finally {
    saving.value = false;
  }
}

async function toggleEnabled() {
  if (!selectedEquipment.value) return;
  selectedEquipment.value = await updateEquipmentEnabledApi(
    selectedEquipment.value.id,
    !selectedEquipment.value.enabled,
  );
  await loadEquipment(equipmentPage.value.page);
  message.success($t('equipment.message.enabledUpdated'));
}

async function changeStatus(status: EquipmentStatus) {
  if (!selectedEquipment.value || !selectedEquipment.value.enabled) return;
  selectedEquipment.value = await updateEquipmentStatusApi(selectedEquipment.value.id, status);
  await loadEquipment(equipmentPage.value.page);
  message.success($t('equipment.message.statusUpdated'));
}

function createCategory(parent?: ViewCategoryNode) {
  categoryForm.value = {
    ...createEmptyCategoryForm(),
    parent_id: parent?.id,
  };
  categoryModalOpen.value = true;
}

function editCategory() {
  if (!selectedCategory.value) return;
  const item = selectedCategory.value;
  categoryForm.value = {
    id: item.id,
    category_code: item.code,
    category_name: item.name,
    parent_id: item.parent_id,
    status: item.status,
    sort_no: item.sort_no,
    remark: item.remark,
  };
  categoryModalOpen.value = true;
}

async function saveCategory() {
  if (!categoryForm.value.category_code.trim() || !categoryForm.value.category_name.trim()) {
    return;
  }
  categorySaving.value = true;
  try {
    const saved = categoryForm.value.id
      ? await updateEquipmentCategoryApi(categoryForm.value.id, categoryForm.value)
      : await createEquipmentCategoryApi(categoryForm.value);
    categoryModalOpen.value = false;
    selectedCategoryId.value = saved.id;
    await loadTree();
    await loadEquipment(1);
    message.success($t('equipment.message.categorySaved'));
  } finally {
    categorySaving.value = false;
  }
}

function handlePageChange(page: number, size: number) {
  loadEquipment(page, size);
}

onMounted(async () => {
  await loadTree();
  await loadEquipment();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 gap-3">
      <a-card class="w-64 shrink-0" :body-style="{ padding: '12px' }">
        <template #title>{{ $t('equipment.categoryTree') }}</template>
        <template #extra><a-space size="small"><a-button size="small" type="link" @click="createCategory()">{{ $t('equipment.action.create') }}</a-button><a-button size="small" type="link" :disabled="!selectedCategory" @click="createCategory(selectedCategory)">{{ $t('equipment.action.addChild') }}</a-button><a-button size="small" type="link" :disabled="!selectedCategory" @click="editCategory">{{ $t('equipment.action.editCategory') }}</a-button></a-space></template>
        <a-button block class="mb-3" size="small" @click="selectedCategoryId = undefined; loadEquipment(1)">
          {{ $t('equipment.allEquipment') }}
        </a-button>
        <a-input v-model:value="categoryKeyword" allow-clear class="mb-3" :placeholder="$t('equipment.placeholder.categorySearch')" />
        <a-tree
          :default-expand-all="true"
          :selected-keys="selectedCategoryId ? [String(selectedCategoryId)] : []"
          :tree-data="filteredCategoryTree"
          block-node
          @select="selectCategory"
        />
      </a-card>

      <a-card class="min-w-0 flex-1" :body-style="{ padding: '12px' }">
        <template #title>
          <span>{{ selectedCategoryName }}</span>
          <span class="ml-2 text-sm text-muted-foreground">{{ equipmentPage.total }}</span>
        </template>
        <template #extra><a-button type="primary" @click="createEquipment">{{ $t('equipment.action.create') }}</a-button></template>

        <div class="mb-3 flex flex-wrap gap-2">
          <a-input-search v-model:value="filters.keyword" allow-clear class="w-52" :placeholder="$t('equipment.placeholder.keyword')" @search="loadEquipment(1)" />
          <a-select v-model:value="filters.equipment_type" allow-clear class="w-32" :options="equipmentTypes" :placeholder="$t('equipment.field.type')" @change="loadEquipment(1)" />
          <a-select v-model:value="filters.status" allow-clear class="w-28" :options="[...statusOptions, { label: $t('equipment.status.DISABLED'), value: 'DISABLED' }]" :placeholder="$t('equipment.field.status')" @change="loadEquipment(1)" />
          <a-select v-model:value="enabledFilter" allow-clear class="w-28" :options="yesNoOptions" :placeholder="$t('equipment.field.enabled')" />
          <a-select v-model:value="productionEnabledFilter" allow-clear class="w-32" :options="yesNoOptions" :placeholder="$t('equipment.field.productionEnabled')" />
          <a-select v-model:value="dataCollectionEnabledFilter" allow-clear class="w-36" :options="yesNoOptions" :placeholder="$t('equipment.field.dataCollectionEnabled')" />
          <a-select v-model:value="maintenanceEnabledFilter" allow-clear class="w-32" :options="yesNoOptions" :placeholder="$t('equipment.field.maintenanceEnabled')" />
          <a-button @click="clearFilters">{{ $t('equipment.action.reset') }}</a-button>
        </div>

        <a-table :columns="tableColumns" :data-source="equipmentPage.items" :loading="loading" :pagination="false" :row-class-name="(record: EquipmentItem) => record.id === selectedEquipmentId ? 'bg-primary/5' : ''" :row-key="(record: EquipmentItem) => record.id" :scroll="{ x: 1120 }" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'equipment_code'"><a-button class="h-auto p-0" type="link" @click="selectEquipment(record)">{{ record.equipment_code }}</a-button></template>
            <template v-else-if="column.key === 'equipment_type'">{{ typeLabel(record.equipment_type) }}</template>
            <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag></template>
            <template v-else-if="column.key === 'enabled'"><a-tag :color="record.enabled ? 'green' : 'default'">{{ yesNo(record.enabled) }}</a-tag></template>
            <template v-else-if="column.key === 'model'">{{ record.model || '-' }}</template>
            <template v-else-if="column.key === 'installation_location'">{{ record.installation_location || '-' }}</template>
          </template>
        </a-table>
        <div class="mt-3 flex justify-end"><a-pagination :current="equipmentPage.page" :page-size="equipmentPage.size" :page-size-options="['20', '50', '100']" :show-size-changer="true" :total="equipmentPage.total" @change="handlePageChange" /></div>
      </a-card>

      <a-card class="w-96 shrink-0" :body-style="{ padding: '12px' }" :loading="detailLoading">
        <template #title>{{ $t('equipment.detail') }}</template>
        <template #extra>
          <a-space v-if="selectedEquipment">
            <a-button size="small" @click="editEquipment">{{ $t('equipment.action.configure') }}</a-button>
            <a-button size="small" :danger="selectedEquipment.enabled" @click="toggleEnabled">{{ selectedEquipment.enabled ? $t('equipment.action.disable') : $t('equipment.action.enable') }}</a-button>
          </a-space>
        </template>
        <a-empty v-if="!selectedEquipment" :description="$t('equipment.empty.selectEquipment')" />
        <div v-else class="space-y-3 text-sm">
          <div class="rounded bg-muted/40 p-3"><div class="text-lg font-semibold">{{ selectedEquipment.equipment_name }}</div><div class="mt-1 text-muted-foreground">{{ selectedEquipment.equipment_code }}</div><a-tag class="mt-2" :color="statusColor(selectedEquipment.status)">{{ statusLabel(selectedEquipment.status) }}</a-tag></div>
          <div class="font-medium">{{ $t('equipment.group.basic') }}</div>
          <a-descriptions :column="1" size="small"><a-descriptions-item :label="$t('equipment.field.category')">{{ selectedEquipment.category_name || '-' }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.type')">{{ typeLabel(selectedEquipment.equipment_type) }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.model')">{{ selectedEquipment.model || '-' }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.manufacturer')">{{ selectedEquipment.manufacturer || '-' }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.serialNumber')">{{ selectedEquipment.serial_number || '-' }}</a-descriptions-item></a-descriptions>
          <div class="font-medium">{{ $t('equipment.group.location') }}</div>
          <a-descriptions :column="1" size="small"><a-descriptions-item :label="$t('equipment.field.factory')">{{ selectedEquipment.factory_code || '-' }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.area')">{{ selectedEquipment.area_code || '-' }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.installationLocation')">{{ selectedEquipment.installation_location || '-' }}</a-descriptions-item></a-descriptions>
          <div class="font-medium">{{ $t('equipment.group.operation') }}</div>
          <a-descriptions :column="1" size="small"><a-descriptions-item :label="$t('equipment.field.enabled')">{{ yesNo(selectedEquipment.enabled) }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.productionEnabled')">{{ yesNo(selectedEquipment.production_enabled) }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.ratedCapacity')">{{ selectedEquipment.rated_capacity ?? '-' }} {{ selectedEquipment.capacity_unit || '' }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.status')"><a-select :disabled="!selectedEquipment.enabled" :options="statusOptions" :value="selectedEquipment.status" class="w-36" @change="changeStatus" /></a-descriptions-item></a-descriptions>
          <div class="font-medium">{{ $t('equipment.group.collection') }}</div><a-tag :color="selectedEquipment.data_collection_enabled ? 'blue' : 'default'">{{ $t('equipment.field.dataCollectionEnabled') }}: {{ yesNo(selectedEquipment.data_collection_enabled) }}</a-tag>
          <div class="font-medium">{{ $t('equipment.group.maintenance') }}</div><a-descriptions :column="1" size="small"><a-descriptions-item :label="$t('equipment.field.maintenanceEnabled')">{{ yesNo(selectedEquipment.maintenance_enabled) }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.commissionDate')">{{ selectedEquipment.commission_date || '-' }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.serviceDate')">{{ selectedEquipment.service_date || '-' }}</a-descriptions-item></a-descriptions>
          <div class="font-medium">{{ $t('equipment.group.system') }}</div><a-descriptions :column="1" size="small"><a-descriptions-item :label="$t('equipment.field.createdTime')">{{ selectedEquipment.created_time || '-' }}</a-descriptions-item><a-descriptions-item :label="$t('equipment.field.updatedTime')">{{ selectedEquipment.updated_time || '-' }}</a-descriptions-item></a-descriptions>
        </div>
      </a-card>
    </div>

    <a-drawer v-model:open="equipmentDrawerOpen" :title="equipmentForm.id ? $t('equipment.title.configure') : $t('equipment.title.create')" :width="760" @close="equipmentDrawerOpen = false">
      <a-form layout="vertical">
        <div class="mb-3 text-base font-medium">{{ $t('equipment.group.basic') }}</div>
        <a-row :gutter="16"><a-col :span="12"><a-form-item :label="$t('equipment.field.code')" required><a-input v-model:value="equipmentForm.equipment_code" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('equipment.field.name')" required><a-input v-model:value="equipmentForm.equipment_name" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('equipment.field.category')" required><a-tree-select v-model:value="equipmentForm.category_id" class="w-full" tree-default-expand-all :tree-data="categorySelectTree" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('equipment.field.type')" required><a-select v-model:value="equipmentForm.equipment_type" class="w-full" :options="equipmentTypes" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('equipment.field.model')"><a-input v-model:value="equipmentForm.model" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('equipment.field.manufacturer')"><a-input v-model:value="equipmentForm.manufacturer" /></a-form-item></a-col><a-col :span="24"><a-form-item :label="$t('equipment.field.serialNumber')"><a-input v-model:value="equipmentForm.serial_number" /></a-form-item></a-col></a-row>
        <div class="mb-3 text-base font-medium">{{ $t('equipment.group.location') }}</div>
        <a-row :gutter="16"><a-col :span="8"><a-form-item :label="$t('equipment.field.factory')"><a-input v-model:value="equipmentForm.factory_code" /></a-form-item></a-col><a-col :span="8"><a-form-item :label="$t('equipment.field.area')"><a-input v-model:value="equipmentForm.area_code" /></a-form-item></a-col><a-col :span="8"><a-form-item :label="$t('equipment.field.installationLocation')"><a-input v-model:value="equipmentForm.installation_location" /></a-form-item></a-col></a-row>
        <div class="mb-3 text-base font-medium">{{ $t('equipment.group.operation') }}</div>
        <a-row :gutter="16"><a-col :span="8"><a-form-item :label="$t('equipment.field.enabled')"><a-switch v-model:checked="equipmentForm.enabled" /></a-form-item></a-col><a-col :span="8"><a-form-item :label="$t('equipment.field.productionEnabled')"><a-switch v-model:checked="equipmentForm.production_enabled" /></a-form-item></a-col><a-col :span="8"><a-form-item :label="$t('equipment.field.dataCollectionEnabled')"><a-switch v-model:checked="equipmentForm.data_collection_enabled" /></a-form-item></a-col><a-col :span="8"><a-form-item :label="$t('equipment.field.maintenanceEnabled')"><a-switch v-model:checked="equipmentForm.maintenance_enabled" /></a-form-item></a-col><a-col :span="8"><a-form-item :label="$t('equipment.field.ratedCapacity')"><a-input-number v-model:value="equipmentForm.rated_capacity" class="w-full" :min="0" :precision="6" /></a-form-item></a-col><a-col :span="8"><a-form-item :label="$t('equipment.field.capacityUnit')"><a-input v-model:value="equipmentForm.capacity_unit" /></a-form-item></a-col></a-row>
        <div class="mb-3 text-base font-medium">{{ $t('equipment.group.maintenance') }}</div>
        <a-row :gutter="16"><a-col :span="12"><a-form-item :label="$t('equipment.field.commissionDate')"><a-input v-model:value="equipmentForm.commission_date" type="date" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('equipment.field.serviceDate')"><a-input v-model:value="equipmentForm.service_date" type="date" /></a-form-item></a-col></a-row>
        <a-form-item :label="$t('equipment.field.remark')"><a-textarea v-model:value="equipmentForm.remark" :rows="3" /></a-form-item>
      </a-form>
      <template #footer><div class="flex justify-end gap-2"><a-button @click="equipmentDrawerOpen = false">{{ $t('equipment.action.cancel') }}</a-button><a-button type="primary" :loading="saving" @click="saveEquipment">{{ $t('equipment.action.save') }}</a-button></div></template>
    </a-drawer>

    <a-modal v-model:open="categoryModalOpen" :confirm-loading="categorySaving" :title="categoryForm.id ? $t('equipment.title.configureCategory') : $t('equipment.title.createCategory')" @ok="saveCategory">
      <a-form layout="vertical"><a-row :gutter="16"><a-col :span="12"><a-form-item :label="$t('equipment.field.categoryCode')" required><a-input v-model:value="categoryForm.category_code" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('equipment.field.categoryName')" required><a-input v-model:value="categoryForm.category_name" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('equipment.field.parentCategory')"><a-tree-select v-model:value="categoryForm.parent_id" allow-clear class="w-full" tree-default-expand-all :tree-data="categorySelectTree" /></a-form-item></a-col><a-col :span="6"><a-form-item :label="$t('equipment.field.categoryStatus')"><a-select v-model:value="categoryForm.status" class="w-full" :options="categoryStatusOptions" /></a-form-item></a-col><a-col :span="6"><a-form-item :label="$t('equipment.field.sortNo')"><a-input-number v-model:value="categoryForm.sort_no" class="w-full" /></a-form-item></a-col></a-row><a-form-item :label="$t('equipment.field.remark')"><a-textarea v-model:value="categoryForm.remark" :rows="3" /></a-form-item></a-form>
    </a-modal>
  </Page>
</template>
