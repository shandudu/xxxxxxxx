<script lang="ts" setup>
import type {
  AreaItem,
  LocationGenerateParams,
  LocationStatus,
  LocationSearchResult,
  WarehouseItem,
  WarehouseTreeNode,
  WarehouseType,
} from '../api';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';
import { $t } from '#/locales';

import {
  createAreaApi,
  createLocationApi,
  createWarehouseApi,
  generateLocationsApi,
  getAreasApi,
  getLocationApi,
  getWarehouseListApi,
  getWarehouseTreeApi,
  moveLocationApi,
  previewLocationGenerateApi,
  searchLocationsApi,
  updateAreaApi,
  updateLocationApi,
  updateLocationStatusApi,
  updateWarehouseApi,
} from '../api';

type FormKind = 'area' | 'generate' | 'location' | 'move' | 'warehouse';

interface ViewTreeNode extends WarehouseTreeNode {
  areaId?: number;
  key: string;
  parentId?: number;
  title: string;
  children: ViewTreeNode[];
}

const warehouseTypes = computed<{ label: string; value: WarehouseType }[]>(() => [
  { label: $t('warehouse.warehouseType.RAW_MATERIAL'), value: 'RAW_MATERIAL' },
  { label: $t('warehouse.warehouseType.WIP'), value: 'WIP' },
  { label: $t('warehouse.warehouseType.FINISHED_PRODUCT'), value: 'FINISHED_PRODUCT' },
  { label: $t('warehouse.warehouseType.LINE_SIDE'), value: 'LINE_SIDE' },
  { label: $t('warehouse.warehouseType.QUALITY_HOLD'), value: 'QUALITY_HOLD' },
  { label: $t('warehouse.warehouseType.SCRAP'), value: 'SCRAP' },
  { label: $t('warehouse.warehouseType.VIRTUAL'), value: 'VIRTUAL' },
]);

const warehouseStatuses = computed(() => [
  { label: $t('warehouse.status.ACTIVE'), value: 'ACTIVE' },
  { label: $t('warehouse.status.DISABLED'), value: 'DISABLED' },
]);

const areaTypes = computed(() => [
  { label: $t('warehouse.areaType.NORMAL'), value: 'NORMAL' },
  { label: $t('warehouse.areaType.RECEIVING'), value: 'RECEIVING' },
  { label: $t('warehouse.areaType.SHIPPING'), value: 'SHIPPING' },
  { label: $t('warehouse.areaType.QUALITY'), value: 'QUALITY' },
  { label: $t('warehouse.areaType.QUARANTINE'), value: 'QUARANTINE' },
  { label: $t('warehouse.areaType.PRODUCTION'), value: 'PRODUCTION' },
]);

const areaStatuses = warehouseStatuses;

const locationStatuses = computed<{ label: string; value: LocationStatus }[]>(() => [
  { label: $t('warehouse.status.AVAILABLE'), value: 'AVAILABLE' },
  { label: $t('warehouse.status.LOCKED'), value: 'LOCKED' },
  { label: $t('warehouse.status.DISABLED'), value: 'DISABLED' },
]);

const locationTypes = computed(() => [
  { label: $t('warehouse.locationType.ZONE'), value: 'ZONE' },
  { label: $t('warehouse.locationType.AISLE'), value: 'AISLE' },
  { label: $t('warehouse.locationType.RACK'), value: 'RACK' },
  { label: $t('warehouse.locationType.LEVEL'), value: 'LEVEL' },
  { label: $t('warehouse.locationType.BIN'), value: 'BIN' },
  { label: $t('warehouse.locationType.FLOOR'), value: 'FLOOR' },
  { label: $t('warehouse.locationType.BUFFER'), value: 'BUFFER' },
  { label: $t('warehouse.locationType.LINE'), value: 'LINE' },
  { label: $t('warehouse.locationType.WORKSTATION'), value: 'WORKSTATION' },
  { label: $t('warehouse.locationType.TEMP'), value: 'TEMP' },
]);

