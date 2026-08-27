<script lang="ts" setup>
import type {
  CategoryTreeNode,
  MaterialForm,
  MaterialItem,
  MaterialStatus,
  MaterialType,
  UnitItem,
  WarehouseOption,
} from '../api';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { message } from 'antdv-next';

import { $t } from '#/locales';

import {
  createMaterialApi,
  getMaterialApi,
  getMaterialCategoryTreeApi,
  getMaterialListApi,
  getMaterialUnitListApi,
  getMaterialWarehouseOptionsApi,
  updateMaterialApi,
  updateMaterialStatusApi,
} from '../api';

interface ViewCategoryNode extends CategoryTreeNode {
  key: string;
  title: string;
  children: ViewCategoryNode[];
}

interface CategorySelectNode {
  key: string;
  value: number;
  title: string;
  disabled?: boolean;
  children?: CategorySelectNode[];
}

interface MaterialPage {
  items: MaterialItem[];
  page: number;
  size: number;
  total: number;
  total_pages: number;
  links: Record<string, unknown>;
}

const defaultPage = (): MaterialPage => ({
  items: [],
  page: 1,
  size: 20,
  total: 0,
  total_pages: 0,
  links: {},
});

const createEmptyForm = (): MaterialForm => ({
  material_code: '',
  material_name: '',
  material_short_name: undefined,
  material_type: 'RAW_MATERIAL',
  category_id: 0,
  base_unit_id: 0,
  specification: undefined,
  model: undefined,
  status: 'ACTIVE',
  batch_control: false,
  serial_control: false,
  purchasable: true,
  producible: false,
  sellable: false,
  quality_inspection_required: false,
  default_warehouse_id: undefined,
  shelf_life_days: undefined,
  remark: undefined,
});

const materialTypes = computed(() =>
  [
    'RAW_MATERIAL',
    'SEMI_FINISHED',
    'FINISHED_PRODUCT',
    'AUXILIARY',
    'PACKAGING',
    'SPARE_PART',
    'CONSUMABLE',
  ].map((value) => ({
    label: $t(`material.materialType.${value}`),
    value,
  })),
);

const statusOptions = computed(() => [
  { label: $t('material.status.ACTIVE'), value: 'ACTIVE' },
  { label: $t('material.status.DISABLED'), value: 'DISABLED' },
]);

const categoryKeyword = ref('');
const categoryTree = ref<ViewCategoryNode[]>([]);
const selectedCategoryId = ref<number>();
const selectedMaterialId = ref<number>();
const materialPage = ref<MaterialPage>(defaultPage());
const selectedMaterial = ref<MaterialItem>();
const units = ref<UnitItem[]>([]);
const warehouses = ref<WarehouseOption[]>([]);
const loading = ref(false);
const detailLoading = ref(false);
const drawerOpen = ref(false);
const saving = ref(false);
const formData = ref<MaterialForm>(createEmptyForm());

const filters = reactive<{
  batch_control?: boolean;
  keyword: string;
  material_type?: MaterialType;
  producible?: boolean;
  purchasable?: boolean;
  sellable?: boolean;
  status?: MaterialStatus;
}>({
  keyword: '',
});

const filteredCategoryTree = computed(() => {
  const keyword = categoryKeyword.value.trim().toLowerCase();
  if (!keyword) return categoryTree.value;

  function filter(nodes: ViewCategoryNode[]): ViewCategoryNode[] {
    return nodes.reduce<ViewCategoryNode[]>((result, node) => {
      const children = filter(node.children);
      if (
        node.title.toLowerCase().includes(keyword) ||
        children.length > 0
      ) {
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
      key: node.key,
      value: node.id,
      title: `${node.name} (${node.code})`,
      disabled: node.status === 'DISABLED',
      children: map(node.children),
    }));
  }
  return map(categoryTree.value);
});

const selectedCategoryName = computed(() => {
  if (!selectedCategoryId.value) return $t('material.allMaterials');
  return findCategory(selectedCategoryId.value)?.name ?? $t('material.allMaterials');
});

const batchControlFilter = computed<string | undefined>({
  get: () => (filters.batch_control === undefined ? undefined : String(filters.batch_control)),
  set: (value) => {
    filters.batch_control = value === undefined ? undefined : value === 'true';
    loadMaterials(1);
  },
});

const businessFilterOptions = computed(() => [
  { label: $t('material.filter.businessYes'), value: 'true' },
  { label: $t('material.filter.businessNo'), value: 'false' },
]);

