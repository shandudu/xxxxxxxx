<script lang="ts" setup>
import type { MaterialOption } from '../../material/api';
import type { LocationItem, WarehouseItem } from '../../warehouse/api';
import type { PurchaseOrder, SupplierOption, SupplierReceipt, SupplierReturn } from '../api';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { message, Modal } from 'antdv-next';

import { $t } from '#/locales';
import { getMaterialOptionsApi } from '../../material/api';
import { getWarehouseListApi, getWarehouseTreeApi } from '../../warehouse/api';
import {
  cancelPurchaseOrderApi,
  confirmPurchaseOrderApi,
  createPurchaseOrderApi,
  createSupplierReceiptApi,
  getPurchaseOrderApi,
  getPurchaseOrdersApi,
  getPurchasingSupplierOptionsApi,
  getSupplierReceiptsApi,
  getSupplierReturnsApi,
} from '../api';

const activeTab = ref('orders');
const loading = ref(false);
const orders = ref<PurchaseOrder[]>([]);
const receipts = ref<SupplierReceipt[]>([]);
const returns = ref<SupplierReturn[]>([]);
const suppliers = ref<SupplierOption[]>([]);
const materials = ref<MaterialOption[]>([]);
const warehouses = ref<WarehouseItem[]>([]);
const locations = ref<LocationItem[]>([]);
const selectedOrder = ref<PurchaseOrder>();
const orderVisible = ref(false);
const receiptVisible = ref(false);
const saving = ref(false);
const orderForm = ref<Record<string, any>>({});
const receiptForm = ref<Record<string, any>>({});

const supplierMap = computed(() => new Map(suppliers.value.map((item) => [item.id, `${item.code} · ${item.name}`])));

function flattenLocations(nodes: any[]): LocationItem[] {
  return nodes.flatMap((node) => [
    ...(node.node_type === 'AREA' ? [] : [{ id: node.id, warehouse_id: 0, area_id: 0, location_code: node.code, location_name: node.name, location_type: node.node_type, location_level: 1, status: node.status, storage_enabled: node.storage_enabled, mixed_material_allowed: false, mixed_lot_allowed: false, sort_no: 0 } as LocationItem]),
    ...flattenLocations(node.children ?? []),
  ]);
}

async function loadOptions() {
  [suppliers.value, materials.value, warehouses.value] = await Promise.all([
    getPurchasingSupplierOptionsApi(), getMaterialOptionsApi(), getWarehouseListApi(),
  ]);
  const trees = await Promise.all(warehouses.value.map((item) => getWarehouseTreeApi(item.id)));
  locations.value = trees.flatMap((tree, index) => flattenLocations(tree.children).map((item) => ({ ...item, warehouse_id: warehouses.value[index]?.id ?? 0 })));
}

async function loadData() {
  loading.value = true;
  try {
    [orders.value, receipts.value, returns.value] = await Promise.all([getPurchaseOrdersApi(), getSupplierReceiptsApi(), getSupplierReturnsApi()]);
    if (selectedOrder.value) selectedOrder.value = orders.value.find((item) => item.id === selectedOrder.value?.id);
  } finally { loading.value = false; }
}

async function selectOrder(item: PurchaseOrder) {
  selectedOrder.value = await getPurchaseOrderApi(item.id);
}

function openOrder() {
  orderForm.value = { supplier_id: undefined, currency: 'CNY', material_id: undefined, ordered_quantity: 1, unit_price: undefined, remark: '' };
  orderVisible.value = true;
}

async function saveOrder() {
  saving.value = true;
  try {
    const { material_id, ordered_quantity, unit_price, ...header } = orderForm.value;
    const created = await createPurchaseOrderApi({ ...header, lines: [{ material_id, ordered_quantity, unit_price }] });
    orders.value.unshift(created);
    selectedOrder.value = created;
    orderVisible.value = false;
    message.success($t('purchasing.created'));
  } finally { saving.value = false; }
}

async function confirmOrder(item: PurchaseOrder) {
  const updated = await confirmPurchaseOrderApi(item.id);
  await loadData();
  selectedOrder.value = updated;
  message.success($t('purchasing.confirmed'));
}

function cancelOrder(item: PurchaseOrder) {
  Modal.confirm({ title: $t('purchasing.cancel'), async onOk() {
    selectedOrder.value = await cancelPurchaseOrderApi(item.id);
    await loadData();
    message.success($t('purchasing.cancelled'));
  }});
}

