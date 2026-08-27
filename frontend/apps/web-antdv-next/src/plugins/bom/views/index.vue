<script lang="ts" setup>
import type { MaterialOption } from '../../material/api';
import type {
  BomInput,
  BomItem,
  BomItemInput,
  BomItemRecord,
  BomStatus,
  BomTreeNode,
  MaterialRequirement,
} from '../api';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import { $t } from '#/locales';

import { getMaterialOptionsApi } from '../../material/api';
import {
  activateBomApi,
  calculateBomApi,
  copyBomApi,
  createBomApi,
  createBomItemApi,
  deactivateBomApi,
  deleteBomItemApi,
  getBomApi,
  getBomListApi,
  getBomTreeApi,
  setDefaultBomApi,
  updateBomApi,
  updateBomItemApi,
  validateBomApi,
} from '../api';

interface BomPage {
  items: BomItemRecord[];
  total: number;
}

interface TreeViewNode {
  key: string;
  title: string;
  children: TreeViewNode[];
}

const products = ref<MaterialOption[]>([]);
const components = ref<MaterialOption[]>([]);
const selectedProductId = ref<number>();
const selectedBomId = ref<number>();
const boms = ref<BomPage>({ items: [], total: 0 });
const selectedBom = ref<BomItemRecord>();
const treeData = ref<TreeViewNode[]>([]);
const requirements = ref<MaterialRequirement[]>([]);
const productKeyword = ref('');
const componentKeyword = ref('');
const bomKeyword = ref('');
const loading = ref(false);
const detailLoading = ref(false);
const saving = ref(false);
const bomModalOpen = ref(false);
const itemModalOpen = ref(false);
const copyModalOpen = ref(false);
const calculateModalOpen = ref(false);
const viewMode = ref<'list' | 'tree'>('list');
const validation = ref<{ valid: boolean; errors: string[] }>();
const bomForm = ref<BomInput>(emptyBomForm());
const editingBomId = ref<number>();
const itemForm = ref<BomItemInput>(emptyItemForm());
const editingItemId = ref<number>();
const copyForm = ref({ new_bom_code: '', new_version: '', effective_from: '', effective_to: '' });
const productionQuantity = ref<number>(1);
const calculating = ref(false);

function emptyBomForm(): BomInput {
  return {
    bom_code: '',
    product_material_id: selectedProductId.value ?? 0,
    bom_version: 'V1.0',
    base_quantity: 1,
    effective_from: '',
    effective_to: '',
    remark: '',
  };
}

function emptyItemForm(): BomItemInput {
  return {
    line_no: 10,
    component_material_id: 0,
    quantity: 1,
    loss_rate: 0,
    fixed_loss_qty: 0,
    is_optional: false,
    remark: '',
    sort_no: 0,
  };
}

const filteredProducts = computed(() => {
  const keyword = productKeyword.value.trim().toLowerCase();
  if (!keyword) return products.value;
  return products.value.filter((item) => `${item.code} ${item.name} ${item.specification ?? ''}`.toLowerCase().includes(keyword));
});

const filteredComponents = computed(() => {
  const keyword = componentKeyword.value.trim().toLowerCase();
  if (!keyword) return components.value;
  return components.value.filter((item) => `${item.code} ${item.name} ${item.specification ?? ''}`.toLowerCase().includes(keyword));
});

const selectedProduct = computed(() => products.value.find((item) => item.id === selectedProductId.value));
const itemColumns = computed(() => [
  { title: $t('bom.field.lineNo'), dataIndex: 'line_no', key: 'line_no', width: 60 },
  { title: $t('bom.field.component'), dataIndex: 'component', key: 'component' },
  { title: $t('bom.field.quantity'), dataIndex: 'quantity', key: 'quantity', width: 110 },
  { title: $t('bom.field.lossRate'), dataIndex: 'loss_rate', key: 'loss_rate', width: 100 },
  { title: $t('bom.field.fixedLoss'), dataIndex: 'fixed_loss_qty', key: 'fixed_loss_qty', width: 100 },
  { title: $t('bom.field.planned'), key: 'planned', width: 120 },
  { title: $t('bom.field.action'), key: 'action', width: 120 },
]);
const requirementColumns = computed(() => [
  { title: $t('bom.field.component'), dataIndex: 'material_code', key: 'material_code' },
  { title: $t('bom.field.standardRequired'), key: 'standard' },
  { title: $t('bom.field.plannedRequired'), key: 'planned' },
]);