function createBooleanFilter(key: 'producible' | 'purchasable' | 'sellable') {
  return computed<string | undefined>({
    get: () => (filters[key] === undefined ? undefined : String(filters[key])),
    set: (value) => {
      filters[key] = value === undefined ? undefined : value === 'true';
      loadMaterials(1);
    },
  });
}

const purchasableFilter = createBooleanFilter('purchasable');
const producibleFilter = createBooleanFilter('producible');
const sellableFilter = createBooleanFilter('sellable');

const tableColumns = computed(() => [
  { title: $t('material.field.code'), dataIndex: 'material_code', key: 'material_code', width: 135 },
  { title: $t('material.field.name'), dataIndex: 'material_name', key: 'material_name', width: 160 },
  { title: $t('material.field.specification'), dataIndex: 'specification', key: 'specification', ellipsis: true },
  { title: $t('material.field.type'), dataIndex: 'material_type', key: 'material_type', width: 120 },
  { title: $t('material.field.unit'), dataIndex: 'unit_code', key: 'unit_code', width: 72 },
  { title: $t('material.field.status'), dataIndex: 'status', key: 'status', width: 78 },
]);

function buildCategoryTree(nodes: CategoryTreeNode[]): ViewCategoryNode[] {
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
    const found = findCategory(id, node.children);
    if (found) return found;
  }
  return undefined;
}

function materialTypeLabel(type: MaterialType) {
  return $t(`material.materialType.${type}`);
}

function statusLabel(status: MaterialStatus) {
  return $t(`material.status.${status}`);
}

function yesNo(value: boolean) {
  return value ? $t('material.common.yes') : $t('material.common.no');
}

async function loadMeta() {
  const [categories, unitList, warehouseList] = await Promise.all([
    getMaterialCategoryTreeApi(),
    getMaterialUnitListApi(),
    getMaterialWarehouseOptionsApi(),
  ]);
  categoryTree.value = buildCategoryTree(categories);
  units.value = unitList;
  warehouses.value = warehouseList;
}

async function loadMaterials(page = 1, size = materialPage.value.size) {
  loading.value = true;
  try {
    const data = await getMaterialListApi({
      page,
      size,
      keyword: filters.keyword.trim() || undefined,
      material_type: filters.material_type,
      category_id: selectedCategoryId.value,
      status: filters.status,
      batch_control: filters.batch_control,
      purchasable: filters.purchasable,
      producible: filters.producible,
      sellable: filters.sellable,
    });
    materialPage.value = data;
    const current = data.items.find((item) => item.id === selectedMaterialId.value);
    if (current) {
      await selectMaterial(current, false);
    } else if (data.items[0]) {
      await selectMaterial(data.items[0], false);
    } else {
      selectedMaterialId.value = undefined;
      selectedMaterial.value = undefined;
    }
  } finally {
    loading.value = false;
  }
}

async function selectMaterial(item: MaterialItem, reload = true) {
  selectedMaterialId.value = item.id;
  if (!reload) {
    selectedMaterial.value = item;
    return;
  }
  detailLoading.value = true;
  try {
    selectedMaterial.value = await getMaterialApi(item.id);
  } finally {
    detailLoading.value = false;
  }
}

function selectCategory(keys: Array<number | string>) {
  selectedCategoryId.value = keys[0] ? Number(keys[0]) : undefined;
  loadMaterials(1);
}

function clearFilters() {
  filters.keyword = '';
  filters.material_type = undefined;
  filters.status = undefined;
  filters.batch_control = undefined;
  filters.purchasable = undefined;
  filters.producible = undefined;
  filters.sellable = undefined;
  loadMaterials(1);
}

function editMaterial() {
  if (!selectedMaterial.value) return;
  const item = selectedMaterial.value;
  formData.value = {
    material_code: item.material_code,
    material_name: item.material_name,
    material_short_name: item.material_short_name,
    material_type: item.material_type,
    category_id: item.category_id,
    base_unit_id: item.base_unit_id,
    specification: item.specification,
    model: item.model,
    status: item.status,
    batch_control: item.batch_control,
    serial_control: item.serial_control,
    purchasable: item.purchasable,
    producible: item.producible,
    sellable: item.sellable,
    quality_inspection_required: item.quality_inspection_required,
    default_warehouse_id: item.default_warehouse_id,
    shelf_life_days: item.shelf_life_days,
    remark: item.remark,
    id: item.id,
  };
  drawerOpen.value = true;
}

