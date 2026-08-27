<script lang="ts" setup>
import { onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';
import type { PromiseAssessment, PromiseDashboard, SalesOrder } from '../api';
import { assessOrderPromiseApi, getOrderPromiseApi, getPromiseDashboardApi, getSalesOrderApi, getSalesOrdersApi } from '../api';

const loading = ref(false);
const dashboard = ref<PromiseDashboard>();
const orders = ref<SalesOrder[]>([]);
const selected = ref<SalesOrder>();
const assessments = ref<PromiseAssessment[]>([]);

async function load() {
  loading.value = true;
  try {
    [dashboard.value, orders.value] = await Promise.all([getPromiseDashboardApi(), getSalesOrdersApi({ status: 'CONFIRMED' })]);
  } finally { loading.value = false; }
}
async function select(order: SalesOrder) {
  selected.value = await getSalesOrderApi(order.id);
  assessments.value = await getOrderPromiseApi(order.id);
}
async function assess() {
  if (!selected.value) return;
  assessments.value = await assessOrderPromiseApi(selected.value.id);
  dashboard.value = await getPromiseDashboardApi();
  message.success('ATP/CTP 评估已刷新');
}
onMounted(load);
</script>

<template>
  <Page title="订单 ATP/CTP 交期评估">
    <div v-if="dashboard" class="mb-4 grid grid-cols-4 gap-3">
      <a-card size="small" title="评估订单">{{ dashboard.order_count }}</a-card>
      <a-card size="small" title="交期风险">{{ dashboard.delayed_order_count }}</a-card>
      <a-card size="small" title="缺料总量">{{ dashboard.total_shortage_quantity }}</a-card>
      <a-card size="small" title="产能缺口">{{ dashboard.total_capacity_shortage_quantity }}</a-card>
    </div>
    <div class="flex min-h-0 gap-4">
      <a-card class="min-w-0 flex-1" :bordered="false">
        <a-table :loading="loading" :data-source="orders" row-key="id" @row="(row: SalesOrder) => ({ onClick: () => select(row) })">
          <a-table-column title="订单号" data-index="sales_order_no" /><a-table-column title="客户" data-index="customer_name_snapshot" /><a-table-column title="状态" data-index="status" />
        </a-table>
      </a-card>
      <a-card class="w-[720px] shrink-0" :bordered="false" :title="selected?.sales_order_no || '订单交期明细'">
        <a-empty v-if="!selected" />
        <template v-else>
          <div class="mb-3 flex gap-2"><a-button type="primary" @click="assess">重新评估 ATP/CTP</a-button></div>
          <a-descriptions :column="1" size="small"><a-descriptions-item label="要求交期">{{ selected.requested_delivery_at || '默认订单创建后 7 天' }}</a-descriptions-item><a-descriptions-item label="客户">{{ selected.customer_name_snapshot }}</a-descriptions-item></a-descriptions>
          <a-table class="mt-3" :data-source="assessments" row-key="id" size="small" :pagination="false">
            <a-table-column title="物料" data-index="material_id" /><a-table-column title="ATP" data-index="atp_quantity" /><a-table-column title="CTP" data-index="ctp_quantity" /><a-table-column title="缺料" data-index="shortage_quantity" /><a-table-column title="产能缺口" data-index="capacity_shortage_quantity" /><a-table-column title="风险" data-index="risk_status" /><a-table-column title="承诺交期" data-index="promised_delivery_at" />
          </a-table>
        </template>
      </a-card>
    </div>
  </Page>
</template>
