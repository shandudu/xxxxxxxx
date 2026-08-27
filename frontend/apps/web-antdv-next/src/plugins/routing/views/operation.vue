<script lang="ts" setup>
import type { OperationItem, OperationStatus, OperationType } from '../api';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import { createOperationApi, getOperationApi, getOperationsApi, updateOperationApi, updateOperationStatusApi } from '../api';

const operationTypes: { label: string; value: OperationType }[] = [
  { label: '普通生产工序', value: 'PROCESS' }, { label: '装配', value: 'ASSEMBLY' },
  { label: '检测', value: 'INSPECTION' }, { label: '包装', value: 'PACKAGING' },
  { label: '转运', value: 'TRANSFER' }, { label: '其他', value: 'OTHER' },
];
const statuses: { label: string; value: OperationStatus }[] = [{ label: '启用', value: 'ACTIVE' }, { label: '停用', value: 'DISABLED' }];
const loading = ref(false);
const saving = ref(false);
const items = ref<OperationItem[]>([]);
const selected = ref<OperationItem>();
const total = ref(0);
const page = ref(1);
const size = ref(20);
const keyword = ref('');
const typeFilter = ref<OperationType>();
const statusFilter = ref<OperationStatus>();
const formVisible = ref(false);
const formData = ref<Record<string, any>>({});
const formTitle = computed(() => formData.value.id ? '调整工序' : '新增工序');