function createMaterial() {
  formData.value = createEmptyForm();
  const firstCategory = categoryTree.value.find((item) => item.status === 'ACTIVE');
  const firstUnit = units.value.find((item) => item.status === 'ACTIVE');
  if (firstCategory) formData.value.category_id = firstCategory.id;
  if (firstUnit) formData.value.base_unit_id = firstUnit.id;
  drawerOpen.value = true;
}

async function saveMaterial() {
  if (!formData.value.material_code.trim() || !formData.value.material_name.trim()) {
    message.warning($t('material.message.requiredBasic'));
    return;
  }
  if (!formData.value.category_id || !formData.value.base_unit_id) {
    message.warning($t('material.message.requiredReferences'));
    return;
  }
  saving.value = true;
  try {
    const saved = formData.value.id
      ? await updateMaterialApi(formData.value.id, formData.value)
      : await createMaterialApi(formData.value);
    drawerOpen.value = false;
    selectedMaterialId.value = saved.id;
    await loadMaterials(materialPage.value.page);
    await selectMaterial(saved);
    message.success($t('material.message.saved'));
  } finally {
    saving.value = false;
  }
}

async function toggleStatus() {
  if (!selectedMaterial.value) return;
  const nextStatus: MaterialStatus = selectedMaterial.value.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  const saved = await updateMaterialStatusApi(selectedMaterial.value.id, nextStatus);
  selectedMaterial.value = saved;
  await loadMaterials(materialPage.value.page);
  message.success($t('material.message.statusUpdated'));
}

function handlePageChange(page: number, pageSize: number) {
  loadMaterials(page, pageSize);
}