function statusLabel(status: BomStatus) {
  return $t(`bom.status.${status}`);
}

function statusColor(status: BomStatus) {
  return status === 'ACTIVE' ? 'green' : status === 'DRAFT' ? 'blue' : 'default';
}

function numberValue(value: number | string | undefined) {
  return Number(value ?? 0);
}

function formatDate(value?: string) {
  return value ? value.slice(0, 16).replace('T', ' ') : $t('bom.common.longTerm');
}

function cleanDate(value?: string) {
  return value?.trim() || undefined;
}

function buildTree(nodes: BomTreeNode[]): TreeViewNode[] {
  return nodes.map((node) => ({
    key: String(node.material_id),
    title: `${node.material_name} (${node.material_code}) × ${node.quantity} ${node.unit}`,
    children: buildTree(node.children ?? []),
  }));
}

async function loadProducts() {
  products.value = await getMaterialOptionsApi({ producible: true });
  components.value = await getMaterialOptionsApi();
  if (!selectedProductId.value && products.value[0]) selectedProductId.value = products.value[0].id;
  if (selectedProductId.value) await loadBoms(selectedProductId.value);
}

async function loadBoms(productId: number) {
  loading.value = true;
  try {
    boms.value = await getBomListApi({
      page: 1,
      size: 100,
      product_material_id: productId,
      keyword: bomKeyword.value.trim() || undefined,
    });
    const selected = boms.value.items.find((item) => item.id === selectedBomId.value) ?? boms.value.items[0];
    if (selected) await selectBom(selected.id);
    else {
      selectedBomId.value = undefined;
      selectedBom.value = undefined;
      treeData.value = [];
    }
  } finally {
    loading.value = false;
  }
}

async function selectProduct(productId: number) {
  selectedProductId.value = productId;
  selectedBomId.value = undefined;
  await loadBoms(productId);
}

async function selectBom(bomId: number) {
  selectedBomId.value = bomId;
  detailLoading.value = true;
  validation.value = undefined;
  try {
    selectedBom.value = await getBomApi(bomId);
    if (viewMode.value === 'tree') await loadTree();
  } finally {
    detailLoading.value = false;
  }
}

async function loadTree() {
  if (!selectedBomId.value) return;
  const tree = await getBomTreeApi(selectedBomId.value);
  treeData.value = buildTree(tree.children);
}

function openCreateBom() {
  editingBomId.value = undefined;
  bomForm.value = emptyBomForm();
  bomForm.value.product_material_id = selectedProductId.value ?? 0;
  bomModalOpen.value = true;
}

function openEditBom() {
  const bom = selectedBom.value;
  if (!bom || bom.status !== 'DRAFT') return;
  editingBomId.value = bom.id;
  bomForm.value = {
    bom_code: bom.bom_code,
    product_material_id: bom.product_material_id,
    bom_version: bom.bom_version,
    base_quantity: bom.base_quantity,
    effective_from: bom.effective_from?.slice(0, 16) ?? '',
    effective_to: bom.effective_to?.slice(0, 16) ?? '',
    remark: bom.remark ?? '',
  };
  bomModalOpen.value = true;
}

async function saveBom() {
  if (!bomForm.value.bom_code.trim() || !bomForm.value.bom_version.trim() || !bomForm.value.product_material_id) {
    message.warning($t('bom.message.requiredHeader'));
    return;
  }
  saving.value = true;
  try {
    const payload = { ...bomForm.value, effective_from: cleanDate(bomForm.value.effective_from), effective_to: cleanDate(bomForm.value.effective_to) };
    const saved = editingBomId.value
      ? await updateBomApi(editingBomId.value, payload)
      : await createBomApi(payload);
    bomModalOpen.value = false;
    selectedBomId.value = saved.id;
    await loadBoms(saved.product_material_id);
    message.success($t('bom.message.saved'));
  } finally {
    saving.value = false;
  }
}