function typeLabel(value: OperationType) { return operationTypes.find((item) => item.value === value)?.label || value; }
async function loadItems(targetPage = page.value) {
  loading.value = true;
  try {
    const result = await getOperationsApi({ page: targetPage, size: size.value, keyword: keyword.value || undefined, operation_type: typeFilter.value, status: statusFilter.value });
    items.value = result.items; total.value = result.total; page.value = result.page;
  } finally { loading.value = false; }
}
async function selectItem(item: OperationItem) { selected.value = await getOperationApi(item.id); }
function openForm(item?: OperationItem) {
  formData.value = item ? { ...item } : { operation_code: '', operation_name: '', operation_short_name: '', operation_type: 'PROCESS', production_enabled: true, quality_enabled: false, trace_enabled: true, sort_no: 0, description: '', remark: '' };
  formVisible.value = true;
}
async function submitForm() {
  if (!formData.value.operation_code?.trim() || !formData.value.operation_name?.trim()) { message.warning('请填写工序编码和名称'); return; }
  saving.value = true;
  try {
    const saved = formData.value.id ? await updateOperationApi(formData.value.id, formData.value) : await createOperationApi(formData.value);
    formVisible.value = false; message.success('工序已保存'); await loadItems(formData.value.id ? page.value : 1); await selectItem(saved);
  } finally { saving.value = false; }
}
async function changeStatus() {
  if (!selected.value) return;
  const status: OperationStatus = selected.value.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  await updateOperationStatusApi(selected.value.id, status); message.success(status === 'ACTIVE' ? '工序已启用' : '工序已停用'); await loadItems(); await selectItem(selected.value);
}
function resetFilters() { keyword.value = ''; typeFilter.value = undefined; statusFilter.value = undefined; void loadItems(1); }
onMounted(loadItems);
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 gap-4">
      <a-card class="min-w-0 flex-1" :body-style="{ padding: '12px' }" title="工序">
        <template #extra><a-button type="primary" @click="openForm()">新增工序</a-button></template>
        <a-space class="mb-3" wrap>
          <a-input-search v-model:value="keyword" allow-clear class="w-52" placeholder="编码或名称" @search="loadItems(1)" />
          <a-select v-model:value="typeFilter" allow-clear class="w-36" :options="operationTypes" placeholder="工序类型" @change="loadItems(1)" />
          <a-select v-model:value="statusFilter" allow-clear class="w-28" :options="statuses" placeholder="状态" @change="loadItems(1)" />
          <a-button @click="resetFilters">重置</a-button>
        </a-space>
        <a-table :columns="[{ title: '编码', dataIndex: 'operation_code' }, { title: '名称', dataIndex: 'operation_name' }, { title: '类型', key: 'type' }, { title: '生产', key: 'production' }, { title: '状态', key: 'status' }]" :data-source="items" :loading="loading" :pagination="false" row-key="id" size="small" @row="(record: OperationItem) => ({ onClick: () => selectItem(record) })">
          <template #bodyCell="{ column, record }">
            <a-button v-if="column.dataIndex === 'operation_code'" type="link" class="h-auto p-0" @click.stop="selectItem(record)">{{ record.operation_code }}</a-button>
            <span v-else-if="column.key === 'type'">{{ typeLabel(record.operation_type) }}</span>
            <a-tag v-else-if="column.key === 'production'" :color="record.production_enabled ? 'green' : 'default'">{{ record.production_enabled ? '启用' : '否' }}</a-tag>
            <a-tag v-else-if="column.key === 'status'" :color="record.status === 'ACTIVE' ? 'green' : 'default'">{{ record.status === 'ACTIVE' ? '启用' : '停用' }}</a-tag>
          </template>
        </a-table>
        <div class="mt-3 text-right"><a-pagination v-model:current="page" v-model:page-size="size" :total="total" show-size-changer @change="loadItems" /></div>
      </a-card>
      <a-card class="w-96 shrink-0" title="工序详情">
        <template #extra><a-space v-if="selected" size="small"><a-button size="small" @click="openForm(selected)">调整</a-button><a-button size="small" :danger="selected.status === 'ACTIVE'" @click="changeStatus">{{ selected.status === 'ACTIVE' ? '停用' : '启用' }}</a-button></a-space></template>
        <a-empty v-if="!selected" description="请选择一条工序" />
        <a-descriptions v-else :column="1" size="small">
          <a-descriptions-item label="名称">{{ selected.operation_name }}（{{ selected.operation_code }}）</a-descriptions-item>
          <a-descriptions-item label="简称">{{ selected.operation_short_name || '-' }}</a-descriptions-item>
          <a-descriptions-item label="类型">{{ typeLabel(selected.operation_type) }}</a-descriptions-item>
          <a-descriptions-item label="生产/质量/追溯">{{ selected.production_enabled ? '生产' : '非生产' }} / {{ selected.quality_enabled ? '质量' : '无质量' }} / {{ selected.trace_enabled ? '追溯' : '不追溯' }}</a-descriptions-item>
          <a-descriptions-item label="说明">{{ selected.description || '-' }}</a-descriptions-item>
          <a-descriptions-item label="备注">{{ selected.remark || '-' }}</a-descriptions-item>
        </a-descriptions>
      </a-card>
    </div>
    <a-modal v-model:open="formVisible" :title="formTitle" :confirm-loading="saving" width="760px" @ok="submitForm">
      <a-form layout="vertical"><a-row :gutter="16">
        <a-col :span="12"><a-form-item label="工序编码" required><a-input v-model:value="formData.operation_code" :disabled="Boolean(formData.id)" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item label="工序名称" required><a-input v-model:value="formData.operation_name" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item label="工序简称"><a-input v-model:value="formData.operation_short_name" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item label="工序类型"><a-select v-model:value="formData.operation_type" :options="operationTypes" /></a-form-item></a-col>
        <a-col :span="8"><a-form-item label="生成生产任务"><a-switch v-model:checked="formData.production_enabled" /></a-form-item></a-col>
        <a-col :span="8"><a-form-item label="质量可用"><a-switch v-model:checked="formData.quality_enabled" /></a-form-item></a-col>
        <a-col :span="8"><a-form-item label="追溯可用"><a-switch v-model:checked="formData.trace_enabled" /></a-form-item></a-col>
        <a-col :span="12"><a-form-item label="排序"><a-input-number v-model:value="formData.sort_no" class="w-full" /></a-form-item></a-col>
      </a-row><a-form-item label="说明"><a-textarea v-model:value="formData.description" :rows="2" /></a-form-item><a-form-item label="备注"><a-textarea v-model:value="formData.remark" :rows="2" /></a-form-item></a-form>
    </a-modal>
  </Page>
</template>
