<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import type { DeliveryDashboard, DeliveryPerformance, SalesOrder, Shipment } from '../api';
import {
  deliverShipmentApi,
  getDeliveryDashboardApi,
  getOrderDeliveryPerformanceApi,
  getSalesOrderApi,
  getSalesOrdersApi,
  getShipmentsApi,
  recalculateDeliveryApi,
} from '../api';

const loading = ref(false);
const dashboard = ref<DeliveryDashboard>();
const orders = ref<SalesOrder[]>([]);
const shipments = ref<Shipment[]>([]);
const selected = ref<SalesOrder>();
const performance = ref<DeliveryPerformance[]>([]);

const selectedShipments = computed(() =>
  shipments.value.filter((item) => item.sales_order_id === selected.value?.id),
);

async function load() {
  loading.value = true;
  try {
    const [summary, confirmed, partial, shipped, shipmentRows] = await Promise.all([
      getDeliveryDashboardApi(),
      getSalesOrdersApi({ status: 'CONFIRMED' }),
      getSalesOrdersApi({ status: 'PARTIALLY_SHIPPED' }),
      getSalesOrdersApi({ status: 'SHIPPED' }),
      getShipmentsApi(),
    ]);
    dashboard.value = summary;
    orders.value = [...confirmed, ...partial, ...shipped];
    shipments.value = shipmentRows;
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

async function select(order: SalesOrder) {
  selected.value = await getSalesOrderApi(order.id);
  performance.value = await getOrderDeliveryPerformanceApi(order.id);
}

async function recalculate() {
  const result = await recalculateDeliveryApi();
  message.success(`已重算 ${result.assessed_order_count} 张订单、${result.assessed_line_count} 行交付绩效`);
  await load();
}

async function deliver(shipment: Shipment) {
  await deliverShipmentApi(shipment.id);
  message.success(`发货单 ${shipment.shipment_no} 已登记签收`);
  await load();
}

onMounted(load);
</script>

<template>
  <Page title="销售订单交付执行 / OTIF" auto-content-height>
    <div v-if="dashboard" class="mb-4 grid grid-cols-4 gap-3">
      <a-card size="small" title="交付订单">{{ dashboard.order_count }}</a-card>
      <a-card size="small" title="OTIF 率">{{ dashboard.otif_rate }}%</a-card>
      <a-card size="small" title="在途订单">{{ dashboard.in_transit_order_count }}</a-card>
      <a-card size="small" title="延期订单">{{ dashboard.delayed_order_count }}</a-card>
    </div>
    <a-card class="mb-4" :bordered="false">
      <template #extra>
        <a-button type="primary" @click="recalculate">重算 OTIF 绩效</a-button>
      </template>
      <a-table
        :data-source="orders"
        :loading="loading"
        row-key="id"
        size="small"
        :pagination="{ pageSize: 15 }"
        @row="(row: SalesOrder) => ({ onClick: () => select(row) })"
      >
        <a-table-column title="订单号" data-index="sales_order_no" />
        <a-table-column title="客户" data-index="customer_name_snapshot" />
        <a-table-column title="订单状态" data-index="status" />
        <a-table-column title="要求交期" data-index="requested_delivery_at" />
      </a-table>
    </a-card>
    <div class="flex min-h-0 gap-4">
      <a-card class="min-w-0 flex-1" :bordered="false" :title="selected?.sales_order_no || '订单行 OTIF 明细'">
        <a-empty v-if="!selected" />
        <a-table v-else :data-source="performance" row-key="id" size="small" :pagination="false">
          <a-table-column title="订单行" data-index="sales_order_line_id" />
          <a-table-column title="承诺交期" data-index="promised_delivery_at" />
          <a-table-column title="实际签收" data-index="actual_delivery_at" />
          <a-table-column title="订单量" data-index="ordered_quantity" />
          <a-table-column title="已发量" data-index="shipped_quantity" />
          <a-table-column title="状态" data-index="otif_status" />
          <a-table-column title="延期原因" data-index="delay_reason" />
        </a-table>
      </a-card>
      <a-card class="w-[520px] shrink-0" :bordered="false" title="发货 / 签收执行">
        <a-empty v-if="!selectedShipments.length" description="该订单暂无发货单" />
        <a-list v-else :data-source="selectedShipments" size="small">
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta :title="item.shipment_no" :description="'发货时间：' + item.created_time" />
              <template #actions>
                <a-tag v-if="item.status === 'DELIVERED'" color="green">已签收</a-tag>
                <a-button v-else type="link" size="small" @click="deliver(item)">登记签收</a-button>
              </template>
            </a-list-item>
          </template>
        </a-list>
      </a-card>
    </div>
  </Page>
</template>
