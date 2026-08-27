<script lang="ts" setup>
import type { MaterialOption } from '../../material/api';
import type { SupplierOption } from '../../purchasing/api';
import type { SalesOrder } from '../../sales/api';
import type { MpsPlan, MrpRun, PlannedOrder } from '../api';

import { computed, onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import { getMaterialOptionsApi } from '../../material/api';
import { getPurchasingSupplierOptionsApi } from '../../purchasing/api';
import { getSalesOrdersApi } from '../../sales/api';
import {
  addMpsDemandApi,
  confirmMpsPlanApi,
  createMpsPlanApi,
  deleteMpsDemandApi,
  firmPlannedOrderApi,
  getMpsPlanApi,
  getMpsPlansApi,
  getMrpRunApi,
  getMrpRunsApi,
  importSalesOrdersApi,
  releasePlannedOrderApi,
  recalculateOpenOrderPromisesApi,
  runMrpApi,
} from '../api';

type DialogKind = 'createPlan' | 'demand' | 'importSales' | 'release' | 'runMrp';

const activeTab = ref('mps');
const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const dialogKind = ref<DialogKind>('createPlan');
const plans = ref<MpsPlan[]>([]);
const selectedPlan = ref<MpsPlan>();
const runs = ref<MrpRun[]>([]);
const selectedRun = ref<MrpRun>();
const selectedPlannedOrder = ref<PlannedOrder>();
const materials = ref<MaterialOption[]>([]);
const suppliers = ref<SupplierOption[]>([]);
const salesOrders = ref<SalesOrder[]>([]);
const form = ref<Record<string, any>>({});

const dialogTitle = computed(() => ({
  createPlan: '新建主生产计划',
  demand: '新增独立需求',
  importSales: '导入销售订单需求',
  release: '下达计划订单',
  runMrp: '运行物料需求计划',
}[dialogKind.value]));

const demandTotal = computed(() =>
  (selectedPlan.value?.demands ?? []).reduce((sum, item) => sum + Number(item.quantity), 0),
);
const netRequirementTotal = computed(() =>
  (selectedRun.value?.requirements ?? []).reduce(
    (sum, item) => sum + Number(item.net_requirement),
    0,
  ),
);
const uncoveredTotal = computed(() =>
  (selectedRun.value?.requirements ?? []).reduce(
    (sum, item) => sum + Number(item.uncovered_quantity),
    0,
  ),
);

function formatDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function dateAfter(days: number) {
  const value = new Date();
  value.setDate(value.getDate() + days);
  return formatDate(value);
}

function number(value?: number) {
  return Number(value ?? 0).toLocaleString('zh-CN', { maximumFractionDigits: 6 });
}

function planStatusColor(status: string) {
  return status === 'CONFIRMED' ? 'green' : status === 'CLOSED' ? 'default' : 'blue';
}

function runStatusColor(status: string) {
  return status === 'COMPLETED' ? 'green' : status === 'FAILED' ? 'red' : 'processing';
}

function orderStatusColor(status: string) {
  return ({ FIRM: 'orange', PLANNED: 'blue', RELEASED: 'green' } as Record<string, string>)[status]
    ?? 'default';
}

async function loadOptions() {
  const [materialOptions, supplierOptions, confirmed, partial] = await Promise.all([
    getMaterialOptionsApi(),
    getPurchasingSupplierOptionsApi(),
    getSalesOrdersApi({ status: 'CONFIRMED' }),
    getSalesOrdersApi({ status: 'PARTIALLY_SHIPPED' }),
  ]);
  materials.value = materialOptions;
  suppliers.value = supplierOptions;
  salesOrders.value = [...confirmed, ...partial];
}

async function loadPlans() {
  plans.value = await getMpsPlansApi();
  if (selectedPlan.value) {
    const current = plans.value.find((item) => item.id === selectedPlan.value?.id);
    selectedPlan.value = current ? await getMpsPlanApi(current.id) : undefined;
  } else if (plans.value[0]) {
    await selectPlan(plans.value[0]);
  }
}

async function loadRuns() {
  runs.value = await getMrpRunsApi();
  if (selectedRun.value) {
    const current = runs.value.find((item) => item.id === selectedRun.value?.id);
    selectedRun.value = current ? await getMrpRunApi(current.id) : undefined;
  } else if (runs.value[0]) {
    await selectRun(runs.value[0]);
  }
}

async function load() {
  loading.value = true;
  try {
    await Promise.all([loadPlans(), loadRuns()]);
  } finally {
    loading.value = false;
  }
}

async function selectPlan(plan: MpsPlan) {
  selectedPlan.value = await getMpsPlanApi(plan.id);
}

async function selectRun(run: MrpRun) {
  selectedRun.value = await getMrpRunApi(run.id);
}

function open(kind: DialogKind, plannedOrder?: PlannedOrder) {
  dialogKind.value = kind;
  selectedPlannedOrder.value = plannedOrder;
  if (kind === 'createPlan') {
    form.value = {
      plan_name: '',
      plan_no: '',
      horizon_start: formatDate(new Date()),
      horizon_end: dateAfter(30),
      remark: '',
    };
  } else if (kind === 'demand') {
    form.value = {
      material_id: materials.value[0]?.id,
      demand_date: selectedPlan.value?.horizon_start ?? formatDate(new Date()),
      demand_type: 'MANUAL',
      quantity: 1,
      remark: '',
    };
  } else if (kind === 'importSales') {
    form.value = {
      sales_order_ids: [],
      demand_date: selectedPlan.value?.horizon_start ?? formatDate(new Date()),
    };
  } else if (kind === 'runMrp') {
    form.value = {
      mps_plan_id: selectedPlan.value?.id,
      include_inventory: true,
      include_open_purchase: true,
      include_open_production: true,
      default_purchase_lead_days: 7,
      default_production_lead_days: 1,
      max_level: 20,
    };
  } else {
    form.value = {
      supplier_id: plannedOrder?.order_type === 'PURCHASE' ? suppliers.value[0]?.id : undefined,
      currency: 'CNY',
      remark: '',
    };
  }
  dialogVisible.value = true;
}

async function submit() {
  saving.value = true;
  try {
    if (dialogKind.value === 'createPlan') {
      if (!form.value.plan_name || !form.value.horizon_start || !form.value.horizon_end) {
        message.warning('请填写计划名称和计划期间');
        return;
      }
      const data = { ...form.value, plan_no: form.value.plan_no || undefined };
      selectedPlan.value = await createMpsPlanApi(data);
      message.success('主生产计划已创建');
    } else if (dialogKind.value === 'demand') {
      if (!selectedPlan.value || !form.value.material_id || !form.value.demand_date) return;
      await addMpsDemandApi(selectedPlan.value.id, form.value);
      message.success('需求已加入计划');
    } else if (dialogKind.value === 'importSales') {
      if (!selectedPlan.value || !form.value.sales_order_ids?.length) {
        message.warning('请选择至少一张销售订单');
        return;
      }
      const imported = await importSalesOrdersApi(selectedPlan.value.id, form.value);
      message.success(`已导入 ${imported.length} 条销售需求`);
    } else if (dialogKind.value === 'runMrp') {
      const result = await runMrpApi(form.value);
      selectedRun.value = result;
      activeTab.value = 'mrp';
      if (result.status === 'FAILED') message.error(result.error_message || 'MRP 运算失败');
      else message.success(`MRP 完成，生成 ${result.planned_order_count} 张计划订单`);
    } else if (selectedPlannedOrder.value) {
      if (selectedPlannedOrder.value.order_type === 'PURCHASE' && !form.value.supplier_id) {
        message.warning('计划采购订单下达时必须选择供应商');
        return;
      }
      await releasePlannedOrderApi(selectedPlannedOrder.value.id, form.value);
      message.success('计划订单已转换为正式业务单据草稿');
    }
    dialogVisible.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}

async function confirmPlan() {
  if (!selectedPlan.value) return;
  selectedPlan.value = await confirmMpsPlanApi(selectedPlan.value.id);
  message.success('MPS 已确认并冻结需求');
  await loadPlans();
}

async function deleteDemand(id: number) {
  if (!selectedPlan.value) return;
  await deleteMpsDemandApi(selectedPlan.value.id, id);
  message.success('需求已删除');
  await loadPlans();
}

async function firmOrder(plannedOrder: PlannedOrder) {
  await firmPlannedOrderApi(plannedOrder.id);
  message.success('计划订单已固定');
  if (selectedRun.value) selectedRun.value = await getMrpRunApi(selectedRun.value.id);
}

async function recalculatePromises() {
  const result = await recalculateOpenOrderPromisesApi();
  message.success(`已重算 ${result.assessed_order_count} 张订单、${result.assessed_line_count} 行承诺`);
  await loadRuns();
}

onMounted(async () => {
  await Promise.all([loadOptions(), load()]);
});
</script>

<template>
  <Page title="主生产计划 / 物料需求计划" auto-content-height>
    <a-tabs v-model:active-key="activeTab" class="h-full">
      <a-tab-pane key="mps" tab="MPS 主生产计划">
        <div class="flex min-h-[680px] gap-3">
          <a-card class="min-w-0 flex-1" :body-style="{ padding: '12px' }">
            <template #title>计划版本</template>
            <template #extra>
              <a-space>
                <a-button @click="load">刷新</a-button>
                <a-button type="primary" @click="open('createPlan')">新建 MPS</a-button>
              </a-space>
            </template>
            <a-table
              :data-source="plans"
              :loading="loading"
              :pagination="{ pageSize: 20 }"
              row-key="id"
              size="small"
              @row="(record: MpsPlan) => ({ onClick: () => selectPlan(record) })"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <a-tag :color="planStatusColor(record.status)">{{ record.status }}</a-tag>
                </template>
              </template>
              <a-table-column title="计划编号" data-index="plan_no" />
              <a-table-column title="计划名称" data-index="plan_name" />
              <a-table-column title="开始" data-index="horizon_start" width="110" />
              <a-table-column title="结束" data-index="horizon_end" width="110" />
              <a-table-column title="状态" data-index="status" key="status" width="100" />
            </a-table>
          </a-card>

          <a-card class="w-[760px] shrink-0" :body-style="{ padding: '12px' }">
            <template #title>{{ selectedPlan?.plan_name ?? '计划详情' }}</template>
            <template #extra>
              <a-space v-if="selectedPlan">
                <a-button
                  v-if="selectedPlan.status === 'DRAFT'"
                  @click="open('demand')"
                >新增需求</a-button>
                <a-button
                  v-if="selectedPlan.status === 'DRAFT'"
                  @click="open('importSales')"
                >导入销售订单</a-button>
                <a-button
                  v-if="selectedPlan.status === 'DRAFT'"
                  type="primary"
                  @click="confirmPlan"
                >确认 MPS</a-button>
                <a-button
                  v-if="selectedPlan.status === 'CONFIRMED'"
                  type="primary"
                  @click="open('runMrp')"
                >运行 MRP</a-button>
              </a-space>
            </template>
            <a-empty v-if="!selectedPlan" description="请选择一个计划" />
            <template v-else>
              <a-row :gutter="12" class="mb-3">
                <a-col :span="8"><a-statistic title="需求行" :value="selectedPlan.demands.length" /></a-col>
                <a-col :span="8"><a-statistic title="需求总量" :value="demandTotal" /></a-col>
                <a-col :span="8"><a-statistic title="计划期间天数" :value="`${selectedPlan.horizon_start} 至 ${selectedPlan.horizon_end}`" /></a-col>
              </a-row>
              <a-alert
                v-if="selectedPlan.status === 'CONFIRMED'"
                class="mb-3"
                message="计划已确认，需求已冻结；如需调整请新建计划版本。"
                type="success"
                show-icon
              />
              <a-table
                :data-source="selectedPlan.demands"
                :pagination="false"
                row-key="id"
                size="small"
                :scroll="{ y: 480 }"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'quantity'">
                    {{ number(record.quantity) }} {{ record.unit_code_snapshot }}
                  </template>
                  <template v-else-if="column.key === 'action'">
                    <a-popconfirm title="确认删除该需求？" @confirm="deleteDemand(record.id)">
                      <a-button type="link" danger size="small">删除</a-button>
                    </a-popconfirm>
                  </template>
                </template>
                <a-table-column title="#" data-index="line_no" width="54" />
                <a-table-column title="物料编码" data-index="material_code_snapshot" width="130" />
                <a-table-column title="物料名称" data-index="material_name_snapshot" />
                <a-table-column title="来源" data-index="demand_type" width="110" />
                <a-table-column title="来源单号" data-index="source_no" width="145" />
                <a-table-column title="需求日期" data-index="demand_date" width="110" />
                <a-table-column title="数量" key="quantity" width="100" />
                <a-table-column v-if="selectedPlan.status === 'DRAFT'" title="操作" key="action" width="70" />
              </a-table>
            </template>
          </a-card>
        </div>
      </a-tab-pane>

      <a-tab-pane key="mrp" tab="MRP 运算结果">
        <div class="flex min-h-[680px] gap-3">
          <a-card class="w-[390px] shrink-0" :body-style="{ padding: '12px' }">
            <template #title>运算历史</template>
            <template #extra><a-button @click="loadRuns">刷新</a-button></template>
            <a-table
              :data-source="runs"
              :loading="loading"
              :pagination="{ pageSize: 20 }"
              row-key="id"
              size="small"
              @row="(record: MrpRun) => ({ onClick: () => selectRun(record) })"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <a-tag :color="runStatusColor(record.status)">{{ record.status }}</a-tag>
                </template>
              </template>
              <a-table-column title="运行编号" data-index="run_no" />
              <a-table-column title="需求" data-index="requirement_count" width="62" />
              <a-table-column title="订单" data-index="planned_order_count" width="62" />
              <a-table-column title="状态" data-index="status" key="status" width="92" />
            </a-table>
          </a-card>

          <a-card class="min-w-0 flex-1" :body-style="{ padding: '12px' }">
            <template #title>{{ selectedRun?.run_no ?? '运算详情' }}</template>
            <template #extra>
              <a-button type="primary" ghost @click="recalculatePromises">重新计算 ATP/CTP</a-button>
            </template>
            <a-empty v-if="!selectedRun" description="请选择一次 MRP 运算" />
            <template v-else>
              <a-alert
                v-if="selectedRun.status === 'FAILED'"
                class="mb-3"
                :message="selectedRun.error_message || 'MRP 运算失败'"
                type="error"
                show-icon
              />
              <a-row :gutter="12" class="mb-3">
                <a-col :span="6"><a-statistic title="需求明细" :value="selectedRun.requirement_count" /></a-col>
                <a-col :span="6"><a-statistic title="计划订单" :value="selectedRun.planned_order_count" /></a-col>
                <a-col :span="6"><a-statistic title="净需求合计" :value="netRequirementTotal" /></a-col>
                <a-col :span="6"><a-statistic title="未覆盖缺口" :value="uncoveredTotal" :value-style="uncoveredTotal > 0 ? { color: '#cf1322' } : {}" /></a-col>
              </a-row>
              <a-row :gutter="12" class="mb-3">
                <a-col :span="6"><a-statistic title="最近重算行数" :value="selectedRun.promise_assessment_count" /></a-col>
                <a-col :span="6"><a-statistic title="最近重算时间" :value="selectedRun.promise_refresh_at || '-'" /></a-col>
              </a-row>
              <a-alert
                v-if="selectedRun.promise_refresh_at"
                class="mb-3"
                :message="`最近 ATP/CTP 重算：${selectedRun.promise_refresh_at}`"
                type="info"
                show-icon
              />
              <a-tabs>
                <a-tab-pane key="requirements" tab="净需求展开">
                  <a-table
                    :data-source="selectedRun.requirements"
                    :pagination="{ pageSize: 20 }"
                    row-key="id"
                    size="small"
                    :scroll="{ x: 1500 }"
                  >
                    <template #bodyCell="{ column, record }">
                      <template v-if="column.key === 'gross_requirement'">{{ number(record.gross_requirement) }}</template>
                      <template v-else-if="column.key === 'on_hand_allocated'">{{ number(record.on_hand_allocated) }}</template>
                      <template v-else-if="column.key === 'purchase_supply_allocated'">{{ number(record.purchase_supply_allocated) }}</template>
                      <template v-else-if="column.key === 'production_supply_allocated'">{{ number(record.production_supply_allocated) }}</template>
                      <template v-else-if="column.key === 'net_requirement'">{{ number(record.net_requirement) }}</template>
                      <template v-else-if="column.key === 'planned_order_quantity'">{{ number(record.planned_order_quantity) }}</template>
                      <template v-else-if="column.key === 'uncovered_quantity'">
                        <span :class="Number(record.uncovered_quantity) > 0 ? 'text-red-500' : ''">{{ number(record.uncovered_quantity) }}</span>
                      </template>
                    </template>
                    <a-table-column title="层级" data-index="level_no" width="70" fixed="left" />
                    <a-table-column title="物料编码" data-index="material_code_snapshot" width="130" fixed="left" />
                    <a-table-column title="物料名称" data-index="material_name_snapshot" width="170" />
                    <a-table-column title="需求日期" data-index="requirement_date" width="110" />
                    <a-table-column title="毛需求" key="gross_requirement" width="105" />
                    <a-table-column title="库存抵扣" key="on_hand_allocated" width="105" />
                    <a-table-column title="采购在途" key="purchase_supply_allocated" width="105" />
                    <a-table-column title="生产在制" key="production_supply_allocated" width="105" />
                    <a-table-column title="净需求" key="net_requirement" width="105" />
                    <a-table-column title="计划量" key="planned_order_quantity" width="105" />
                    <a-table-column title="未覆盖" key="uncovered_quantity" width="105" />
                    <a-table-column title="来源路径" data-index="source_path" width="320" />
                  </a-table>
                </a-tab-pane>
                <a-tab-pane key="orders" tab="计划订单">
                  <a-table
                    :data-source="selectedRun.planned_orders"
                    :pagination="{ pageSize: 20 }"
                    row-key="id"
                    size="small"
                    :scroll="{ x: 1300 }"
                  >
                    <template #bodyCell="{ column, record }">
                      <template v-if="column.key === 'order_type'">
                        <a-tag :color="record.order_type === 'PRODUCTION' ? 'purple' : 'cyan'">{{ record.order_type }}</a-tag>
                      </template>
                      <template v-else-if="column.key === 'quantity'">{{ number(record.quantity) }} {{ record.unit_code_snapshot }}</template>
                      <template v-else-if="column.key === 'status'">
                        <a-tag :color="orderStatusColor(record.status)">{{ record.status }}</a-tag>
                      </template>
                      <template v-else-if="column.key === 'action'">
                        <a-space>
                          <a-button v-if="record.status === 'PLANNED'" type="link" size="small" @click="firmOrder(record)">固定</a-button>
                          <a-button v-if="record.status === 'PLANNED' || record.status === 'FIRM'" type="link" size="small" @click="open('release', record)">下达</a-button>
                        </a-space>
                      </template>
                    </template>
                    <a-table-column title="计划订单号" data-index="planned_order_no" width="180" fixed="left" />
                    <a-table-column title="类型" data-index="order_type" key="order_type" width="95" />
                    <a-table-column title="物料编码" data-index="material_code_snapshot" width="130" />
                    <a-table-column title="物料名称" data-index="material_name_snapshot" width="170" />
                    <a-table-column title="数量" key="quantity" width="110" />
                    <a-table-column title="建议下达" data-index="release_date" width="110" />
                    <a-table-column title="需求日期" data-index="due_date" width="110" />
                    <a-table-column title="状态" data-index="status" key="status" width="100" />
                    <a-table-column title="正式单据" data-index="source_document_no" width="150" />
                    <a-table-column title="操作" key="action" width="150" fixed="right" />
                  </a-table>
                </a-tab-pane>
              </a-tabs>
            </template>
          </a-card>
        </div>
      </a-tab-pane>
    </a-tabs>

    <a-modal
      v-model:open="dialogVisible"
      :title="dialogTitle"
      :confirm-loading="saving"
      width="620px"
      @ok="submit"
    >
      <a-form layout="vertical" :model="form">
        <template v-if="dialogKind === 'createPlan'">
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="计划编号"><a-input v-model:value="form.plan_no" placeholder="留空自动生成" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="计划名称" required><a-input v-model:value="form.plan_name" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="计划开始" required><a-date-picker v-model:value="form.horizon_start" value-format="YYYY-MM-DD" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="计划结束" required><a-date-picker v-model:value="form.horizon_end" value-format="YYYY-MM-DD" class="w-full" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="备注"><a-textarea v-model:value="form.remark" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'demand'">
          <a-form-item label="需求物料" required>
            <a-select
              v-model:value="form.material_id"
              show-search
              :filter-option="(input: string, option: any) => option.label.toLowerCase().includes(input.toLowerCase())"
              :options="materials.map((item) => ({ label: `${item.code} - ${item.name}`, value: item.id }))"
            />
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="需求类型"><a-select v-model:value="form.demand_type" :options="[{ label: '手工需求', value: 'MANUAL' }, { label: '预测需求', value: 'FORECAST' }]" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="需求日期" required><a-date-picker v-model:value="form.demand_date" value-format="YYYY-MM-DD" class="w-full" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="需求数量" required><a-input-number v-model:value="form.quantity" class="w-full" :min="0.000001" :precision="6" /></a-form-item>
          <a-form-item label="备注"><a-textarea v-model:value="form.remark" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'importSales'">
          <a-form-item label="已确认销售订单" required>
            <a-select
              v-model:value="form.sales_order_ids"
              mode="multiple"
              show-search
              :options="salesOrders.map((item) => ({ label: `${item.sales_order_no} - ${item.customer_name_snapshot}`, value: item.id }))"
            />
          </a-form-item>
          <a-form-item label="统一需求日期" required><a-date-picker v-model:value="form.demand_date" value-format="YYYY-MM-DD" class="w-full" /></a-form-item>
          <a-alert message="销售订单当前没有承诺交期字段，本次导入使用这里指定的统一需求日期。" type="info" show-icon />
        </template>

        <template v-else-if="dialogKind === 'runMrp'">
          <a-row :gutter="16">
            <a-col :span="8"><a-form-item label="抵扣可用库存"><a-switch v-model:checked="form.include_inventory" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="抵扣采购在途"><a-switch v-model:checked="form.include_open_purchase" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="抵扣生产在制"><a-switch v-model:checked="form.include_open_production" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="采购提前期（天）"><a-input-number v-model:value="form.default_purchase_lead_days" class="w-full" :min="0" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="生产提前期（天）"><a-input-number v-model:value="form.default_production_lead_days" class="w-full" :min="0" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="最大展开层级"><a-input-number v-model:value="form.max_level" class="w-full" :min="1" :max="100" /></a-form-item></a-col>
          </a-row>
        </template>

        <template v-else>
          <a-descriptions class="mb-3" :column="1" size="small" bordered>
            <a-descriptions-item label="计划订单">{{ selectedPlannedOrder?.planned_order_no }}</a-descriptions-item>
            <a-descriptions-item label="类型">{{ selectedPlannedOrder?.order_type }}</a-descriptions-item>
            <a-descriptions-item label="物料">{{ selectedPlannedOrder?.material_code_snapshot }} - {{ selectedPlannedOrder?.material_name_snapshot }}</a-descriptions-item>
            <a-descriptions-item label="数量">{{ number(selectedPlannedOrder?.quantity) }}</a-descriptions-item>
          </a-descriptions>
          <template v-if="selectedPlannedOrder?.order_type === 'PURCHASE'">
            <a-form-item label="供应商" required>
              <a-select
                v-model:value="form.supplier_id"
                show-search
                :options="suppliers.map((item) => ({ label: `${item.code} - ${item.name}`, value: item.id }))"
              />
            </a-form-item>
            <a-row :gutter="16">
              <a-col :span="12"><a-form-item label="币种"><a-input v-model:value="form.currency" /></a-form-item></a-col>
              <a-col :span="12"><a-form-item label="参考单价"><a-input-number v-model:value="form.unit_price" class="w-full" :min="0" :precision="6" /></a-form-item></a-col>
            </a-row>
          </template>
          <a-alert v-else class="mb-3" message="系统将使用该物料的默认生效工艺路线创建生产工单草稿。" type="info" show-icon />
          <a-form-item label="下达备注"><a-textarea v-model:value="form.remark" /></a-form-item>
        </template>
      </a-form>
    </a-modal>
  </Page>
</template>