function openReceipt() {
  const order = selectedOrder.value;
  const line = order?.lines.find((item) => Number(item.received_quantity) < Number(item.ordered_quantity));
  if (!order || !line || !['CONFIRMED', 'PARTIALLY_RECEIVED'].includes(order.status)) {
    message.warning($t('purchasing.selectOrder'));
    return;
  }
  receiptForm.value = {
    purchase_order_id: order.id,
    purchase_order_line_id: line.id,
    material_label: `${line.material_code_snapshot} · ${line.material_name_snapshot}`,
    quantity: Number(line.ordered_quantity) - Number(line.received_quantity),
    warehouse_id: undefined, location_id: undefined, lot_no: '', supplier_lot_no: '', remark: '',
  };
  receiptVisible.value = true;
}

function locationOptions(warehouseId?: number) {
  return locations.value.filter((item) => item.warehouse_id === warehouseId && item.storage_enabled).map((item) => ({ label: `${item.location_code} · ${item.location_name}`, value: item.id }));
}

async function saveReceipt() {
  saving.value = true;
  try {
    const { purchase_order_id, purchase_order_line_id, material_label: _materialLabel, ...line } = receiptForm.value;
    await createSupplierReceiptApi({ purchase_order_id, remark: line.remark, lines: [{ purchase_order_line_id, ...line, lot_no: line.lot_no || undefined, supplier_lot_no: line.supplier_lot_no || undefined }] });
    receiptVisible.value = false;
    await loadData();
    if (purchase_order_id) selectedOrder.value = await getPurchaseOrderApi(purchase_order_id);
    activeTab.value = 'receipts';
    message.success($t('purchasing.received'));
  } finally { saving.value = false; }
}

onMounted(async () => { await loadOptions(); await loadData(); });
</script>