const warehouses = ref<WarehouseItem[]>([]);
const selectedWarehouseId = ref<number>();
const treeData = ref<ViewTreeNode[]>([]);
const selectedKeys = ref<string[]>([]);
const expandedKeys = ref<string[]>([]);
const selectedNode = ref<ViewTreeNode>();
const loading = ref(false);
const searchKeyword = ref('');
const searchResults = ref<LocationSearchResult[]>([]);

const formVisible = ref(false);
const formKind = ref<FormKind>('warehouse');
const formLoading = ref(false);
const formData = ref<Record<string, any>>({});

const selectedWarehouse = computed(() =>
  warehouses.value.find((item) => item.id === selectedWarehouseId.value),
);

const modalTitle = computed(() => {
  if (formKind.value === 'warehouse') return formData.value.id ? $t('warehouse.title.editWarehouse') : $t('warehouse.title.createWarehouse');
  if (formKind.value === 'area') return formData.value.id ? $t('warehouse.title.editArea') : $t('warehouse.title.createArea');
  if (formKind.value === 'location') return formData.value.id ? $t('warehouse.title.editLocation') : $t('warehouse.title.createLocation');
  if (formKind.value === 'generate') return $t('warehouse.title.generateLocations');
  return $t('warehouse.title.moveLocation');
});

function warehouseTypeLabel(type: WarehouseType) {
  return $t(`warehouse.warehouseType.${type}`);
}

function nodeTypeLabel(type: string) {
  return type === 'AREA'
    ? $t('warehouse.nodeType.AREA')
    : $t(`warehouse.locationType.${type}`);
}

function statusLabel(status: string) {
  return $t(`warehouse.status.${status}`);
}

function nodeKey(type: string, id: number) {
  return `${type}-${id}`;
}

function buildTree(nodes: WarehouseTreeNode[], areaId?: number): ViewTreeNode[] {
  return nodes.map((node) => {
    const currentAreaId = node.node_type === 'AREA' ? node.id : areaId;
    const viewNode: ViewTreeNode = {
      ...node,
      areaId: currentAreaId,
      key: nodeKey(node.node_type, node.id),
      parentId: undefined,
      title: `${node.name} (${node.code})`,
      children: [],
    };
    viewNode.children = buildTree(node.children ?? [], currentAreaId);
    viewNode.children.forEach((child) => {
      child.parentId = node.node_type === 'AREA' ? undefined : node.id;
    });
    return viewNode;
  });
}