function openCreateItem() {
  if (!selectedBom.value || selectedBom.value.status !== 'DRAFT') return;
  const maxLine = Math.max(0, ...(selectedBom.value.items ?? []).map((item) => item.line_no));
  itemForm.value = { ...emptyItemForm(), line_no: maxLine + 10 };
  componentKeyword.value = '';
  editingItemId.value = undefined;
  itemModalOpen.value = true;
}

function openEditItem(item: BomItem) {
  if (!selectedBom.value || selectedBom.value.status !== 'DRAFT') return;
  itemForm.value = {
    line_no: item.line_no,
    component_material_id: item.component_material_id,
    quantity: item.quantity,
    unit_id: item.unit_id,
    loss_rate: item.loss_rate,
    fixed_loss_qty: item.fixed_loss_qty,
    is_optional: item.is_optional,
    remark: item.remark ?? '',
    sort_no: item.sort_no,
  };
  editingItemId.value = item.id;
  itemModalOpen.value = true;
}

async function saveItem() {
  if (!selectedBom.value || !itemForm.value.component_material_id || !itemForm.value.quantity) {
    message.warning($t('bom.message.requiredItem'));
    return;
  }
  saving.value = true;
  try {
    if (editingItemId.value) await updateBomItemApi(selectedBom.value.id, editingItemId.value, itemForm.value);
    else await createBomItemApi(selectedBom.value.id, itemForm.value);
    itemModalOpen.value = false;
    await selectBom(selectedBom.value.id);
    message.success($t('bom.message.itemSaved'));
  } finally {
    saving.value = false;
  }
}

async function removeItem(item: BomItem) {
  if (!selectedBom.value) return;
  await deleteBomItemApi(selectedBom.value.id, item.id);
  await selectBom(selectedBom.value.id);
  message.success($t('bom.message.itemDeleted'));
}

async function validateCurrent() {
  if (!selectedBom.value) return;
  validation.value = await validateBomApi(selectedBom.value.id);
  if (validation.value.valid) message.success($t('bom.message.validationPassed'));
  else message.error(validation.value.errors.join(', '));
}

async function activateCurrent() {
  if (!selectedBom.value) return;
  await activateBomApi(selectedBom.value.id);
  await loadBoms(selectedProductId.value!);
  message.success($t('bom.message.activated'));
}

async function deactivateCurrent() {
  if (!selectedBom.value) return;
  await deactivateBomApi(selectedBom.value.id);
  await loadBoms(selectedProductId.value!);
  message.success($t('bom.message.deactivated'));
}

async function setDefaultCurrent() {
  if (!selectedBom.value) return;
  await setDefaultBomApi(selectedBom.value.id);
  await loadBoms(selectedProductId.value!);
  message.success($t('bom.message.defaultSet'));
}

function openCopyBom() {
  if (!selectedBom.value) return;
  copyForm.value = {
    new_bom_code: `${selectedBom.value.bom_code}-COPY`,
    new_version: selectedBom.value.bom_version,
    effective_from: selectedBom.value.effective_from?.slice(0, 16) ?? '',
    effective_to: selectedBom.value.effective_to?.slice(0, 16) ?? '',
  };
  copyModalOpen.value = true;
}

async function copyCurrent() {
  if (!selectedBom.value) return;
  const saved = await copyBomApi(selectedBom.value.id, {
    ...copyForm.value,
    effective_from: cleanDate(copyForm.value.effective_from),
    effective_to: cleanDate(copyForm.value.effective_to),
  });
  copyModalOpen.value = false;
  selectedBomId.value = saved.id;
  await loadBoms(saved.product_material_id);
  message.success($t('bom.message.copied'));
}

async function calculateRequirements() {
  if (!selectedBom.value) return;
  calculating.value = true;
  try {
    requirements.value = await calculateBomApi(selectedBom.value.id, {
      production_quantity: productionQuantity.value,
      explode: false,
    });
    calculateModalOpen.value = false;
  } finally {
    calculating.value = false;
  }
}

