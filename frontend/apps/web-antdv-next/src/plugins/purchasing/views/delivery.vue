<script lang="ts" setup>
import { onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import type { PurchaseDeliveryDashboard, PurchaseDeliveryPerformance, PurchaseOrder } from '../api';
import {
  confirmPurchaseOrderApi,
  getPurchaseOrderApi,
  getPurchaseOrderDeliveryPerformanceApi,
  getPurchaseDeliveryDashboardApi,
  getPurchaseOrdersApi,
  recalculatePurchaseDeliveryApi,
} from '../api';

const loading = ref(false);
const dashboard = ref<PurchaseDeliveryDashboard>();
const orders = ref<PurchaseOrder[]>([]);
const selected = ref<PurchaseOrder>();
const performance = ref<PurchaseDeliveryPerformance[]>([]);
const confirmedDeliveryAt = ref<string>();

function statusColor(status: string) {
  return ({ OTIF: 'green', LATE: 'red', LATE_AND_NOT_IN_FULL: 'red', OPEN: 'blue' } as Record<string, string>)[status] ?? 'default';
}

async function load() {
  loading.value = true;
  try {
    const [summary, draft, confirmed, partial, received] = await Promise.all([
      getPurchaseDeliveryDashboardApi(),
      getPurchaseOrdersApi({ status: 'DRAFT' }),
      getPurchaseOrdersApi({ status: 'CONFIRMED' }),
      getPurchaseOrdersApi({ status: 'PARTIALLY_RECEIVED' }),
      getPurchaseOrdersApi({ status: 'RECEIVED' }),
    ]);
    dashboard.value = summary;
    orders.value = [...draft, ...confirmed, ...partial, ...received];
    if (selected.value) {
      const current = orders.value.find((item) => item.id === selected.value?.id);
      if (current) await select(current);
    } else if (orders.value[0]) {
      await select(orders.value[0]);
    }
  } finally {
    loading.value = false;
  }
}

async function select(item: PurchaseOrder) {
  selected.value = await getPurchaseOrderApi(item.id);
  performance.value = await getPurchaseOrderDeliveryPerformanceApi(item.id);
  confirmedDeliveryAt.value = selected.value.lines[0]?.supplier_confirmed_delivery_at;
}

async function confirm() {
  if (!selected.value) return;
  selected.value = await confirmPurchaseOrderApi(selected.value.id, {
    supplier_confirmed_delivery_at: confirmedDeliveryAt.value || undefined,
  });
  await load();
  message.success('采购订单已确认，供应商承诺交期已保存');
}

async function recalculate() {
  const result = await recalculatePurchaseDeliveryApi();
  message.success(`已重算 ${result.assessed_order_count} 张采购订单、${result.assessed_line_count} 行 OTIF`);
  await load();
}

onMounted(load);
</script>

<template>
  <Page title="供应商交期协同 / 采购 OTIF" auto-content-height>
    <div v-if="dashboard" class="mb-4 grid grid-cols-5 gap-3">
      <a-card size="small" title="采购订单">{{ dashboard.order_count }}</a-card>
      <a-card size="small" title="供应商">{{ dashboard.supplier_count }}</a-card>
      <a-card size="small" title="采购 OTIF 率">{{ dashboard.otif_rate }}%</a-card>
      <a-card size="small" title="延期数量">{{ dashboard.delayed_quantity }}</a-card>
      <a-card size="small" title="销售缺料影响">{{ dashboard.shortage_impact_quantity }}</a-card>
    </div>
    <a-card class="mb-4" :bordered="false">
      <template #extra><a-button type="primary" @click="recalculate">重算采购 OTIF</a-button></template>
      <a-table
        :data-source="orders"
        :loading="loading"
        row-key="id"
        size="small"
        :pagination="{ pageSize: 15 }"
        @row="(row: PurchaseOrder) => ({ onClick: () => select(row) })"
      >
        <a-table-column title="采购单号" data-index="purchase_order_no" />
        <a-table-column title="供应商" data-index="supplier_name_snapshot" />
        <a-table-column title="状态" data-index="status" />
        <a-table-column title="下单时间" data-index="created_time" />
      </a-table>
    </a-card>
    <div class="flex min-h-0 gap-4">
      <a-card class="min-w-0 flex-1" :bordered="false" :title="selected?.purchase_order_no || '采购交付明细'">
        <a-empty v-if="!selected" />
        <template v-else>
          <a-space class="mb-3">
            <a-date-picker v-model:value="confirmedDeliveryAt" value-format="YYYY-MM-DDTHH:mm:ssZ" placeholder="供应商承诺交期" />
            <a-button v-if="selected.status === 'DRAFT'" type="primary" @click="confirm">确认采购 / 保存承诺</a-button>
          </a-space>
          <a-table :data-source="performance" row-key="id" size="small" :pagination="false">
            <a-table-column title="订单行" data-index="purchase_order_line_id" />
            <a-table-column title="要求交期" data-index="requested_delivery_at" />
            <a-table-column title="供应商承诺" data-index="supplier_confirmed_delivery_at" />
            <a-table-column title="实际到货" data-index="actual_delivery_at" />
            <a-table-column title="订单量" data-index="ordered_quantity" />
            <a-table-column title="已收量" data-index="received_quantity" />
            <a-table-column title="状态" data-index="otif_status" />
            <a-table-column title="延期天数" data-index="days_late" />
            <a-table-column title="销售缺料影响" data-index="shortage_impact_quantity" />
            <a-table-column title="影响订单数" data-index="impacted_sales_order_count" />
          </a-table>
        </template>
      </a-card>
      <a-card class="w-[340px] shrink-0" :bordered="false" title="供应商 OTIF">
        <a-list v-if="dashboard?.supplier_otif.length" :data-source="dashboard.supplier_otif" size="small">
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta :title="'供应商 #' + item.supplier_id" :description="'订单行 ' + item.line_count + '，OTIF ' + item.otif_line_count" />
              <template #actions><a-tag :color="statusColor(item.otif_rate >= 95 ? 'OTIF' : 'LATE')">{{ item.otif_rate }}%</a-tag></template>
            </a-list-item>
          </template>
        </a-list>
        <a-empty v-else description="暂无供应商绩效" />
      </a-card>
    </div>
  </Page>
</template>
