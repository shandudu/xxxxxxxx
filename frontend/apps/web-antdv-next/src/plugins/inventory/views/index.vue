<script lang="ts" setup>
import type { InventoryBalance, StockMovement, StockTransaction } from '../api';
import type { LocationItem, WarehouseItem } from '../../warehouse/api';
import type { MaterialOption } from '../../material/api';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { message, Modal } from 'antdv-next';

import { $t } from '#/locales';
import { getMaterialOptionsApi } from '../../material/api';
import { getWarehouseListApi, getWarehouseTreeApi } from '../../warehouse/api';
import {
  createStockMovementApi,
  getInventoryBalancesApi,
  getStockTransactionsApi,
  getStockMovementsApi,
  postStockAdjustmentApi,
  postStockMovementApi,
} from '../api';

type FormKind = 'adjustment' | 'movement';

const activeTab = ref('balance');
const loading = ref(false);
const balances = ref<InventoryBalance[]>([]);
const transactions = ref<StockTransaction[]>([]);
const movements = ref<StockMovement[]>([]);
const materials = ref<MaterialOption[]>([]);
const warehouses = ref<WarehouseItem[]>([]);
const locations = ref<LocationItem[]>([]);
const formVisible = ref(false);
const formLoading = ref(false);
const formKind = ref<FormKind>('movement');
const formData = ref<Record<string, any>>({});
const filters = ref<Record<string, any>>({ positive_only: true });

const materialMap = computed(() => new Map(materials.value.map((item) => [item.id, `${item.code} · ${item.name}`])));
const warehouseMap = computed(() => new Map(warehouses.value.map((item) => [item.id, `${item.warehouse_code} · ${item.warehouse_name}`])));
const locationMap = computed(() => new Map(locations.value.map((item) => [item.id, `${item.location_code} · ${item.location_name}`])));

function flattenLocations(nodes: any[]): LocationItem[] {
  return nodes.flatMap((node) => {
    const current = node.node_type === 'AREA' ? [] : [{
      id: node.id,
      warehouse_id: 0,
      area_id: 0,
      location_code: node.code,
      location_name: node.name,
      location_type: node.node_type,
      location_level: 1,
      status: node.status,
      storage_enabled: node.storage_enabled,
      mixed_material_allowed: false,
      mixed_lot_allowed: false,
      sort_no: 0,
    } as LocationItem];
    return [...current, ...flattenLocations(node.children ?? [])];
  });
}

async function loadOptions() {
  [materials.value, warehouses.value] = await Promise.all([
    getMaterialOptionsApi(),
    getWarehouseListApi(),
  ]);
  const trees = await Promise.all(warehouses.value.map((item) => getWarehouseTreeApi(item.id)));
  locations.value = trees.flatMap((tree, index) => flattenLocations(tree.children).map((item) => ({
    ...item,
    warehouse_id: warehouses.value[index]?.id ?? 0,
  })));
}

async function loadData() {
  loading.value = true;
  try {
    [balances.value, transactions.value, movements.value] = await Promise.all([
      getInventoryBalancesApi(filters.value),
      getStockTransactionsApi({ material_id: filters.value.material_id, limit: 500 }),
      getStockMovementsApi(),
    ]);
  } finally {
    loading.value = false;
  }
}

function locationOptions(warehouseId?: number) {
  return locations.value
    .filter((item) => item.warehouse_id === warehouseId && item.storage_enabled)
    .map((item) => ({ label: locationMap.value.get(item.id), value: item.id }));
}

function openMovement() {
  formKind.value = 'movement';
  formData.value = {
    movement_no: '',
    material_id: undefined,
    lot_id: undefined,
    from_warehouse_id: undefined,
    from_location_id: undefined,
    to_warehouse_id: undefined,
    to_location_id: undefined,
    quantity: 1,
    remark: '',
  };
  formVisible.value = true;
}

function openAdjustment() {
  formKind.value = 'adjustment';
  formData.value = {
    idempotency_key: `UI-${Date.now()}`,
    material_id: undefined,
    lot_id: undefined,
    warehouse_id: undefined,
    location_id: undefined,
    quantity_delta: 0,
    reference_no: '',
    remark: '',
  };
  formVisible.value = true;
}

