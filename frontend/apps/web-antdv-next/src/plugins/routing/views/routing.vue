<script lang="ts" setup>
import type { OperationOption, RoutingItem, RoutingStatus, RoutingType, WorkCenterOption } from '../api';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import {
  activateRoutingApi, calculateRoutingTimeApi, copyRoutingApi, createRoutingApi, createRoutingOperationApi,
  deactivateRoutingApi, deleteRoutingOperationApi, getOperationOptionsApi, getProductOptionsApi, getRoutingApi,
  getRoutingsApi, getWorkCenterOptionsApi, reorderRoutingOperationsApi, setDefaultRoutingApi, updateRoutingApi,
  updateRoutingOperationApi, validateRoutingApi,
} from '../api';

const routingTypes: { label: string; value: RoutingType }[] = [
  { label: '标准生产', value: 'STANDARD' }, { label: '返工', value: 'REWORK' }, { label: '试制', value: 'TRIAL' },
];
const statuses: { label: string; value: RoutingStatus }[] = [
  { label: '草稿', value: 'DRAFT' }, { label: '生效', value: 'ACTIVE' }, { label: '停用', value: 'INACTIVE' },
];
const runTimeUnits = [
  { label: '分钟 / 基准数量', value: 'MIN_PER_BASE_QTY' }, { label: '小时 / 基准数量', value: 'HOUR_PER_BASE_QTY' }, { label: '秒 / 基准数量', value: 'SEC_PER_BASE_QTY' },
];
const loading = ref(false); const saving = ref(false); const items = ref<RoutingItem[]>([]); const selected = ref<RoutingItem>();
const page = ref(1); const size = ref(20); const total = ref(0); const keyword = ref(''); const statusFilter = ref<RoutingStatus>(); const typeFilter = ref<RoutingType>();
const products = ref<any[]>([]); const operations = ref<OperationOption[]>([]); const workCenters = ref<WorkCenterOption[]>([]);
const routingFormVisible = ref(false); const operationFormVisible = ref(false); const copyVisible = ref(false); const calculationVisible = ref(false);
const routingForm = ref<Record<string, any>>({}); const operationForm = ref<Record<string, any>>({}); const copyForm = ref<Record<string, any>>({});
const calculationQuantity = ref<number>(0); const calculation = ref<any>();
const isDraft = computed(() => selected.value?.status === 'DRAFT');
const routingFormTitle = computed(() => routingForm.value.id ? '调整工艺路线（仅草稿）' : '新建工艺路线');
function typeLabel(value: RoutingType) { return routingTypes.find((item) => item.value === value)?.label || value; }
function statusColor(status: RoutingStatus) { return status === 'ACTIVE' ? 'green' : status === 'DRAFT' ? 'blue' : 'default'; }