onMounted(async () => {
  await loadMeta();
  await loadMaterials();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 gap-3">
      <a-card class="w-64 shrink-0" :body-style="{ padding: '12px' }">
        <template #title>{{ $t('material.categoryTree') }}</template>
        <template #extra>
          <a-button type="link" size="small" @click="selectedCategoryId = undefined; loadMaterials(1)">
            {{ $t('material.allMaterials') }}
          </a-button>
        </template>
        <a-input
          v-model:value="categoryKeyword"
          allow-clear
          class="mb-3"
          :placeholder="$t('material.placeholder.categorySearch')"
        />
        <a-tree
          :tree-data="filteredCategoryTree"
          :selected-keys="selectedCategoryId ? [String(selectedCategoryId)] : []"
          :default-expand-all="true"
          block-node
          @select="selectCategory"
        />
      </a-card>

      <a-card class="min-w-0 flex-1" :body-style="{ padding: '12px' }">
        <template #title>
          <span>{{ selectedCategoryName }}</span>
          <span class="ml-2 text-sm text-muted-foreground">{{ materialPage.total }}</span>
        </template>
        <template #extra>
          <a-space>
            <a-button type="primary" @click="createMaterial">{{ $t('material.action.create') }}</a-button>
          </a-space>
        </template>

        <div class="mb-3 flex flex-wrap gap-2">
          <a-input-search
            v-model:value="filters.keyword"
            allow-clear
            class="w-52"
            :placeholder="$t('material.placeholder.keyword')"
            @search="loadMaterials(1)"
          />
          <a-select
            v-model:value="filters.material_type"
            allow-clear
            class="w-36"
            :options="materialTypes"
            :placeholder="$t('material.field.type')"
            @change="loadMaterials(1)"
          />
          <a-select
            v-model:value="filters.status"
            allow-clear
            class="w-28"
            :options="statusOptions"
            :placeholder="$t('material.field.status')"
            @change="loadMaterials(1)"
          />
          <a-select
            v-model:value="batchControlFilter"
            allow-clear
            class="w-32"
            :options="[
              { label: $t('material.filter.batchYes'), value: 'true' },
              { label: $t('material.filter.batchNo'), value: 'false' },
            ]"
            :placeholder="$t('material.filter.batch')"
          />
          <a-select
            v-model:value="purchasableFilter"
            allow-clear
            class="w-32"
            :options="businessFilterOptions"
            :placeholder="$t('material.field.purchasable')"
          />
          <a-select
            v-model:value="producibleFilter"
            allow-clear
            class="w-32"
            :options="businessFilterOptions"
            :placeholder="$t('material.field.producible')"
          />
          <a-select
            v-model:value="sellableFilter"
            allow-clear
            class="w-32"
            :options="businessFilterOptions"
            :placeholder="$t('material.field.sellable')"
          />
          <a-button @click="clearFilters">{{ $t('material.action.reset') }}</a-button>
        </div>

        <a-table
          :columns="tableColumns"
          :data-source="materialPage.items"
          :loading="loading"
          :pagination="false"
          :row-class-name="(record: MaterialItem) => record.id === selectedMaterialId ? 'bg-primary/5' : ''"
          :row-key="(record: MaterialItem) => record.id"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'material_code'">
              <a-button type="link" class="h-auto p-0" @click="selectMaterial(record)">
                {{ record.material_code }}
              </a-button>
            </template>
            <template v-else-if="column.key === 'material_type'">
              {{ materialTypeLabel(record.material_type) }}
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="record.status === 'ACTIVE' ? 'green' : 'default'">
                {{ statusLabel(record.status) }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'specification'">
              {{ record.specification || '-' }}
            </template>
          </template>
        </a-table>
        <div class="mt-3 flex justify-end">
          <a-pagination
            :current="materialPage.page"
            :page-size="materialPage.size"
            :page-size-options="['20', '50', '100']"
            :show-size-changer="true"
            :total="materialPage.total"
            @change="handlePageChange"
          />
        </div>
      </a-card>

      <a-card class="w-96 shrink-0" :loading="detailLoading" :body-style="{ padding: '12px' }">
        <template #title>{{ $t('material.detail') }}</template>
        <template #extra>
          <a-space v-if="selectedMaterial">
            <a-button size="small" @click="editMaterial">{{ $t('material.action.configure') }}</a-button>
            <a-button size="small" :danger="selectedMaterial.status === 'ACTIVE'" @click="toggleStatus">
              {{ selectedMaterial.status === 'ACTIVE' ? $t('material.action.disable') : $t('material.action.enable') }}
            </a-button>
          </a-space>
        </template>
        <a-empty v-if="!selectedMaterial" :description="$t('material.empty.selectMaterial')" />
        <div v-else class="space-y-3 text-sm">
          <div class="rounded bg-muted/40 p-3">
            <div class="text-lg font-semibold">{{ selectedMaterial.material_name }}</div>
            <div class="mt-1 text-muted-foreground">{{ selectedMaterial.material_code }}</div>
            <a-tag class="mt-2" :color="selectedMaterial.status === 'ACTIVE' ? 'green' : 'default'">
              {{ statusLabel(selectedMaterial.status) }}
            </a-tag>
          </div>

          <a-divider class="my-2" />
          <div class="font-medium">{{ $t('material.group.basic') }}</div>
          <a-descriptions :column="1" size="small">
            <a-descriptions-item :label="$t('material.field.shortName')">{{ selectedMaterial.material_short_name || '-' }}</a-descriptions-item>
            <a-descriptions-item :label="$t('material.field.type')">{{ materialTypeLabel(selectedMaterial.material_type) }}</a-descriptions-item>
            <a-descriptions-item :label="$t('material.field.category')">{{ selectedMaterial.category_name || '-' }}</a-descriptions-item>
            <a-descriptions-item :label="$t('material.field.unit')">{{ selectedMaterial.unit_code || '-' }}</a-descriptions-item>
            <a-descriptions-item :label="$t('material.field.specification')">{{ selectedMaterial.specification || '-' }}</a-descriptions-item>
            <a-descriptions-item :label="$t('material.field.model')">{{ selectedMaterial.model || '-' }}</a-descriptions-item>
          </a-descriptions>

          <div class="font-medium">{{ $t('material.group.business') }}</div>
          <div class="flex flex-wrap gap-2">
            <a-tag :color="selectedMaterial.purchasable ? 'blue' : 'default'">{{ $t('material.field.purchasable') }}：{{ yesNo(selectedMaterial.purchasable) }}</a-tag>
            <a-tag :color="selectedMaterial.producible ? 'blue' : 'default'">{{ $t('material.field.producible') }}：{{ yesNo(selectedMaterial.producible) }}</a-tag>
            <a-tag :color="selectedMaterial.sellable ? 'blue' : 'default'">{{ $t('material.field.sellable') }}：{{ yesNo(selectedMaterial.sellable) }}</a-tag>
          </div>

          <div class="font-medium">{{ $t('material.group.traceability') }}</div>
          <a-descriptions :column="1" size="small">
            <a-descriptions-item :label="$t('material.field.batchControl')">{{ yesNo(selectedMaterial.batch_control) }}</a-descriptions-item>
            <a-descriptions-item :label="$t('material.field.serialControl')">{{ yesNo(selectedMaterial.serial_control) }}</a-descriptions-item>
            <a-descriptions-item :label="$t('material.field.shelfLife')">{{ selectedMaterial.shelf_life_days ?? '-' }}</a-descriptions-item>
          </a-descriptions>

          <div class="font-medium">{{ $t('material.group.quality') }}</div>
          <a-tag :color="selectedMaterial.quality_inspection_required ? 'orange' : 'default'">
            {{ $t('material.field.qualityInspection') }}：{{ yesNo(selectedMaterial.quality_inspection_required) }}
          </a-tag>

          <div class="font-medium">{{ $t('material.group.storage') }}</div>
          <a-descriptions :column="1" size="small">
            <a-descriptions-item :label="$t('material.field.defaultWarehouse')">{{ selectedMaterial.warehouse_name || '-' }}</a-descriptions-item>
          </a-descriptions>

          <div class="font-medium">{{ $t('material.group.system') }}</div>
          <a-descriptions :column="1" size="small">
            <a-descriptions-item :label="$t('material.field.createdTime')">{{ selectedMaterial.created_time || '-' }}</a-descriptions-item>
            <a-descriptions-item :label="$t('material.field.updatedTime')">{{ selectedMaterial.updated_time || '-' }}</a-descriptions-item>
          </a-descriptions>
        </div>
      </a-card>
    </div>

    <a-drawer
      v-model:open="drawerOpen"
      :title="formData.id ? $t('material.title.configure') : $t('material.title.create')"
      :width="720"
    >
      <a-form layout="vertical">
        <div class="mb-3 text-base font-medium">{{ $t('material.group.basic') }}</div>
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item :label="$t('material.field.code')" required><a-input v-model:value="formData.material_code" :disabled="Boolean(formData.id)" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('material.field.name')" required><a-input v-model:value="formData.material_name" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('material.field.shortName')"><a-input v-model:value="formData.material_short_name" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('material.field.type')" required><a-select v-model:value="formData.material_type" class="w-full" :options="materialTypes" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('material.field.category')" required><a-tree-select v-model:value="formData.category_id" class="w-full" tree-default-expand-all :tree-data="categorySelectTree" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('material.field.unit')" required><a-select v-model:value="formData.base_unit_id" class="w-full" :options="units.filter((item) => item.status === 'ACTIVE').map((item) => ({ label: `${item.unit_name} (${item.unit_code})`, value: item.id }))" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('material.field.specification')"><a-input v-model:value="formData.specification" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('material.field.model')"><a-input v-model:value="formData.model" /></a-form-item></a-col>
        </a-row>

        <a-divider />
        <div class="mb-3 text-base font-medium">{{ $t('material.group.business') }}</div>
        <a-row :gutter="16">
          <a-col :span="8"><a-form-item :label="$t('material.field.purchasable')"><a-switch v-model:checked="formData.purchasable" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item :label="$t('material.field.producible')"><a-switch v-model:checked="formData.producible" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item :label="$t('material.field.sellable')"><a-switch v-model:checked="formData.sellable" /></a-form-item></a-col>
        </a-row>

        <a-divider />
        <div class="mb-3 text-base font-medium">{{ $t('material.group.traceability') }}</div>
        <a-row :gutter="16">
          <a-col :span="8"><a-form-item :label="$t('material.field.batchControl')"><a-switch v-model:checked="formData.batch_control" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item :label="$t('material.field.serialControl')"><a-switch v-model:checked="formData.serial_control" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item :label="$t('material.field.shelfLife')"><a-input-number v-model:value="formData.shelf_life_days" class="w-full" :min="0" /></a-form-item></a-col>
        </a-row>

        <a-divider />
        <div class="mb-3 text-base font-medium">{{ $t('material.group.quality') }}</div>
        <a-form-item :label="$t('material.field.qualityInspection')"><a-switch v-model:checked="formData.quality_inspection_required" /></a-form-item>

        <a-divider />
        <div class="mb-3 text-base font-medium">{{ $t('material.group.storage') }}</div>
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item :label="$t('material.field.defaultWarehouse')"><a-select v-model:value="formData.default_warehouse_id" allow-clear class="w-full" :options="warehouses.map((item) => ({ label: `${item.name} (${item.code})`, value: item.id }))" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('material.field.status')"><a-select v-model:value="formData.status" class="w-full" :options="statusOptions" /></a-form-item></a-col>
        </a-row>
        <a-form-item :label="$t('material.field.remark')"><a-textarea v-model:value="formData.remark" :rows="3" /></a-form-item>
      </a-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <a-button @click="drawerOpen = false">{{ $t('material.action.cancel') }}</a-button>
          <a-button type="primary" :loading="saving" @click="saveMaterial">{{ $t('material.action.save') }}</a-button>
        </div>
      </template>
    </a-drawer>
  </Page>
</template>
