<script lang="ts" setup>
import type { ManufacturingDemoStatus, ManufacturingDemoVerifyResult } from '../api';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import {
  getManufacturingDemoStatusApi,
  runManufacturingDemoApi,
  verifyManufacturingDemoApi,
} from '../api';

const loading = ref(false);
const running = ref(false);
const status = ref<ManufacturingDemoStatus>();
const verification = computed<ManufacturingDemoVerifyResult | undefined>(
  () => status.value?.verification,
);

const steps = [
  ['supplier', '供应商与原材料'],
  ['bom', 'BOM 与工艺路线'],
  ['purchase_order', '采购订单与原料入库'],
  ['work_order', '工单、领料与工序执行'],
  ['finished_lot', '成品批次与完工入库'],
  ['inspection', '成品检验合格'],
  ['sales_order', '销售订单与发货'],
  ['trace_relation', '原料批次到成品批次追溯'],
] as const;

function isCompleted(code: string) {
  return verification.value?.completed_steps.includes(code) ?? false;
}

async function loadStatus() {
  loading.value = true;
  try {
    status.value = await getManufacturingDemoStatusApi();
  } finally {
    loading.value = false;
  }
}

async function runDemo() {
  running.value = true;
  try {
    await runManufacturingDemoApi();
    message.success('制造闭环演示已完成');
    await loadStatus();
  } finally {
    running.value = false;
  }
}

async function verifyDemo() {
  loading.value = true;
  try {
    const result = await verifyManufacturingDemoApi();
    status.value = { run: status.value?.run, verification: result };
    message[result.passed ? 'success' : 'warning'](
      result.passed ? '闭环验证通过' : '闭环尚未完成，请运行演示',
    );
  } finally {
    loading.value = false;
  }
}

onMounted(loadStatus);
</script>

<template>
  <Page title="制造演示中心" auto-content-height>
    <a-card :loading="loading" class="mb-3">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div class="text-base font-semibold">完整制造闭环 Happy Path</div>
          <div class="mt-1 text-sm text-gray-500">
            以固定演示编码串联采购、库存、生产、质量、销售与双向追溯。重复执行不会重复建单。
          </div>
        </div>
        <a-space>
          <a-button :loading="loading" @click="verifyDemo">验证闭环</a-button>
          <a-button type="primary" :loading="running" @click="runDemo">运行 / 继续演示</a-button>
        </a-space>
      </div>
    </a-card>

    <a-alert
      v-if="verification"
      class="mb-3"
      :message="verification.passed ? '验证通过：制造闭环完整' : `尚缺少：${verification.missing_steps.join('、') || '无'}`"
      :type="verification.passed ? 'success' : 'warning'"
      show-icon
    />

    <a-card title="闭环步骤" :loading="loading">
      <a-steps direction="vertical" :current="verification?.passed ? steps.length : 0">
        <a-step v-for="[code, title] in steps" :key="code" :title="title">
          <template #description>
            <a-tag :color="isCompleted(code) ? 'green' : 'default'">
              {{ isCompleted(code) ? '已完成' : '待执行' }}
            </a-tag>
          </template>
        </a-step>
      </a-steps>
    </a-card>

    <a-card v-if="status?.run" title="最近演示运行" class="mt-3">
      <a-descriptions :column="2" size="small">
        <a-descriptions-item label="运行单号">{{ status.run.run_no }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="status.run.status === 'COMPLETED' ? 'green' : 'blue'">{{ status.run.status }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="开始时间">{{ status.run.started_at }}</a-descriptions-item>
        <a-descriptions-item label="完成时间">{{ status.run.completed_at || '-' }}</a-descriptions-item>
      </a-descriptions>
    </a-card>
  </Page>
</template>
