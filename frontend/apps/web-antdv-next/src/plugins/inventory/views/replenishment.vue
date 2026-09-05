<script lang="ts" setup>
import { onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import type { SupplierOption } from '../../purchasing/api';
import type { ReplenishmentDashboard, ReplenishmentSuggestion } from '../api';
import { getPurchasingSupplierOptionsApi } from '../../purchasing/api';
import {
  firmReplenishmentApi,
  generateReplenishmentApi,
  getReplenishmentDashboardApi,
  getReplenishmentSuggestionsApi,
  releaseReplenishmentApi,
} from '../api';
import { getConfigurableTip } from '#/utils/dict';

const loading = ref(false);
const dashboard = ref<ReplenishmentDashboard>();
const suggestions = ref<ReplenishmentSuggestion[]>([]);
const suppliers = ref<SupplierOption[]>([]);
const tip = (key: string, params: Record<string, unknown> = {}) =>
  getConfigurableTip(`inventory.replenishment.${key}`, `inventory.replenishmentTips.${key}`, params);

async function load() {
  loading.value = true;
  try {
    [dashboard.value, suggestions.value, suppliers.value] = await Promise.all([
      getReplenishmentDashboardApi(),
      getReplenishmentSuggestionsApi(),
      getPurchasingSupplierOptionsApi(),
    ]);
  } finally {
    loading.value = false;
  }
}

async function generate() {
  const rows = await generateReplenishmentApi();
  message.success(tip('generated', { count: rows.length }));
  await load();
}

async function firm(row: ReplenishmentSuggestion) {
  await firmReplenishmentApi(row.id);
  message.success(tip('firmed'));
  await load();
}

async function release(row: ReplenishmentSuggestion) {
  if (row.order_type === 'PURCHASE' && !suppliers.value[0]) {
    message.warning(tip('noSupplier'));
    return;
  }
  await releaseReplenishmentApi(row.id, {
    supplier_id: row.order_type === 'PURCHASE' ? suppliers.value[0]?.id : undefined,
  });
  message.success(tip('released'));
  await load();
}

onMounted(load);
</script>

<template>
  <Page title="安全库存 / 自动补货建议" auto-content-height>
    <div v-if="dashboard" class="mb-4 grid grid-cols-4 gap-3">
      <a-card size="small" title="策略物料">{{ dashboard.policy_count }}</a-card>
      <a-card size="small" title="待执行建议">{{ dashboard.suggestion_count }}</a-card>
      <a-card size="small" title="短缺预警">{{ dashboard.shortage_count }}</a-card>
      <a-card size="small" title="建议补货量">{{ dashboard.total_suggested_quantity }}</a-card>
    </div>
    <a-card :bordered="false">
      <template #extra><a-button type="primary" @click="generate">重新计算补货建议</a-button></template>
      <a-table :data-source="suggestions" :loading="loading" row-key="id" size="small" :pagination="{ pageSize: 20 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button v-if="record.status === 'SUGGESTED'" type="link" size="small" @click="firm(record)">固定</a-button>
              <a-button v-if="record.status === 'SUGGESTED' || record.status === 'FIRM'" type="link" size="small" @click="release(record)">释放</a-button>
            </a-space>
          </template>
        </template>
        <a-table-column title="建议单号" data-index="suggestion_no" />
        <a-table-column title="物料编码" data-index="material_code_snapshot" />
        <a-table-column title="物料名称" data-index="material_name_snapshot" />
        <a-table-column title="类型" data-index="order_type" />
        <a-table-column title="现有可用" data-index="projected_available_quantity" />
        <a-table-column title="需求量" data-index="demand_quantity" />
        <a-table-column title="安全库存" data-index="safety_stock" />
        <a-table-column title="建议量" data-index="suggested_quantity" />
        <a-table-column title="预警" data-index="alert_level" />
        <a-table-column title="状态" data-index="status" />
        <a-table-column title="建议到期" data-index="due_date" />
        <a-table-column title="操作" key="action" />
      </a-table>
    </a-card>
  </Page>
</template>
