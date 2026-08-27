<script lang="ts" setup>
import type { MaterialOption } from '../../material/api';
import type { LocationItem, WarehouseItem } from '../../warehouse/api';
import type {
  MaterialIssue,
  MaterialVariance,
  AndonDashboard,
  AndonEvent,
  ProductionDashboard,
  ProductionExecution,
  VersionOption,
  WorkOrder,
} from '../api';

import { computed, onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import { $t } from '#/locales';
import { getMaterialOptionsApi } from '../../material/api';
import { getWarehouseListApi, getWarehouseTreeApi } from '../../warehouse/api';
import {
  completeExecutionApi,
  createAndonEventApi,
  createWorkOrderApi,
  getBomVersionOptionsApi,
  getExecutionsApi,
  getMaterialIssuesApi,
  getMaterialVarianceApi,
  getProductionDashboardApi,
  getAndonDashboardApi,
  getAndonEventsApi,
  assignAndonEventApi,
  startAndonEventApi,
  resolveAndonEventApi,
  escalateAndonEventApi,
  cancelAndonEventApi,
  getRoutingVersionOptionsApi,
  getWorkOrderApi,
  getWorkOrdersApi,
  issueMaterialApi,
  recordConsumptionApi,
  releaseWorkOrderApi,
  reportProductionApi,
  returnMaterialApi,
  startExecutionApi,
  startWorkOrderApi,
} from '../api';

type DialogKind = 'completeExecution' | 'consume' | 'create' | 'issue' | 'report' | 'return';

const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const dialogKind = ref<DialogKind>('create');
const orders = ref<WorkOrder[]>([]);
const selected = ref<WorkOrder>();
const materials = ref<MaterialOption[]>([]);
const warehouses = ref<WarehouseItem[]>([]);
const locations = ref<LocationItem[]>([]);
const issues = ref<MaterialIssue[]>([]);
const executions = ref<ProductionExecution[]>([]);
const bomOptions = ref<VersionOption[]>([]);
const routingOptions = ref<VersionOption[]>([]);
const dashboard = ref<ProductionDashboard>();
const variances = ref<MaterialVariance[]>([]);
const andonDashboard = ref<AndonDashboard>();
const andonEvents = ref<AndonEvent[]>([]);
const selectedAndon = ref<AndonEvent>();
const form = ref<Record<string, any>>({});

const activeExecution = computed(() => executions.value.find((item) => item.status === 'IN_PROGRESS'));
const dialogTitle = computed(() => ({
  completeExecution: '完成工序执行',
  consume: '记录实际耗料',
  create: '新建生产工单',
  issue: '生产领料',
  report: '生产报工入库',
  return: '生产退料',
}[dialogKind.value]));

function flatten(nodes: any[]): LocationItem[] {
  return nodes.flatMap((node) => [
    ...(node.node_type === 'AREA' ? [] : [{
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
    } as LocationItem]),
    ...flatten(node.children ?? []),
  ]);
}

async function loadOptions() {
  [materials.value, warehouses.value] = await Promise.all([
    getMaterialOptionsApi({ producible: true }),
    getWarehouseListApi(),
  ]);
  const trees = await Promise.all(warehouses.value.map((item) => getWarehouseTreeApi(item.id)));
  locations.value = trees.flatMap((tree, index) =>
    flatten(tree.children).map((item) => ({ ...item, warehouse_id: warehouses.value[index]?.id ?? 0 })),
  );
}

async function load() {
  loading.value = true;
  try {
    [orders.value, dashboard.value, andonDashboard.value, andonEvents.value] = await Promise.all([
      getWorkOrdersApi(),
      getProductionDashboardApi(),
      getAndonDashboardApi(),
      getAndonEventsApi(),
    ]);
    if (selected.value) await selectOrder(selected.value);
  } finally {
    loading.value = false;
  }
}

async function runAndonAction(event: AndonEvent, action: 'assign' | 'start' | 'resolve' | 'escalate' | 'cancel') {
  if (action === 'assign') await assignAndonEventApi(event.id, { assignee_id: 1, notes: '现场值班组' });
  if (action === 'start') await startAndonEventApi(event.id);
  if (action === 'resolve') await resolveAndonEventApi(event.id, { root_cause: '现场处理完成', resolution_notes: '恢复生产并验证' });
  if (action === 'escalate') await escalateAndonEventApi(event.id, '现场升级处理');
  if (action === 'cancel') await cancelAndonEventApi(event.id);
  await load();
  selectedAndon.value = andonEvents.value.find((item) => item.id === event.id);
}

async function createQuickAndon(type: AndonEvent['event_type']) {
  await createAndonEventApi({ event_type: type, priority: type === 'STOPPAGE' ? 'HIGH' : 'MEDIUM', title: type === 'STOPPAGE' ? '现场停机异常' : type === 'MATERIAL_SHORTAGE' ? '生产缺料异常' : '生产质量异常', description: '由生产现场 Andon 看板登记' });
  message.success('Andon 异常已登记');
  await load();
}

async function selectOrder(row: WorkOrder) {
  selectedAndon.value = undefined;
  selected.value = await getWorkOrderApi(row.id);
  [issues.value, variances.value, executions.value] = await Promise.all([
    getMaterialIssuesApi(row.id),
    getMaterialVarianceApi(row.id),
    getExecutionsApi(row.id),
  ]);
}

function locationOptions(warehouseId?: number) {
  return locations.value
    .filter((item) => item.warehouse_id === warehouseId && item.storage_enabled)
    .map((item) => ({ label: `${item.location_code} · ${item.location_name}`, value: item.id }));
}

async function productChanged(id: number) {
  [bomOptions.value, routingOptions.value] = await Promise.all([
    getBomVersionOptionsApi(id),
    getRoutingVersionOptionsApi(id),
  ]);
  form.value.bom_id = bomOptions.value[0]?.id;
  form.value.routing_id = routingOptions.value[0]?.id;
}

function open(kind: DialogKind) {
  if (kind !== 'create' && !selected.value) return;
  dialogKind.value = kind;
  if (kind === 'create') form.value = { planned_quantity: 1 };
  if (kind === 'issue') form.value = {
    work_order_id: selected.value?.id,
    requirement_id: selected.value?.requirements[0]?.id,
    quantity: 1,
  };
  if (kind === 'return') {
    const line = issues.value.flatMap((item) => item.lines)
      .find((item) => Number(item.returned_quantity) < Number(item.quantity));
    form.value = {
      work_order_id: selected.value?.id,
      issue_line_id: line?.id,
      quantity: line ? Number(line.quantity) - Number(line.returned_quantity) : 1,
    };
  }
  if (kind === 'report') form.value = {
    work_order_id: selected.value?.id,
    good_quantity: 1,
    scrap_quantity: 0,
    lot_no: '',
  };
  if (kind === 'consume') form.value = {
    requirement_id: selected.value?.requirements[0]?.id,
    issue_line_id: issues.value.flatMap((item) => item.lines)[0]?.id,
    quantity: 1,
  };
  if (kind === 'completeExecution') form.value = { good_quantity: 1, scrap_quantity: 0 };
  dialogVisible.value = true;
}

async function submit() {
  saving.value = true;
  try {
    if (dialogKind.value === 'create') {
      selected.value = await createWorkOrderApi(form.value);
      message.success($t('production.created'));
    } else if (dialogKind.value === 'issue') {
      const { work_order_id, requirement_id, ...line } = form.value;
      await issueMaterialApi({ work_order_id, lines: [{ requirement_id, ...line }] });
      message.success($t('production.issuedMessage'));
    } else if (dialogKind.value === 'return') {
      const { work_order_id, issue_line_id, quantity } = form.value;
      await returnMaterialApi({ work_order_id, lines: [{ issue_line_id, quantity }] });
      message.success($t('production.returnedMessage'));
    } else if (dialogKind.value === 'consume' && activeExecution.value) {
      await recordConsumptionApi(activeExecution.value.id, form.value);
      message.success('实际耗料已记录');
    } else if (dialogKind.value === 'completeExecution' && activeExecution.value) {
      await completeExecutionApi(activeExecution.value.id, form.value);
      message.success('工序执行已完成');
    } else {
      await reportProductionApi({ ...form.value, lot_no: form.value.lot_no || undefined });
      message.success($t('production.reported'));
    }
    dialogVisible.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}

async function transition(action: 'release' | 'start') {
  if (!selected.value) return;
  selected.value = action === 'release'
    ? await releaseWorkOrderApi(selected.value.id)
    : await startWorkOrderApi(selected.value.id);
  message.success($t(action === 'release' ? 'production.released' : 'production.started'));
  await load();
}

async function startOperationExecution(operationId: number) {
  if (!selected.value) return;
  await startExecutionApi(selected.value.id, operationId);
  message.success('工序执行已开始');
  await load();
}

onMounted(async () => {
  await loadOptions();
  await load();
});
</script>

<template>
  <Page :title="$t('production.menu')">
  <div v-if="dashboard" class="mb-4 grid grid-cols-4 gap-3">
      <a-card size="small" title="工单总数">{{ dashboard.total_orders }}</a-card>
      <a-card size="small" title="生产中">{{ dashboard.in_progress_orders }}</a-card>
      <a-card size="small" title="已完成">{{ dashboard.completed_orders }}</a-card>
      <a-card size="small" title="完工率">{{ Number(dashboard.completion_rate).toFixed(2) }}%</a-card>
  </div>
  <div v-if="andonDashboard" class="mb-4 grid grid-cols-4 gap-3">
    <a-card size="small" title="Andon 活动数">{{ andonDashboard.active_count }}</a-card>
    <a-card size="small" title="Andon 超期数">{{ andonDashboard.overdue_count }}</a-card>
    <a-card size="small" title="停机异常">{{ andonDashboard.type_counts.STOPPAGE || 0 }}</a-card>
    <a-card size="small" title="平均恢复时长">{{ andonDashboard.average_resolve_hours }} 小时</a-card>
  </div>
    <div class="flex h-full min-h-0 gap-4">
      <a-card class="min-w-0 flex-1" :bordered="false">
        <div class="mb-3 flex gap-2">
          <a-button type="primary" @click="open('create')">{{ $t('production.create') }}</a-button>
          <a-button danger @click="createQuickAndon('STOPPAGE')">登记停机</a-button>
          <a-button @click="createQuickAndon('MATERIAL_SHORTAGE')">登记缺料</a-button>
          <a-button @click="createQuickAndon('QUALITY')">登记质量异常</a-button>
          <a-button @click="load">{{ $t('production.refresh') }}</a-button>
        </div>
        <a-table
          :loading="loading"
          :data-source="orders"
          row-key="id"
          :pagination="{ pageSize: 20 }"
          @row="(row: WorkOrder) => ({ onClick: () => selectOrder(row) })"
        >
          <a-table-column :title="$t('production.orderNo')" data-index="work_order_no" />
          <a-table-column :title="$t('production.product')" data-index="product_name_snapshot" />
          <a-table-column :title="$t('production.planned')" data-index="planned_quantity" />
          <a-table-column :title="$t('production.completed')" data-index="completed_quantity" />
          <a-table-column :title="$t('production.status')" data-index="status" />
        </a-table>
        <a-divider>Andon 现场异常</a-divider>
        <a-table :loading="loading" :data-source="andonEvents" row-key="id" size="small" :pagination="{ pageSize: 8 }" @row="(row: AndonEvent) => ({ onClick: () => selectedAndon = row })">
          <a-table-column title="事件号" data-index="event_no" /><a-table-column title="类型" data-index="event_type" /><a-table-column title="优先级" data-index="priority" /><a-table-column title="状态" data-index="status" /><a-table-column title="SLA 截止" data-index="sla_due_at" />
        </a-table>
      </a-card>

      <a-card class="w-[620px] shrink-0" :bordered="false" :title="selected?.work_order_no ?? $t('production.workOrders')">
        <template v-if="selectedAndon">
          <a-descriptions :column="1" size="small">
            <a-descriptions-item label="Andon 事件号">{{ selectedAndon.event_no }}</a-descriptions-item>
            <a-descriptions-item label="异常">{{ selectedAndon.title }}：{{ selectedAndon.description }}</a-descriptions-item>
            <a-descriptions-item label="状态"><a-tag>{{ selectedAndon.status }}</a-tag></a-descriptions-item>
            <a-descriptions-item label="SLA 截止">{{ selectedAndon.sla_due_at }}</a-descriptions-item>
            <a-descriptions-item label="责任人">{{ selectedAndon.assignee_id || '未派工' }}</a-descriptions-item>
          </a-descriptions>
          <div class="my-3 flex flex-wrap gap-2">
            <a-button v-if="selectedAndon.status === 'OPEN'" @click="runAndonAction(selectedAndon, 'assign')">派工</a-button>
            <a-button v-if="['OPEN', 'ACKNOWLEDGED', 'BLOCKED'].includes(selectedAndon.status)" @click="runAndonAction(selectedAndon, 'start')">开始处理</a-button>
            <a-button v-if="selectedAndon.status !== 'RESOLVED' && selectedAndon.status !== 'CANCELLED'" @click="runAndonAction(selectedAndon, 'escalate')">升级</a-button>
            <a-button v-if="selectedAndon.status !== 'RESOLVED' && selectedAndon.status !== 'CANCELLED'" type="primary" @click="runAndonAction(selectedAndon, 'resolve')">恢复关闭</a-button>
            <a-button v-if="selectedAndon.status !== 'RESOLVED' && selectedAndon.status !== 'CANCELLED'" danger @click="runAndonAction(selectedAndon, 'cancel')">取消</a-button>
          </div>
        </template>
        <a-empty v-else-if="!selected" />
        <template v-else>
          <a-descriptions :column="1" size="small">
            <a-descriptions-item :label="$t('production.product')">{{ selected.product_code_snapshot }} · {{ selected.product_name_snapshot }}</a-descriptions-item>
            <a-descriptions-item :label="$t('production.bom')">{{ selected.bom_code_snapshot }} / {{ selected.bom_version_snapshot }}</a-descriptions-item>
            <a-descriptions-item :label="$t('production.routing')">{{ selected.routing_code_snapshot }} / {{ selected.routing_version_snapshot }}</a-descriptions-item>
            <a-descriptions-item :label="$t('production.status')"><a-tag>{{ selected.status }}</a-tag></a-descriptions-item>
          </a-descriptions>
          <div class="my-3 flex flex-wrap gap-2">
            <a-button v-if="selected.status === 'DRAFT'" type="primary" @click="transition('release')">{{ $t('production.release') }}</a-button>
            <a-button v-if="selected.status === 'RELEASED'" type="primary" @click="transition('start')">{{ $t('production.start') }}</a-button>
            <a-button v-if="['RELEASED', 'IN_PROGRESS'].includes(selected.status)" @click="open('issue')">{{ $t('production.issue') }}</a-button>
            <a-button v-if="['RELEASED', 'IN_PROGRESS'].includes(selected.status)" @click="open('return')">{{ $t('production.return') }}</a-button>
            <a-button v-if="selected.status === 'IN_PROGRESS'" @click="open('report')">{{ $t('production.report') }}</a-button>
            <a-button v-if="activeExecution" @click="open('consume')">记录耗料</a-button>
            <a-button v-if="activeExecution" type="primary" @click="open('completeExecution')">完成工序</a-button>
          </div>
          <a-tabs>
            <a-tab-pane key="requirements" :tab="$t('production.requirements')">
              <a-table :data-source="selected.requirements" row-key="id" size="small" :pagination="false">
                <a-table-column :title="$t('production.material')" data-index="material_name_snapshot" />
                <a-table-column :title="$t('production.required')" data-index="required_quantity" />
                <a-table-column :title="$t('production.issued')" data-index="issued_quantity" />
                <a-table-column :title="$t('production.returned')" data-index="returned_quantity" />
              </a-table>
            </a-tab-pane>
            <a-tab-pane key="operations" :tab="$t('production.operations')">
              <a-timeline>
                <a-timeline-item v-for="operation in selected.operations" :key="operation.id">
                  <span>{{ operation.sequence_no }} · {{ operation.operation_code_snapshot }} · {{ operation.operation_name_snapshot }} ({{ operation.status }})</span>
                  <a-button
                    v-if="!activeExecution && ['PENDING', 'IN_PROGRESS'].includes(operation.status) && selected.status === 'IN_PROGRESS'"
                    class="ml-2"
                    size="small"
                    type="link"
                    @click="startOperationExecution(operation.id)"
                  >开始执行</a-button>
                </a-timeline-item>
              </a-timeline>
            </a-tab-pane>
            <a-tab-pane key="executions" tab="工序执行记录">
              <a-table :data-source="executions" row-key="id" size="small" :pagination="false">
                <a-table-column title="执行单号" data-index="execution_no" />
                <a-table-column title="状态" data-index="status" />
                <a-table-column title="合格数" data-index="good_quantity" />
                <a-table-column title="报废数" data-index="scrap_quantity" />
              </a-table>
            </a-tab-pane>
            <a-tab-pane key="variance" tab="物料差异">
              <a-table :data-source="variances" row-key="requirement_id" size="small" :pagination="false">
                <a-table-column title="物料" data-index="material_name" />
                <a-table-column title="标准" data-index="required_quantity" />
                <a-table-column title="实际" data-index="actual_quantity" />
                <a-table-column title="差异" data-index="variance_quantity" />
              </a-table>
            </a-tab-pane>
          </a-tabs>
        </template>
      </a-card>
    </div>

    <a-modal v-model:open="dialogVisible" :title="dialogTitle" :confirm-loading="saving" width="650px" @ok="submit">
      <a-form layout="vertical" :model="form">
        <template v-if="dialogKind === 'create'">
          <a-form-item :label="$t('production.product')" required><a-select v-model:value="form.product_material_id" show-search :options="materials.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" @change="productChanged" /></a-form-item>
          <a-form-item :label="$t('production.bom')" required><a-select v-model:value="form.bom_id" :options="bomOptions.map((item) => ({ label: `${item.bom_code} / ${item.bom_version}`, value: item.id }))" /></a-form-item>
          <a-form-item :label="$t('production.routing')" required><a-select v-model:value="form.routing_id" :options="routingOptions.map((item) => ({ label: `${item.code ?? item.name} / ${item.routing_version ?? ''}`, value: item.id }))" /></a-form-item>
          <a-form-item :label="$t('production.planned')" required><a-input-number v-model:value="form.planned_quantity" class="w-full" :min="0.000001" /></a-form-item>
        </template>
        <template v-else-if="dialogKind === 'issue'">
          <a-form-item :label="$t('production.material')" required><a-select v-model:value="form.requirement_id" :options="selected?.requirements.map((item) => ({ label: `${item.material_code_snapshot} · ${item.material_name_snapshot}`, value: item.id }))" /></a-form-item>
          <a-form-item :label="$t('production.warehouse')" required><a-select v-model:value="form.warehouse_id" :options="warehouses.map((item) => ({ label: `${item.warehouse_code} · ${item.warehouse_name}`, value: item.id }))" @change="form.location_id = undefined" /></a-form-item>
          <a-form-item :label="$t('production.location')" required><a-select v-model:value="form.location_id" :options="locationOptions(form.warehouse_id)" /></a-form-item>
          <a-form-item :label="$t('production.lot')"><a-input-number v-model:value="form.lot_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item :label="$t('production.quantity')"><a-input-number v-model:value="form.quantity" class="w-full" :min="0.000001" /></a-form-item>
        </template>
        <template v-else-if="dialogKind === 'return'">
          <a-form-item :label="$t('production.issueLine')"><a-select v-model:value="form.issue_line_id" :options="issues.flatMap((item) => item.lines).map((item) => ({ label: `#${item.id} · ${item.quantity - item.returned_quantity}`, value: item.id }))" /></a-form-item>
          <a-form-item :label="$t('production.quantity')"><a-input-number v-model:value="form.quantity" class="w-full" :min="0.000001" /></a-form-item>
        </template>
        <template v-else-if="dialogKind === 'consume'">
          <a-form-item label="工单物料" required><a-select v-model:value="form.requirement_id" :options="selected?.requirements.map((item) => ({ label: `${item.material_code_snapshot} · ${item.material_name_snapshot}`, value: item.id }))" /></a-form-item>
          <a-form-item label="领料明细"><a-select v-model:value="form.issue_line_id" allow-clear :options="issues.flatMap((issue) => issue.lines).map((item) => ({ label: `#${item.id} · 可用 ${item.quantity - item.returned_quantity}`, value: item.id }))" /></a-form-item>
          <a-form-item label="实际耗用量" required><a-input-number v-model:value="form.quantity" class="w-full" :min="0.000001" /></a-form-item>
        </template>
        <template v-else-if="dialogKind === 'completeExecution'">
          <a-form-item label="工序合格数" required><a-input-number v-model:value="form.good_quantity" class="w-full" :min="0" /></a-form-item>
          <a-form-item label="工序报废数"><a-input-number v-model:value="form.scrap_quantity" class="w-full" :min="0" /></a-form-item>
        </template>
        <template v-else>
          <a-form-item :label="$t('production.quantity')"><a-input-number v-model:value="form.good_quantity" class="w-full" :min="0.000001" /></a-form-item>
          <a-form-item :label="$t('production.scrap')"><a-input-number v-model:value="form.scrap_quantity" class="w-full" :min="0" /></a-form-item>
          <a-form-item :label="$t('production.warehouse')"><a-select v-model:value="form.warehouse_id" :options="warehouses.map((item) => ({ label: `${item.warehouse_code} · ${item.warehouse_name}`, value: item.id }))" @change="form.location_id = undefined" /></a-form-item>
          <a-form-item :label="$t('production.location')"><a-select v-model:value="form.location_id" :options="locationOptions(form.warehouse_id)" /></a-form-item>
          <a-form-item :label="$t('production.lot')"><a-input v-model:value="form.lot_no" /></a-form-item>
        </template>
      </a-form>
    </a-modal>
  </Page>
</template>