async function submitForm() {
  formLoading.value = true;
  try {
    if (formKind.value === 'movement') {
      const { movement_no, remark, ...line } = formData.value;
      const created = await createStockMovementApi({ movement_no: movement_no || undefined, remark, lines: [line] });
      movements.value.unshift(created);
      message.success($t('inventory.saved'));
      activeTab.value = 'movement';
    } else {
      await postStockAdjustmentApi(formData.value);
      message.success($t('inventory.adjusted'));
      await loadData();
    }
    formVisible.value = false;
  } finally {
    formLoading.value = false;
  }
}

function postMovement(item: StockMovement) {
  Modal.confirm({
    title: $t('inventory.confirmPost'),
    async onOk() {
      const posted = await postStockMovementApi(item.id);
      const index = movements.value.findIndex((row) => row.id === item.id);
      if (index >= 0) movements.value[index] = posted;
      message.success($t('inventory.posted'));
      await loadData();
    },
  });
}

function displayMaterial(id: number) { return materialMap.value.get(id) ?? `#${id}`; }
function displayWarehouse(id: number) { return warehouseMap.value.get(id) ?? `#${id}`; }
function displayLocation(id: number) { return locationMap.value.get(id) ?? `#${id}`; }

onMounted(async () => {
  await loadOptions();
  await loadData();
});
</script>

