<script lang="ts" setup>
import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  getAlertInboxApi,
  type AlertInboxItem,
  type AlertInboxSummary,
} from '#/api';

const loading = ref(false);
const source = ref<string>();
const status = ref<string>();
const summary = ref<AlertInboxSummary>({
  total: 0,
  open_count: 0,
  overdue_count: 0,
  by_source: {},
  items: [],
});

const sourceOptions = [
  { label: '全部来源', value: undefined },
  { label: '质量', value: 'QUALITY' },
  { label: 'Andon', value: 'ANDON' },
  { label: '库存补货', value: 'INVENTORY' },
  { label: '销售交付', value: 'SALES' },
  { label: '供应商交付', value: 'PURCHASING' },
];

const statusOptions = [
  { label: '全部状态', value: undefined },
  { label: '逾期', value: 'OVERDUE' },
  { label: '处理中', value: 'IN_PROGRESS' },
  { label: '待处理', value: 'OPEN' },
  { label: '缺料', value: 'SHORTAGE' },
  { label: '重订货', value: 'REORDER' },
  { label: '交付延期', value: 'LATE' },
];

const columns = [
  { title: '来源', dataIndex: 'source', key: 'source', width: 100 },
  { title: '编号', dataIndex: 'code', key: 'code', width: 180 },
  { title: '告警', dataIndex: 'title', key: 'title' },
  { title: '级别', dataIndex: 'severity', key: 'severity', width: 100 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
  { title: '截止时间', dataIndex: 'due_at', key: 'due_at', width: 190 },
  { title: '处理入口', key: 'action', width: 120 },
];

function severityColor(severity: AlertInboxItem['severity']) {
  return severity === 'CRITICAL'
    ? 'red'
    : severity === 'HIGH'
      ? 'orange'
      : severity === 'MEDIUM'
        ? 'gold'
        : 'blue';
}

async function fetchAlerts() {
  loading.value = true;
  try {
    summary.value = await getAlertInboxApi({
      source: source.value,
      status: status.value,
      limit: 500,
    });
  } finally {
    loading.value = false;
  }
}

onMounted(fetchAlerts);
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full flex-col gap-4">
      <div class="grid grid-cols-1 gap-3 md:grid-cols-4">
        <a-card size="small" title="告警总数">
          <a-statistic :value="summary.total" />
        </a-card>
        <a-card size="small" title="待处理">
          <a-statistic :value="summary.open_count" />
        </a-card>
        <a-card size="small" title="已逾期">
          <a-statistic :value="summary.overdue_count" :value-style="{ color: '#cf1322' }" />
        </a-card>
        <a-card size="small" title="来源数">
          <a-statistic :value="Object.keys(summary.by_source).length" />
        </a-card>
      </div>

      <a-card class="min-h-0 flex-1" :loading="loading" title="统一预警中心">
        <template #extra>
          <div class="flex gap-2">
            <a-select v-model:value="source" allow-clear placeholder="来源" :options="sourceOptions" />
            <a-select v-model:value="status" allow-clear placeholder="状态" :options="statusOptions" />
            <a-button type="primary" @click="fetchAlerts">刷新</a-button>
          </div>
        </template>
        <a-table :columns="columns" :data-source="summary.items" :pagination="{ pageSize: 12 }" row-key="alert_id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'severity'">
              <a-tag :color="severityColor(record.severity)">{{ record.severity }}</a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" :href="record.action_path" target="_blank">打开业务</a-button>
            </template>
          </template>
        </a-table>
      </a-card>
    </div>
  </Page>
</template>