async function loadWarehouses() {
  loading.value = true;
  try {
    warehouses.value = await getWarehouseListApi();
    if (!selectedWarehouseId.value && warehouses.value.length > 0) {
      const firstWarehouse = warehouses.value[0];
      if (firstWarehouse) selectedWarehouseId.value = firstWarehouse.id;
    }
    if (selectedWarehouseId.value) await loadTree();
    else treeData.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadTree() {
  if (!selectedWarehouseId.value) return;
  const result = await getWarehouseTreeApi(selectedWarehouseId.value);
  treeData.value = buildTree(result.children);
  expandedKeys.value = treeData.value.map((node) => node.key);
  selectedKeys.value = [];
  selectedNode.value = undefined;
}

async function selectWarehouse(id: number) {
  selectedWarehouseId.value = id;
  await loadTree();
}

function selectNode(keys: (string | number)[], info: { node: unknown }) {
  selectedKeys.value = keys.map(String);
  selectedNode.value = info.node as ViewTreeNode;
}

function openWarehouseConfig(item?: WarehouseItem) {
  formKind.value = 'warehouse';
  formData.value = item
    ? { ...item }
    : {
        warehouse_code: '',
        warehouse_name: '',
        warehouse_type: 'RAW_MATERIAL',
        factory_code: '',
        status: 'ACTIVE',
        allow_inbound: true,
        allow_outbound: true,
        remark: '',
        sort_no: 0,
      };
  formVisible.value = true;
}

async function openAreaConfig(area?: AreaItem) {
  if (!selectedWarehouseId.value) return;
  if (!area && selectedNode.value?.node_type === 'AREA') {
    const areas = await getAreasApi(selectedWarehouseId.value);
    area = areas.find((item) => item.id === selectedNode.value?.id);
  }
  formKind.value = 'area';
  formData.value = area
    ? { ...area }
    : {
        area_code: '',
        area_name: '',
        warehouse_id: selectedWarehouseId.value,
        area_type: 'NORMAL',
        status: 'ACTIVE',
        remark: '',
        sort_no: 0,
      };
  formVisible.value = true;
}

async function openLocationConfig(node?: ViewTreeNode) {
  if (!selectedWarehouseId.value || !node?.areaId) return;
  if (node.node_type !== 'AREA') {
    formData.value = await getLocationApi(node.id);
  } else {
    formData.value = {
      warehouse_id: selectedWarehouseId.value,
      area_id: node.id,
      parent_id: undefined,
      location_code: '',
      location_name: '',
      location_type: 'BIN',
      location_level: 1,
      status: 'AVAILABLE',
      storage_enabled: true,
      capacity_value: undefined,
      capacity_unit: '',
      mixed_material_allowed: false,
      mixed_lot_allowed: false,
      remark: '',
      sort_no: 0,
    };
  }
  formKind.value = 'location';
  formVisible.value = true;
}

function openGenerate() {
  if (!selectedWarehouseId.value || !selectedNode.value?.areaId) return;
  const node = selectedNode.value;
  const areaId = node.areaId;
  if (!areaId) return;
  formKind.value = 'generate';
  formData.value = {
    warehouse_id: selectedWarehouseId.value,
    area_id: node.node_type === 'AREA' ? node.id : areaId,
    parent_id: node.node_type === 'AREA' ? undefined : node.id,
    area_prefix: node.node_type === 'AREA' ? node.code : 'A',
    rack: { start: 1, end: 10, digits: 2 },
    level: { start: 1, end: 5, digits: 2 },
    bin: { start: 1, end: 10, digits: 2 },
    pattern: '{AREA}{RACK}-{LEVEL}-{BIN}',
    location_type: 'BIN',
  } satisfies LocationGenerateParams;
  formVisible.value = true;
}

function openMove() {
  if (!selectedNode.value || selectedNode.value.node_type === 'AREA') return;
  formKind.value = 'move';
  formData.value = { target_parent_id: selectedNode.value.parentId };
  formVisible.value = true;
}

async function submitForm() {
  formLoading.value = true;
  try {
    if (formKind.value === 'warehouse') {
      if (formData.value.id) await updateWarehouseApi(formData.value.id, formData.value);
      else await createWarehouseApi(formData.value);
      message.success($t('warehouse.message.warehouseSaved'));
      formVisible.value = false;
      await loadWarehouses();
      return;
    }
    if (formKind.value === 'area') {
      if (formData.value.id) await updateAreaApi(formData.value.id, formData.value);
      else await createAreaApi(formData.value);
      message.success($t('warehouse.message.areaSaved'));
      formVisible.value = false;
      await loadTree();
      return;
    }
    if (formKind.value === 'location') {
      if (formData.value.id) await updateLocationApi(formData.value.id, formData.value);
      else await createLocationApi(formData.value);
      message.success($t('warehouse.message.locationSaved'));
      formVisible.value = false;
      await loadTree();
      return;
    }
    if (formKind.value === 'move') {
      await moveLocationApi(selectedNode.value!.id, formData.value.target_parent_id || undefined);
      message.success($t('warehouse.message.locationMoved'));
      formVisible.value = false;
      await loadTree();
      return;
    }
    const preview = await previewLocationGenerateApi(formData.value);
    if (preview.conflicts.length > 0) {
      message.error(`${$t('warehouse.message.locationConflict')}: ${preview.conflicts.slice(0, 3).join(', ')}`);
      return;
    }
    await generateLocationsApi(formData.value);
    message.success($t('warehouse.message.locationsGenerated', [preview.count]));
    formVisible.value = false;
    await loadTree();
  } finally {
    formLoading.value = false;
  }
}

async function changeLocationStatus(status: LocationStatus) {
  if (!selectedNode.value || selectedNode.value.node_type === 'AREA') return;
  await updateLocationStatusApi(selectedNode.value.id, status);
  message.success($t('warehouse.message.locationStatusUpdated'));
  await loadTree();
}

async function searchLocations() {
  if (!selectedWarehouseId.value || !searchKeyword.value.trim()) {
    searchResults.value = [];
    return;
  }
  searchResults.value = await searchLocationsApi(
    selectedWarehouseId.value,
    searchKeyword.value.trim(),
  );
  const result = searchResults.value[0];
  if (!result) return;
  expandedKeys.value = result.path_ids
    .map((id) => findTreeNode(id)?.key)
    .filter((key): key is string => Boolean(key));
  const matched = findTreeNode(result.id);
  if (matched) {
    selectedNode.value = matched;
    selectedKeys.value = [matched.key];
  }
}

function findTreeNode(id: number, nodes = treeData.value): ViewTreeNode | undefined {
  for (const node of nodes) {
    if (node.id === id && node.node_type !== 'AREA') return node;
    const found = findTreeNode(id, node.children);
    if (found) return found;
  }
  return undefined;
}

onMounted(loadWarehouses);
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 gap-4">
      <a-card class="w-64 shrink-0" :body-style="{ padding: '12px' }" :title="$t('warehouse.warehouseList')">
        <template #extra>
          <a-space size="small">
            <a-button type="link" size="small" @click="openWarehouseConfig()">{{ $t('warehouse.action.add') }}</a-button>
            <a-button
              type="link"
              size="small"
              :disabled="!selectedWarehouse"
              @click="openWarehouseConfig(selectedWarehouse)"
            >
              {{ $t('warehouse.action.edit') }}
            </a-button>
          </a-space>
        </template>
        <a-spin :spinning="loading">
          <a-empty v-if="warehouses.length === 0" :description="$t('warehouse.empty.noWarehouse')" />
          <div v-else class="space-y-2">
            <button
              v-for="item in warehouses"
              :key="item.id"
              class="w-full rounded px-3 py-2 text-left transition-colors"
              :class="selectedWarehouseId === item.id ? 'bg-primary/10 text-primary' : 'hover:bg-muted'"
              @click="selectWarehouse(item.id)"
            >
              <div class="font-medium">{{ item.warehouse_name }}</div>
              <div class="text-xs text-muted-foreground">
                {{ item.warehouse_code }} · {{ warehouseTypeLabel(item.warehouse_type) }}
              </div>
            </button>
          </div>
        </a-spin>
      </a-card>

      <a-card class="min-w-0 flex-1" :body-style="{ padding: '12px' }">
        <template #title>
          <span>{{ selectedWarehouse?.warehouse_name || $t('warehouse.storageStructure') }}</span>
          <span v-if="selectedWarehouse" class="ml-2 text-sm text-muted-foreground">
            {{ selectedWarehouse.warehouse_code }}
          </span>
        </template>
        <template #extra>
          <a-space>
            <a-input-search
              v-model:value="searchKeyword"
              allow-clear
              :placeholder="$t('warehouse.placeholder.searchLocation')"
              style="width: 180px"
              @search="searchLocations"
            />
            <a-button :disabled="!selectedWarehouseId" @click="openAreaConfig()">
              {{ $t('warehouse.action.configureArea') }}
            </a-button>
            <a-button type="primary" :disabled="!selectedNode?.areaId" @click="openLocationConfig(selectedNode)">
              {{ $t('warehouse.action.configureLocation') }}
            </a-button>
            <a-button :disabled="!selectedNode?.areaId" @click="openGenerate">{{ $t('warehouse.action.generateLocations') }}</a-button>
          </a-space>
        </template>

        <div class="flex h-full min-h-0 gap-4">
          <div class="min-w-0 flex-1 overflow-auto rounded border p-3">
            <a-empty v-if="!selectedWarehouseId" :description="$t('warehouse.empty.configureWarehouseFirst')" />
            <a-empty v-else-if="treeData.length === 0" :description="$t('warehouse.empty.noStructure')" />
            <a-tree
              v-else
              v-model:expanded-keys="expandedKeys"
              :selected-keys="selectedKeys"
              :tree-data="treeData"
              :show-line="true"
              @select="selectNode"
            />
            <div v-if="searchResults.length > 0" class="mt-3 border-t pt-3">
              <div class="mb-2 text-sm font-medium">{{ $t('warehouse.searchResults') }}</div>
              <button
                v-for="item in searchResults"
                :key="item.id"
                class="block w-full rounded px-2 py-1 text-left text-sm hover:bg-muted"
                @click="selectedNode = findTreeNode(item.id)"
              >
                {{ item.location_code }} <span class="text-muted-foreground">{{ item.path }}</span>
              </button>
            </div>
          </div>

          <a-card class="w-80 shrink-0" size="small" :title="$t('warehouse.currentNode')">
            <a-empty v-if="!selectedNode" :description="$t('warehouse.empty.selectNode')" />
            <div v-else class="space-y-3 text-sm">
              <div><span class="text-muted-foreground">{{ $t('warehouse.field.name') }}：</span>{{ selectedNode.name }}</div>
              <div><span class="text-muted-foreground">{{ $t('warehouse.field.code') }}：</span>{{ selectedNode.code }}</div>
              <div><span class="text-muted-foreground">{{ $t('warehouse.field.nodeType') }}：</span>{{ nodeTypeLabel(selectedNode.node_type) }}</div>
              <div>
                <span class="mr-2 text-muted-foreground">{{ $t('warehouse.field.status') }}：</span>
                <a-tag :color="selectedNode.status === 'AVAILABLE' || selectedNode.status === 'ACTIVE' ? 'green' : 'orange'">
                  {{ statusLabel(selectedNode.status) }}
                </a-tag>
              </div>
              <div v-if="selectedNode.node_type !== 'AREA'">
                <span class="mr-2 text-muted-foreground">{{ $t('warehouse.field.storageAllowed') }}：</span>
                <a-tag :color="selectedNode.storage_enabled ? 'green' : 'default'">
                  {{ selectedNode.storage_enabled ? $t('warehouse.common.yes') : $t('warehouse.common.no') }}
                </a-tag>
              </div>
              <a-divider class="my-2" />
              <a-space wrap>
                <a-button v-if="selectedNode.node_type === 'AREA'" @click="openAreaConfig()">
                  {{ $t('warehouse.action.editArea') }}
                </a-button>
                <a-button v-else @click="openLocationConfig(selectedNode)">{{ $t('warehouse.action.editLocation') }}</a-button>
                <a-button v-if="selectedNode.node_type !== 'AREA'" @click="openMove">{{ $t('warehouse.action.moveLocation') }}</a-button>
              </a-space>
              <a-select
                v-if="selectedNode.node_type !== 'AREA'"
                class="w-full"
                :value="selectedNode.status"
                :options="locationStatuses"
                @change="changeLocationStatus"
              />
            </div>
          </a-card>
        </div>
      </a-card>
    </div>

    <a-modal
      v-model:open="formVisible"
      :confirm-loading="formLoading"
      :title="modalTitle"
      width="620px"
      @ok="submitForm"
    >
      <a-form v-if="formKind === 'warehouse'" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.warehouseCode')" required><a-input v-model:value="formData.warehouse_code" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.warehouseName')" required><a-input v-model:value="formData.warehouse_name" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.warehouseType')" required><a-select v-model:value="formData.warehouse_type" class="w-full" :options="warehouseTypes" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.factoryCode')"><a-input v-model:value="formData.factory_code" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.status')"><a-select v-model:value="formData.status" class="w-full" :options="warehouseStatuses" /></a-form-item></a-col>
          <a-col :span="6"><a-form-item :label="$t('warehouse.field.allowInbound')"><a-switch v-model:checked="formData.allow_inbound" /></a-form-item></a-col>
          <a-col :span="6"><a-form-item :label="$t('warehouse.field.allowOutbound')"><a-switch v-model:checked="formData.allow_outbound" /></a-form-item></a-col>
        </a-row>
        <a-form-item :label="$t('warehouse.field.remark')"><a-textarea v-model:value="formData.remark" :rows="3" /></a-form-item>
      </a-form>

      <a-form v-else-if="formKind === 'area'" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.areaCode')" required><a-input v-model:value="formData.area_code" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.areaName')" required><a-input v-model:value="formData.area_name" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.areaType')"><a-select v-model:value="formData.area_type" class="w-full" :options="areaTypes" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.status')"><a-select v-model:value="formData.status" class="w-full" :options="areaStatuses" /></a-form-item></a-col>
        </a-row>
        <a-form-item :label="$t('warehouse.field.remark')"><a-textarea v-model:value="formData.remark" :rows="3" /></a-form-item>
      </a-form>

      <a-form v-else-if="formKind === 'location'" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.locationCode')" required><a-input v-model:value="formData.location_code" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.locationName')" required><a-input v-model:value="formData.location_name" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.locationType')" required><a-select v-model:value="formData.location_type" class="w-full" :options="locationTypes" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.status')"><a-select v-model:value="formData.status" class="w-full" :options="locationStatuses" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item :label="$t('warehouse.field.level')"><a-input-number v-model:value="formData.location_level" class="w-full" :min="1" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item :label="$t('warehouse.field.storageAllowed')"><a-switch v-model:checked="formData.storage_enabled" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item :label="$t('warehouse.field.parentId')"><a-input-number v-model:value="formData.parent_id" class="w-full" /></a-form-item></a-col>
        </a-row>
        <a-form-item :label="$t('warehouse.field.remark')"><a-textarea v-model:value="formData.remark" :rows="3" /></a-form-item>
      </a-form>

      <a-form v-else-if="formKind === 'generate'" layout="vertical">
        <a-alert :message="$t('warehouse.generate.previewHint')" type="info" show-icon class="mb-4" />
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.areaPrefix')"><a-input v-model:value="formData.area_prefix" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item :label="$t('warehouse.field.pattern')"><a-input v-model:value="formData.pattern" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item :label="$t('warehouse.field.rackRange')"><a-space><a-input-number v-model:value="formData.rack.start" :min="0" /><a-input-number v-model:value="formData.rack.end" :min="0" /></a-space></a-form-item></a-col>
          <a-col :span="8"><a-form-item :label="$t('warehouse.field.levelRange')"><a-space><a-input-number v-model:value="formData.level.start" :min="0" /><a-input-number v-model:value="formData.level.end" :min="0" /></a-space></a-form-item></a-col>
          <a-col :span="8"><a-form-item :label="$t('warehouse.field.binRange')"><a-space><a-input-number v-model:value="formData.bin.start" :min="0" /><a-input-number v-model:value="formData.bin.end" :min="0" /></a-space></a-form-item></a-col>
        </a-row>
      </a-form>

      <a-form v-else layout="vertical">
        <a-alert :message="$t('warehouse.move.parentHint')" type="warning" show-icon class="mb-4" />
        <a-form-item :label="$t('warehouse.field.targetParentId')"><a-input-number v-model:value="formData.target_parent_id" class="w-full" /></a-form-item>
      </a-form>
    </a-modal>
  </Page>
</template>