<template>
  <Page :title="$t('purchasing.menu')">
    <div class="flex h-full min-h-0 gap-4">
      <a-card class="min-w-0 flex-1" :bordered="false">
        <div class="mb-4 flex gap-2"><a-button type="primary" @click="openOrder">{{ $t('purchasing.createOrder') }}</a-button><a-button @click="openReceipt">{{ $t('purchasing.receive') }}</a-button><a-button @click="loadData">{{ $t('purchasing.refresh') }}</a-button></div>
        <a-tabs v-model:active-key="activeTab">
          <a-tab-pane key="orders" :tab="$t('purchasing.orders')">
            <a-table :loading="loading" :data-source="orders" row-key="id" :pagination="{ pageSize: 20 }" @row="(record: PurchaseOrder) => ({ onClick: () => selectOrder(record) })">
              <a-table-column :title="$t('purchasing.orderNo')" data-index="purchase_order_no" />
              <a-table-column :title="$t('purchasing.supplier')" data-index="supplier_name_snapshot" />
              <a-table-column :title="$t('purchasing.status')" data-index="status" />
              <a-table-column :title="$t('purchasing.currency')" data-index="currency" />
              <a-table-column :title="$t('purchasing.remark')" data-index="remark" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="receipts" :tab="$t('purchasing.receipts')">
            <a-table :loading="loading" :data-source="receipts" row-key="id" :pagination="{ pageSize: 20 }">
              <a-table-column :title="$t('purchasing.receiptNo')" data-index="receipt_no" />
              <a-table-column :title="$t('purchasing.supplier')" data-index="supplier_name_snapshot" />
              <a-table-column :title="$t('purchasing.status')" data-index="status" />
              <a-table-column :title="$t('inventory.occurredAt')" data-index="created_time" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="returns" :tab="$t('purchasing.returns')">
            <a-table :loading="loading" :data-source="returns" row-key="id" :pagination="{ pageSize: 20 }">
              <a-table-column :title="$t('purchasing.returnNo')" data-index="return_no" />
              <a-table-column :title="$t('purchasing.supplier')" data-index="supplier_name_snapshot" />
              <a-table-column title="NCR" data-index="ncr_id" />
              <a-table-column :title="$t('purchasing.status')" data-index="status" />
              <a-table-column :title="$t('inventory.occurredAt')" data-index="created_time" />
            </a-table>
          </a-tab-pane>
        </a-tabs>
      </a-card>

      <a-card class="w-[430px] shrink-0" :bordered="false" :title="selectedOrder?.purchase_order_no ?? $t('purchasing.orders')">
        <a-empty v-if="!selectedOrder" :description="$t('purchasing.selectOrder')" />
        <template v-else>
          <a-descriptions :column="1" size="small"><a-descriptions-item :label="$t('purchasing.supplier')">{{ supplierMap.get(selectedOrder.supplier_id) ?? selectedOrder.supplier_name_snapshot }}</a-descriptions-item><a-descriptions-item :label="$t('purchasing.status')"><a-tag>{{ selectedOrder.status }}</a-tag></a-descriptions-item><a-descriptions-item :label="$t('purchasing.currency')">{{ selectedOrder.currency }}</a-descriptions-item></a-descriptions>
          <div class="my-3 flex gap-2"><a-button v-if="selectedOrder.status === 'DRAFT'" type="primary" @click="confirmOrder(selectedOrder)">{{ $t('purchasing.confirm') }}</a-button><a-button v-if="['DRAFT', 'CONFIRMED'].includes(selectedOrder.status)" danger @click="cancelOrder(selectedOrder)">{{ $t('purchasing.cancel') }}</a-button><a-button v-if="['CONFIRMED', 'PARTIALLY_RECEIVED'].includes(selectedOrder.status)" @click="openReceipt">{{ $t('purchasing.receive') }}</a-button></div>
          <a-table :data-source="selectedOrder.lines" row-key="id" size="small" :pagination="false"><a-table-column :title="$t('purchasing.material')" data-index="material_name_snapshot" /><a-table-column :title="$t('purchasing.orderedQuantity')" data-index="ordered_quantity" /><a-table-column :title="$t('purchasing.receivedQuantity')" data-index="received_quantity" /></a-table>
        </template>
      </a-card>
    </div>

    <a-modal v-model:open="orderVisible" :title="$t('purchasing.createOrder')" :confirm-loading="saving" @ok="saveOrder">
      <a-form layout="vertical" :model="orderForm"><a-form-item :label="$t('purchasing.supplier')" required><a-select v-model:value="orderForm.supplier_id" show-search :options="suppliers.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item><a-form-item :label="$t('purchasing.material')" required><a-select v-model:value="orderForm.material_id" show-search :options="materials.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item><a-row :gutter="16"><a-col :span="12"><a-form-item :label="$t('purchasing.orderedQuantity')" required><a-input-number v-model:value="orderForm.ordered_quantity" class="w-full" :min="0.000001" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('purchasing.unitPrice')"><a-input-number v-model:value="orderForm.unit_price" class="w-full" :min="0" /></a-form-item></a-col></a-row><a-form-item :label="$t('purchasing.remark')"><a-textarea v-model:value="orderForm.remark" /></a-form-item></a-form>
    </a-modal>

    <a-modal v-model:open="receiptVisible" :title="$t('purchasing.receive')" :confirm-loading="saving" @ok="saveReceipt">
      <a-form layout="vertical" :model="receiptForm"><a-form-item :label="$t('purchasing.material')"><a-input :value="receiptForm.material_label" disabled /></a-form-item><a-form-item :label="$t('purchasing.receiptQuantity')" required><a-input-number v-model:value="receiptForm.quantity" class="w-full" :min="0.000001" /></a-form-item><a-form-item :label="$t('purchasing.warehouse')" required><a-select v-model:value="receiptForm.warehouse_id" :options="warehouses.map((item) => ({ label: `${item.warehouse_code} · ${item.warehouse_name}`, value: item.id }))" @change="receiptForm.location_id = undefined" /></a-form-item><a-form-item :label="$t('purchasing.location')" required><a-select v-model:value="receiptForm.location_id" show-search :options="locationOptions(receiptForm.warehouse_id)" /></a-form-item><a-row :gutter="16"><a-col :span="12"><a-form-item :label="$t('purchasing.lotNo')"><a-input v-model:value="receiptForm.lot_no" /></a-form-item></a-col><a-col :span="12"><a-form-item :label="$t('purchasing.supplierLotNo')"><a-input v-model:value="receiptForm.supplier_lot_no" /></a-form-item></a-col></a-row><a-form-item :label="$t('purchasing.remark')"><a-textarea v-model:value="receiptForm.remark" /></a-form-item></a-form>
    </a-modal>
  </Page>
</template>