onMounted(loadProducts);
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 gap-3">
      <a-card class="w-72 shrink-0" :body-style="{ padding: '12px' }">
        <template #title>{{ $t('bom.productList') }}</template>
        <a-input-search v-model:value="productKeyword" allow-clear class="mb-3" :placeholder="$t('bom.placeholder.product')" />
        <a-empty v-if="filteredProducts.length === 0" :description="$t('bom.empty.noProduct')" />
        <div v-else class="space-y-1 overflow-auto">
          <button
            v-for="item in filteredProducts"
            :key="item.id"
            class="w-full rounded px-3 py-2 text-left transition-colors"
            :class="selectedProductId === item.id ? 'bg-primary/10 text-primary' : 'hover:bg-muted'"
            @click="selectProduct(item.id)"
          >
            <div class="font-medium">{{ item.name }}</div>
            <div class="text-xs text-muted-foreground">{{ item.code }} · {{ item.unit }}</div>
          </button>
        </div>
      </a-card>

      <a-card class="w-[24rem] shrink-0" :body-style="{ padding: '12px' }">
        <template #title>
          <span>{{ $t('bom.versionList') }}</span>
          <span v-if="selectedProduct" class="ml-2 text-xs text-muted-foreground">{{ selectedProduct.code }}</span>
        </template>
        <template #extra><a-button type="primary" size="small" :disabled="!selectedProductId" @click="openCreateBom">{{ $t('bom.action.create') }}</a-button></template>
        <a-input-search v-model:value="bomKeyword" allow-clear class="mb-3" :placeholder="$t('bom.placeholder.bom')" @search="loadBoms(selectedProductId!)" />
        <a-spin :spinning="loading">
          <a-empty v-if="boms.items.length === 0" :description="$t('bom.empty.noBom')" />
          <div v-else class="space-y-2">
            <button
              v-for="bom in boms.items"
              :key="bom.id"
              class="w-full rounded border px-3 py-2 text-left"
              :class="selectedBomId === bom.id ? 'border-primary bg-primary/5' : 'border-transparent hover:bg-muted'"
              @click="selectBom(bom.id)"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="font-medium">{{ bom.bom_version }}</span>
                <a-tag :color="statusColor(bom.status)">{{ statusLabel(bom.status) }}</a-tag>
              </div>
              <div class="mt-1 text-xs text-muted-foreground">{{ bom.bom_code }}</div>
              <div class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                <span>{{ formatDate(bom.effective_from) }} ~ {{ bom.effective_to ? formatDate(bom.effective_to) : $t('bom.common.longTerm') }}</span>
                <a-tag v-if="bom.is_default" color="gold">{{ $t('bom.common.default') }}</a-tag>
              </div>
            </button>
          </div>
        </a-spin>
      </a-card>

      <a-card class="min-w-0 flex-1" :loading="detailLoading" :body-style="{ padding: '12px' }">
        <template #title>
          <span>{{ selectedBom?.bom_code || $t('bom.detail') }}</span>
          <a-tag v-if="selectedBom" class="ml-2" :color="statusColor(selectedBom.status)">{{ statusLabel(selectedBom.status) }}</a-tag>
        </template>
        <template #extra>
          <a-space wrap v-if="selectedBom">
            <a-button size="small" :disabled="selectedBom.status !== 'DRAFT'" @click="openEditBom">{{ $t('bom.action.edit') }}</a-button>
            <a-button size="small" @click="openCopyBom">{{ $t('bom.action.copy') }}</a-button>
            <a-button size="small" @click="validateCurrent">{{ $t('bom.action.validate') }}</a-button>
            <a-button v-if="selectedBom.status === 'DRAFT'" type="primary" size="small" @click="activateCurrent">{{ $t('bom.action.activate') }}</a-button>
            <a-button v-if="selectedBom.status === 'ACTIVE'" danger size="small" @click="deactivateCurrent">{{ $t('bom.action.deactivate') }}</a-button>
            <a-button v-if="selectedBom.status === 'ACTIVE' && !selectedBom.is_default" size="small" @click="setDefaultCurrent">{{ $t('bom.action.setDefault') }}</a-button>
          </a-space>
        </template>

        <a-empty v-if="!selectedBom" :description="$t('bom.empty.selectBom')" />
        <div v-else class="space-y-3">
          <div class="rounded bg-muted/40 p-3">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-lg font-semibold">{{ selectedBom.product.name }}</span>
              <a-tag color="blue">{{ selectedBom.product.code }}</a-tag>
              <a-tag v-if="selectedBom.is_default" color="gold">{{ $t('bom.common.default') }}</a-tag>
            </div>
            <div class="mt-2 grid grid-cols-2 gap-2 text-sm text-muted-foreground md:grid-cols-4">
              <span>{{ $t('bom.field.version') }}：{{ selectedBom.bom_version }}</span>
              <span>{{ $t('bom.field.baseQuantity') }}：{{ selectedBom.base_quantity }} {{ selectedBom.product.unit }}</span>
              <span>{{ $t('bom.field.effectiveFrom') }}：{{ formatDate(selectedBom.effective_from) }}</span>
              <span>{{ $t('bom.field.effectiveTo') }}：{{ selectedBom.effective_to ? formatDate(selectedBom.effective_to) : $t('bom.common.longTerm') }}</span>
            </div>
          </div>

          <div v-if="validation && !validation.valid" class="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {{ validation.errors.join(' · ') }}
          </div>
          <div v-if="validation?.valid" class="rounded border border-green-200 bg-green-50 p-3 text-sm text-green-700">{{ $t('bom.message.validationPassed') }}</div>

          <div class="flex items-center justify-between">
            <span class="font-medium">{{ $t('bom.structure') }}（{{ selectedBom.items?.length ?? 0 }}）</span>
            <a-space>
              <a-button size="small" :disabled="selectedBom.status !== 'DRAFT'" @click="openCreateItem">{{ $t('bom.action.addItem') }}</a-button>
              <a-button size="small" @click="calculateModalOpen = true">{{ $t('bom.action.calculate') }}</a-button>
              <a-radio-group v-model:value="viewMode" size="small" @change="viewMode === 'tree' && loadTree()">
                <a-radio-button value="list">{{ $t('bom.view.list') }}</a-radio-button>
                <a-radio-button value="tree">{{ $t('bom.view.tree') }}</a-radio-button>
              </a-radio-group>
            </a-space>
          </div>

          <a-table v-if="viewMode === 'list'" :columns="itemColumns" :data-source="selectedBom.items" :pagination="false" :row-key="(record: BomItem) => record.id" size="small">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'component'"><span class="font-medium">{{ record.component.name }}</span><span class="ml-2 text-xs text-muted-foreground">{{ record.component.code }}</span></template>
              <template v-else-if="column.key === 'quantity'">{{ record.quantity }} {{ record.component.unit }}</template>
              <template v-else-if="column.key === 'lossRate'">{{ record.loss_rate }}%</template>
              <template v-else-if="column.key === 'fixedLoss'">{{ record.fixed_loss_qty }} {{ record.component.unit }}</template>
              <template v-else-if="column.key === 'planned'">{{ (numberValue(record.quantity) * (1 + numberValue(record.loss_rate) / 100) + numberValue(record.fixed_loss_qty)).toFixed(6) }} {{ record.component.unit }}</template>
              <template v-else-if="column.key === 'action'"><a-space><a-button type="link" size="small" :disabled="selectedBom.status !== 'DRAFT'" @click="openEditItem(record)">{{ $t('bom.action.edit') }}</a-button><a-popconfirm :title="$t('bom.message.confirmDelete')" :disabled="selectedBom.status !== 'DRAFT'" @confirm="removeItem(record)"><a-button type="link" danger size="small" :disabled="selectedBom.status !== 'DRAFT'">{{ $t('bom.action.delete') }}</a-button></a-popconfirm></a-space></template>
            </template>
          </a-table>
          <a-tree v-else :tree-data="treeData" default-expand-all block-node />

          <div v-if="requirements.length" class="rounded border p-3">
            <div class="mb-2 font-medium">{{ $t('bom.requirements') }}（{{ productionQuantity }}）</div>
            <a-table :columns="requirementColumns" :data-source="requirements" :pagination="false" :row-key="(record: MaterialRequirement) => record.material_id" size="small">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'material_code'">{{ record.material_name }} ({{ record.material_code }})</template>
                <template v-else-if="column.key === 'standard'">{{ record.standard_required_qty }} {{ record.unit }}</template>
                <template v-else-if="column.key === 'planned'">{{ record.planned_required_qty }} {{ record.unit }}</template>
              </template>
            </a-table>
          </div>
        </div>
      </a-card>
    </div>

    <a-modal v-model:open="bomModalOpen" :confirm-loading="saving" :title="editingBomId ? $t('bom.title.edit') : $t('bom.title.create')" width="680px" @ok="saveBom">
      <a-form layout="vertical"><a-row :gutter="16">
        <a-col :span="12"><a-form-item :label="$t('bom.field.bomCode')" required><a-input v-model:value="bomForm.bom_code" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item :label="$t('bom.field.version')" required><a-input v-model:value="bomForm.bom_version" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item :label="$t('bom.field.product')" required><a-select v-model:value="bomForm.product_material_id" class="w-full" :options="products.map((item) => ({ label: `${item.name} (${item.code})`, value: item.id }))" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item :label="$t('bom.field.baseQuantity')" required><a-input-number v-model:value="bomForm.base_quantity" class="w-full" :min="0.000001" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item :label="$t('bom.field.effectiveFrom')"><a-input v-model:value="bomForm.effective_from" type="datetime-local" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item :label="$t('bom.field.effectiveTo')"><a-input v-model:value="bomForm.effective_to" type="datetime-local" /></a-form-item></a-col>
      </a-row><a-form-item :label="$t('bom.field.remark')"><a-textarea v-model:value="bomForm.remark" :rows="3" /></a-form-item></a-form>
    </a-modal>

    <a-modal v-model:open="itemModalOpen" :confirm-loading="saving" :title="editingItemId ? $t('bom.title.editItem') : $t('bom.title.addItem')" width="680px" @ok="saveItem">
      <a-form layout="vertical"><a-row :gutter="16">
        <a-col :span="8"><a-form-item :label="$t('bom.field.lineNo')" required><a-input-number v-model:value="itemForm.line_no" class="w-full" :min="1" /></a-form-item></a-col>
        <a-col :span="16"><a-form-item :label="$t('bom.field.component')" required><a-input v-model:value="componentKeyword" class="mb-2" :placeholder="$t('bom.placeholder.component')" /><a-select v-model:value="itemForm.component_material_id" show-search class="w-full" :options="filteredComponents.filter((item) => item.id !== selectedProductId).map((item) => ({ label: `${item.name} (${item.code}) · ${item.unit}`, value: item.id }))" /></a-form-item></a-col>
        <a-col :span="8"><a-form-item :label="$t('bom.field.quantity')" required><a-input-number v-model:value="itemForm.quantity" class="w-full" :min="0.000001" /></a-form-item></a-col>
        <a-col :span="8"><a-form-item :label="$t('bom.field.lossRate')"><a-input-number v-model:value="itemForm.loss_rate" class="w-full" :min="0" :step="0.1" /></a-form-item></a-col>
        <a-col :span="8"><a-form-item :label="$t('bom.field.fixedLoss')"><a-input-number v-model:value="itemForm.fixed_loss_qty" class="w-full" :min="0" /></a-form-item></a-col>
      </a-row><a-form-item :label="$t('bom.field.remark')"><a-textarea v-model:value="itemForm.remark" :rows="2" /></a-form-item><a-form-item :label="$t('bom.field.optional')"><a-switch v-model:checked="itemForm.is_optional" /></a-form-item></a-form>
    </a-modal>

    <a-modal v-model:open="copyModalOpen" :title="$t('bom.title.copy')" @ok="copyCurrent">
      <a-form layout="vertical"><a-form-item :label="$t('bom.field.bomCode')" required><a-input v-model:value="copyForm.new_bom_code" /></a-form-item><a-form-item :label="$t('bom.field.version')" required><a-input v-model:value="copyForm.new_version" /></a-form-item><a-form-item :label="$t('bom.field.effectiveFrom')"><a-input v-model:value="copyForm.effective_from" type="datetime-local" /></a-form-item><a-form-item :label="$t('bom.field.effectiveTo')"><a-input v-model:value="copyForm.effective_to" type="datetime-local" /></a-form-item></a-form>
    </a-modal>

    <a-modal v-model:open="calculateModalOpen" :title="$t('bom.title.calculate')" @ok="calculateRequirements">
      <a-form layout="vertical"><a-form-item :label="$t('bom.field.productionQuantity')" required><a-input-number v-model:value="productionQuantity" class="w-full" :min="0.000001" /></a-form-item></a-form>
    </a-modal>
  </Page>
</template>