async function loadOptions() {
  const [productOptions, operationOptions, workCenterOptions] = await Promise.all([getProductOptionsApi(), getOperationOptionsApi(), getWorkCenterOptionsApi()]);
  products.value = productOptions; operations.value = operationOptions; workCenters.value = workCenterOptions;
}
async function loadItems(targetPage = page.value) {
  loading.value = true;
  try {
    const result = await getRoutingsApi({ page: targetPage, size: size.value, keyword: keyword.value || undefined, status: statusFilter.value, routing_type: typeFilter.value });
    items.value = result.items; total.value = result.total; page.value = result.page;
  } finally { loading.value = false; }
}
async function selectItem(item: RoutingItem) { selected.value = await getRoutingApi(item.id); }
async function reloadSelected() { if (selected.value) await selectItem(selected.value); await loadItems(); }
function openRoutingForm(item?: RoutingItem) {
  if (item && item.status !== 'DRAFT') { message.warning('生效或停用的路线只读，请复制新版本'); return; }
  routingForm.value = item ? { ...item } : { routing_code: '', routing_name: '', product_material_id: undefined, routing_version: 'V1.0', routing_type: 'STANDARD', base_quantity: 1, effective_from: undefined, effective_to: undefined, description: '', remark: '' };
  routingFormVisible.value = true;
}
async function submitRoutingForm() {
  if (!routingForm.value.routing_code?.trim() || !routingForm.value.routing_name?.trim() || !routingForm.value.product_material_id) { message.warning('请填写路线编码、名称与产品'); return; }
  saving.value = true;
  try {
    const saved = routingForm.value.id ? await updateRoutingApi(routingForm.value.id, routingForm.value) : await createRoutingApi(routingForm.value);
    routingFormVisible.value = false; message.success('工艺路线已保存'); await loadItems(routingForm.value.id ? page.value : 1); await selectItem(saved);
  } finally { saving.value = false; }
}
function openOperationForm(item?: any) {
  if (!selected.value || !isDraft.value) { message.warning('仅草稿路线可以配置工序'); return; }
  operationForm.value = item ? { ...item } : { sequence_no: ((selected.value.operations?.at(-1)?.sequence_no || 0) + 10), operation_id: undefined, work_center_id: undefined, operation_name_override: '', setup_time_min: 0, run_time_value: 0, run_time_unit: 'MIN_PER_BASE_QTY', queue_time_min: 0, move_time_min: 0, standard_yield_rate: 100, reporting_required: true, quality_required: false, trace_required: true, sort_no: 0, remark: '' };
  operationFormVisible.value = true;
}
async function submitOperationForm() {
  if (!selected.value || !operationForm.value.operation_id) { message.warning('请选择工序'); return; }
  saving.value = true;
  try {
    if (operationForm.value.id) await updateRoutingOperationApi(selected.value.id, operationForm.value.id, operationForm.value);
    else await createRoutingOperationApi(selected.value.id, operationForm.value);
    operationFormVisible.value = false; message.success('工序配置已保存'); await reloadSelected();
  } finally { saving.value = false; }
}
async function removeOperation(item: any) { if (!selected.value) return; await deleteRoutingOperationApi(selected.value.id, item.id); message.success('已移除工序'); await reloadSelected(); }
async function moveOperation(item: any, direction: -1 | 1) {
  if (!selected.value?.operations || !isDraft.value) return;
  const list = [...selected.value.operations]; const index = list.findIndex((entry) => entry.id === item.id); const target = index + direction;
  if (target < 0 || target >= list.length) return;
  const current = list[index]; const replacement = list[target];
  if (!current || !replacement) return;
  list[index] = replacement; list[target] = current;
  await reorderRoutingOperationsApi(selected.value.id, list.map((entry, itemIndex) => ({ routing_operation_id: entry.id, sequence_no: (itemIndex + 1) * 10 })));
  await reloadSelected();
}
async function validate() { if (!selected.value) return; const result = await validateRoutingApi(selected.value.id); if (result.valid) message.success('路线校验通过'); else message.error(result.errors.map((item) => item.message).join('；')); }
async function activate() { if (!selected.value) return; await activateRoutingApi(selected.value.id, !selected.value.is_default); message.success('路线已生效'); await reloadSelected(); }
async function deactivate() { if (!selected.value) return; await deactivateRoutingApi(selected.value.id); message.success('路线已停用'); await reloadSelected(); }
async function setDefault() { if (!selected.value) return; await setDefaultRoutingApi(selected.value.id); message.success('已设为默认路线'); await reloadSelected(); }
function openCopy() { if (!selected.value) return; copyForm.value = { new_routing_code: '', new_version: '', new_routing_name: selected.value.routing_name, effective_from: undefined, effective_to: undefined, description: selected.value.description, remark: selected.value.remark }; copyVisible.value = true; }
async function submitCopy() { if (!selected.value || !copyForm.value.new_routing_code?.trim() || !copyForm.value.new_version?.trim()) { message.warning('请填写新路线编码与版本'); return; } saving.value = true; try { const copied = await copyRoutingApi(selected.value.id, copyForm.value); copyVisible.value = false; message.success('新草稿版本已创建'); await loadItems(1); await selectItem(copied); } finally { saving.value = false; } }
async function calculate() { if (!selected.value || !calculationQuantity.value) { message.warning('请输入生产数量'); return; } calculation.value = await calculateRoutingTimeApi(selected.value.id, calculationQuantity.value); calculationVisible.value = true; }
function resetFilters() { keyword.value = ''; statusFilter.value = undefined; typeFilter.value = undefined; void loadItems(1); }
onMounted(async () => { await Promise.all([loadOptions(), loadItems()]); });
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 gap-4">
      <a-card class="w-[34rem] shrink-0" :body-style="{ padding: '12px' }" title="工艺路线版本">
        <template #extra><a-button type="primary" @click="openRoutingForm()">新建路线</a-button></template>
        <a-space class="mb-3" wrap><a-input-search v-model:value="keyword" allow-clear class="w-40" placeholder="编码或名称" @search="loadItems(1)" /><a-select v-model:value="typeFilter" allow-clear class="w-28" :options="routingTypes" placeholder="类型" @change="loadItems(1)" /><a-select v-model:value="statusFilter" allow-clear class="w-24" :options="statuses" placeholder="状态" @change="loadItems(1)" /><a-button @click="resetFilters">重置</a-button></a-space>
        <a-table :columns="[{ title: '编码', dataIndex: 'routing_code' }, { title: '产品 / 版本', key: 'product' }, { title: '状态', key: 'status' }]" :data-source="items" :loading="loading" :pagination="false" row-key="id" size="small" @row="(record: RoutingItem) => ({ onClick: () => selectItem(record) })"><template #bodyCell="{ column, record }"><a-button v-if="column.dataIndex === 'routing_code'" type="link" class="h-auto p-0 text-left" @click.stop="selectItem(record)">{{ record.routing_code }}</a-button><div v-else-if="column.key === 'product'"><div>{{ record.product.name }}</div><div class="text-xs text-muted-foreground">{{ record.routing_version }} · {{ typeLabel(record.routing_type) }}</div></div><a-tag v-else-if="column.key === 'status'" :color="statusColor(record.status)">{{ record.status }}{{ record.is_default ? ' 默认' : '' }}</a-tag></template></a-table>
        <div class="mt-3 text-right"><a-pagination v-model:current="page" v-model:page-size="size" :total="total" size="small" @change="loadItems" /></div>
      </a-card>
      <a-card class="min-w-0 flex-1" :body-style="{ padding: '16px' }" title="路线与工序配置">
        <a-empty v-if="!selected" description="请选择或创建一条工艺路线" />
        <template v-else>
          <div class="mb-4 flex flex-wrap items-start justify-between gap-3"><div><div class="text-lg font-medium">{{ selected.routing_name }}</div><div class="text-muted-foreground">{{ selected.routing_code }} · {{ selected.product.name }} · {{ selected.routing_version }} · 基准数量 {{ selected.base_quantity }} {{ selected.product.unit }}</div><a-tag class="mt-2" :color="statusColor(selected.status)">{{ selected.status }}</a-tag><a-tag v-if="selected.is_default" class="mt-2" color="gold">默认</a-tag></div><a-space wrap><a-button @click="openRoutingForm(selected)">调整</a-button><a-button @click="openCopy">复制新版本</a-button><a-button @click="validate">校验</a-button><a-button v-if="isDraft" type="primary" @click="activate">生效</a-button><a-button v-if="selected.status === 'ACTIVE' && !selected.is_default" @click="setDefault">设为默认</a-button><a-button v-if="selected.status === 'ACTIVE'" danger @click="deactivate">停用</a-button></a-space></div>
          <a-descriptions class="mb-4" :column="3" size="small" bordered><a-descriptions-item label="路线类型">{{ typeLabel(selected.routing_type) }}</a-descriptions-item><a-descriptions-item label="有效期">{{ selected.effective_from || '长期' }} ~ {{ selected.effective_to || '长期' }}</a-descriptions-item><a-descriptions-item label="说明">{{ selected.description || '-' }}</a-descriptions-item></a-descriptions>
          <div class="mb-2 flex items-center justify-between"><span class="font-medium">线性工序（{{ selected.operations?.length || 0 }}）</span><a-space><a-input-number v-model:value="calculationQuantity" :min="0" placeholder="生产数量" /><a-button @click="calculate">测算工时</a-button><a-button v-if="isDraft" type="primary" @click="openOperationForm()">添加工序</a-button></a-space></div>
          <a-table :columns="[{ title: '顺序', dataIndex: 'sequence_no' }, { title: '工序', key: 'operation' }, { title: '工作中心', key: 'workCenter' }, { title: '准备', dataIndex: 'setup_time_min' }, { title: '运行', key: 'run' }, { title: '等待/转运', key: 'waitMove' }, { title: '良率', dataIndex: 'standard_yield_rate' }, { title: '操作', key: 'actions' }]" :data-source="selected.operations || []" :pagination="false" row-key="id" size="small"><template #bodyCell="{ column, record }"><span v-if="column.key === 'operation'">{{ record.operation_display_name }}<small class="ml-1 text-muted-foreground">{{ record.operation.code }}</small></span><span v-else-if="column.key === 'workCenter'">{{ record.work_center?.name || '-' }}</span><span v-else-if="column.key === 'run'">{{ record.run_time_value }} {{ runTimeUnits.find((item) => item.value === record.run_time_unit)?.label }}</span><span v-else-if="column.key === 'waitMove'">{{ record.queue_time_min }} / {{ record.move_time_min }} 分</span><span v-else-if="column.key === 'actions'"><a-space v-if="isDraft" size="small"><a-button type="link" size="small" @click="openOperationForm(record)">编辑</a-button><a-button type="link" size="small" @click="moveOperation(record, -1)">上移</a-button><a-button type="link" size="small" @click="moveOperation(record, 1)">下移</a-button><a-button type="link" danger size="small" @click="removeOperation(record)">移除</a-button></a-space></span></template></a-table>
        </template>
      </a-card>
    </div>

    <a-modal v-model:open="routingFormVisible" :title="routingFormTitle" :confirm-loading="saving" width="800px" @ok="submitRoutingForm"><a-form layout="vertical"><a-row :gutter="16"><a-col :span="12"><a-form-item label="路线编码" required><a-input v-model:value="routingForm.routing_code" :disabled="Boolean(routingForm.id)" /></a-form-item></a-col><a-col :span="12"><a-form-item label="路线名称" required><a-input v-model:value="routingForm.routing_name" /></a-form-item></a-col><a-col :span="12"><a-form-item label="产品" required><a-select v-model:value="routingForm.product_material_id" show-search :options="products.map((item) => ({ label: `${item.name} (${item.code})`, value: item.id }))" /></a-form-item></a-col><a-col :span="12"><a-form-item label="版本" required><a-input v-model:value="routingForm.routing_version" /></a-form-item></a-col><a-col :span="12"><a-form-item label="路线类型"><a-select v-model:value="routingForm.routing_type" :options="routingTypes" /></a-form-item></a-col><a-col :span="12"><a-form-item label="基准数量"><a-input-number v-model:value="routingForm.base_quantity" class="w-full" :min="0.000001" :precision="6" /></a-form-item></a-col><a-col :span="12"><a-form-item label="生效开始"><a-date-picker v-model:value="routingForm.effective_from" class="w-full" show-time value-format="YYYY-MM-DDTHH:mm:ss" /></a-form-item></a-col><a-col :span="12"><a-form-item label="生效结束"><a-date-picker v-model:value="routingForm.effective_to" class="w-full" show-time value-format="YYYY-MM-DDTHH:mm:ss" /></a-form-item></a-col></a-row><a-form-item label="说明"><a-textarea v-model:value="routingForm.description" :rows="2" /></a-form-item><a-form-item label="备注"><a-textarea v-model:value="routingForm.remark" :rows="2" /></a-form-item></a-form></a-modal>
    <a-modal v-model:open="operationFormVisible" title="配置路线工序" :confirm-loading="saving" width="900px" @ok="submitOperationForm"><a-form layout="vertical"><a-row :gutter="16"><a-col :span="8"><a-form-item label="顺序号" required><a-input-number v-model:value="operationForm.sequence_no" class="w-full" :min="1" /></a-form-item></a-col><a-col :span="8"><a-form-item label="工序" required><a-select v-model:value="operationForm.operation_id" show-search :options="operations.map((item) => ({ label: `${item.name} (${item.code})`, value: item.id }))" /></a-form-item></a-col><a-col :span="8"><a-form-item label="工作中心"><a-select v-model:value="operationForm.work_center_id" allow-clear show-search :options="workCenters.map((item) => ({ label: `${item.name} (${item.code})`, value: item.id }))" /></a-form-item></a-col><a-col :span="8"><a-form-item label="显示名称覆盖"><a-input v-model:value="operationForm.operation_name_override" /></a-form-item></a-col><a-col :span="8"><a-form-item label="准备时间（分）"><a-input-number v-model:value="operationForm.setup_time_min" class="w-full" :min="0" :precision="4" /></a-form-item></a-col><a-col :span="8"><a-form-item label="运行时间"><a-input-number v-model:value="operationForm.run_time_value" class="w-full" :min="0" :precision="6" /></a-form-item></a-col><a-col :span="8"><a-form-item label="运行单位"><a-select v-model:value="operationForm.run_time_unit" :options="runTimeUnits" /></a-form-item></a-col><a-col :span="8"><a-form-item label="等待时间（分）"><a-input-number v-model:value="operationForm.queue_time_min" class="w-full" :min="0" :precision="4" /></a-form-item></a-col><a-col :span="8"><a-form-item label="转运时间（分）"><a-input-number v-model:value="operationForm.move_time_min" class="w-full" :min="0" :precision="4" /></a-form-item></a-col><a-col :span="8"><a-form-item label="标准良率（%）"><a-input-number v-model:value="operationForm.standard_yield_rate" class="w-full" :min="0.0001" :max="100" :precision="4" /></a-form-item></a-col><a-col :span="8"><a-form-item label="需要报工"><a-switch v-model:checked="operationForm.reporting_required" /></a-form-item></a-col><a-col :span="8"><a-form-item label="需要质量"><a-switch v-model:checked="operationForm.quality_required" /></a-form-item></a-col><a-col :span="8"><a-form-item label="需要追溯"><a-switch v-model:checked="operationForm.trace_required" /></a-form-item></a-col></a-row><a-form-item label="备注"><a-textarea v-model:value="operationForm.remark" :rows="2" /></a-form-item></a-form></a-modal>
    <a-modal v-model:open="copyVisible" title="复制为新草稿版本" :confirm-loading="saving" @ok="submitCopy"><a-form layout="vertical"><a-form-item label="新路线编码" required><a-input v-model:value="copyForm.new_routing_code" /></a-form-item><a-form-item label="新版本" required><a-input v-model:value="copyForm.new_version" placeholder="V1.1" /></a-form-item><a-form-item label="新路线名称"><a-input v-model:value="copyForm.new_routing_name" /></a-form-item></a-form></a-modal>
    <a-modal v-model:open="calculationVisible" title="标准工时测算" :footer="null" width="760px"><a-alert type="info" :message="`生产 ${calculation?.production_quantity}，总标准时间 ${calculation?.total_time_min} 分钟`" class="mb-3" /><a-table :columns="[{ title: '顺序', dataIndex: 'sequence_no' }, { title: '工序', dataIndex: 'operation_name' }, { title: '准备', dataIndex: 'setup_time_min' }, { title: '运行', dataIndex: 'run_time_min' }, { title: '等待', dataIndex: 'queue_time_min' }, { title: '转运', dataIndex: 'move_time_min' }, { title: '合计（分）', dataIndex: 'total_time_min' }]" :data-source="calculation?.items || []" :pagination="false" row-key="routing_operation_id" size="small" /></a-modal>
  </Page>
</template>