<template>
  <Page :title="$t('inventory.menu')">
    <a-card :bordered="false">
      <div class="mb-4 flex flex-wrap items-center gap-3">
        <a-select v-model:value="filters.material_id" allow-clear show-search :placeholder="$t('inventory.material')" style="width: 260px" :options="materials.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" />
        <a-select v-model:value="filters.warehouse_id" allow-clear :placeholder="$t('inventory.warehouse')" style="width: 240px" :options="warehouses.map((item) => ({ label: `${item.warehouse_code} · ${item.warehouse_name}`, value: item.id }))" />
        <a-button type="primary" @click="loadData">{{ $t('inventory.refresh') }}</a-button>
        <a-button @click="openMovement">{{ $t('inventory.createMovement') }}</a-button>
        <a-button @click="openAdjustment">{{ $t('inventory.adjustment') }}</a-button>
      </div>

      <a-tabs v-model:active-key="activeTab">
        <a-tab-pane key="balance" :tab="$t('inventory.balance')">
          <a-table :loading="loading" :data-source="balances" row-key="id" :pagination="{ pageSize: 20 }">
            <a-table-column :title="$t('inventory.material')" key="material" :custom-render="({ record }: any) => displayMaterial(record.material_id)" />
            <a-table-column :title="$t('inventory.lot')" data-index="lot_id" />
            <a-table-column :title="$t('inventory.warehouse')" key="warehouse" :custom-render="({ record }: any) => displayWarehouse(record.warehouse_id)" />
            <a-table-column :title="$t('inventory.location')" key="location" :custom-render="({ record }: any) => displayLocation(record.location_id)" />
            <a-table-column :title="$t('inventory.quantity')" data-index="quantity" />
            <a-table-column :title="$t('inventory.reserved')" data-index="reserved_quantity" />
            <a-table-column :title="$t('inventory.available')" key="available" :custom-render="({ record }: any) => Number(record.quantity) - Number(record.reserved_quantity)" />
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="ledger" :tab="$t('inventory.ledger')">
          <a-table :loading="loading" :data-source="transactions" row-key="id" :pagination="{ pageSize: 20 }">
            <a-table-column :title="$t('inventory.type')" data-index="transaction_type" />
            <a-table-column :title="$t('inventory.material')" key="material" :custom-render="({ record }: any) => displayMaterial(record.material_id)" />
            <a-table-column :title="$t('inventory.location')" key="location" :custom-render="({ record }: any) => displayLocation(record.location_id)" />
            <a-table-column :title="$t('inventory.quantityDelta')" data-index="quantity_delta" />
            <a-table-column :title="$t('inventory.balanceAfter')" data-index="balance_after" />
            <a-table-column :title="$t('inventory.reference')" data-index="reference_no" />
            <a-table-column :title="$t('inventory.occurredAt')" data-index="occurred_at" />
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="movement" :tab="$t('inventory.movement')">
          <a-table :data-source="movements" row-key="id">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'actions'">
                <a-button v-if="record.status === 'DRAFT'" type="link" @click="postMovement(record)">
                  {{ $t('inventory.post') }}
                </a-button>
              </template>
            </template>
            <a-table-column :title="$t('inventory.movementNo')" data-index="movement_no" />
            <a-table-column :title="$t('inventory.status')" data-index="status" />
            <a-table-column :title="$t('inventory.remark')" data-index="remark" />
            <a-table-column title="" key="actions" />
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <a-modal v-model:open="formVisible" :title="formKind === 'movement' ? $t('inventory.createMovement') : $t('inventory.adjustment')" :confirm-loading="formLoading" width="760px" @ok="submitForm">
      <a-form layout="vertical" :model="formData">
        <template v-if="formKind === 'movement'">
          <a-form-item :label="$t('inventory.movementNo')"><a-input v-model:value="formData.movement_no" /></a-form-item>
          <a-row :gutter="16"><a-col :span="12"><a-form-item :label="$t('inventory.material')" required><a-select v-model:value="formData.material_id" show-search :options="materials.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('inventory.lot')"><a-input-number v-model:value="formData.lot_id" class="w-full" :min="1" /></a-form-item></a-col></a-row>
          <a-row :gutter="16"><a-col :span="12"><a-form-item :label="$t('inventory.fromWarehouse')" required><a-select v-model:value="formData.from_warehouse_id" :options="warehouses.map((item) => ({ label: `${item.warehouse_code} · ${item.warehouse_name}`, value: item.id }))" @change="formData.from_location_id = undefined" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('inventory.fromLocation')" required><a-select v-model:value="formData.from_location_id" show-search :options="locationOptions(formData.from_warehouse_id)" /></a-form-item></a-col></a-row>
          <a-row :gutter="16"><a-col :span="12"><a-form-item :label="$t('inventory.toWarehouse')" required><a-select v-model:value="formData.to_warehouse_id" :options="warehouses.map((item) => ({ label: `${item.warehouse_code} · ${item.warehouse_name}`, value: item.id }))" @change="formData.to_location_id = undefined" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('inventory.toLocation')" required><a-select v-model:value="formData.to_location_id" show-search :options="locationOptions(formData.to_warehouse_id)" /></a-form-item></a-col></a-row>
          <a-form-item :label="$t('inventory.quantity')" required><a-input-number v-model:value="formData.quantity" class="w-full" :min="0.000001" /></a-form-item>
        </template>
        <template v-else>
          <a-form-item :label="$t('inventory.idempotencyKey')" required><a-input v-model:value="formData.idempotency_key" /></a-form-item>
          <a-row :gutter="16"><a-col :span="12"><a-form-item :label="$t('inventory.material')" required><a-select v-model:value="formData.material_id" show-search :options="materials.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('inventory.lot')"><a-input-number v-model:value="formData.lot_id" class="w-full" :min="1" /></a-form-item></a-col></a-row>
          <a-row :gutter="16"><a-col :span="12"><a-form-item :label="$t('inventory.warehouse')" required><a-select v-model:value="formData.warehouse_id" :options="warehouses.map((item) => ({ label: `${item.warehouse_code} · ${item.warehouse_name}`, value: item.id }))" @change="formData.location_id = undefined" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('inventory.location')" required><a-select v-model:value="formData.location_id" show-search :options="locationOptions(formData.warehouse_id)" /></a-form-item></a-col></a-row>
          <a-form-item :label="$t('inventory.quantityDelta')" required><a-input-number v-model:value="formData.quantity_delta" class="w-full" /></a-form-item>
        </template>
        <a-form-item :label="$t('inventory.remark')"><a-textarea v-model:value="formData.remark" :rows="3" /></a-form-item>
      </a-form>
    </a-modal>
  </Page>
</template>
