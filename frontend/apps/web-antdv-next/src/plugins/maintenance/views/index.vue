<script lang="ts" setup>
import type {
  EquipmentDowntime,
  EquipmentOption,
  MaintenanceDashboard,
  MaintenancePlan,
  MaintenanceTask,
  RepairOrder,
  UserOption,
  WorkCenterOption,
} from '../api';

import { computed, onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';
import dayjs from 'dayjs';

import {
  assignRepairOrderApi,
  cancelRepairOrderApi,
  closeEquipmentDowntimeApi,
  completeMaintenanceTaskApi,
  completeRepairOrderApi,
  createEquipmentDowntimeApi,
  createMaintenancePlanApi,
  createRepairOrderApi,
  generateDueTasksApi,
  getEquipmentDowntimesApi,
  getMaintenanceDashboardApi,
  getMaintenanceEquipmentOptionsApi,
  getMaintenancePlansApi,
  getMaintenanceTasksApi,
  getMaintenanceUserOptionsApi,
  getMaintenanceWorkCenterOptionsApi,
  getRepairOrdersApi,
  startMaintenanceTaskApi,
  startRepairOrderApi,
  updateMaintenancePlanApi,
} from '../api';

type DialogKind =
  | 'assignRepair'
  | 'closeDowntime'
  | 'completeRepair'
  | 'completeTask'
  | 'downtime'
  | 'generate'
  | 'plan'
  | 'repair';

const emptyDashboard: MaintenanceDashboard = {
  active_plans: 0,
  completion_rate_30d: 0,
  critical_repairs: 0,
  downtime_minutes_30d: 0,
  in_progress_tasks: 0,
  open_downtimes: 0,
  open_repairs: 0,
  overdue_tasks: 0,
  pending_tasks: 0,
};

const activeTab = ref('dashboard');
const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const dialogKind = ref<DialogKind>('plan');
const form = ref<Record<string, any>>({});
const dashboard = ref<MaintenanceDashboard>({ ...emptyDashboard });
const plans = ref<MaintenancePlan[]>([]);
const tasks = ref<MaintenanceTask[]>([]);
const repairs = ref<RepairOrder[]>([]);
const downtimes = ref<EquipmentDowntime[]>([]);
const equipmentOptions = ref<EquipmentOption[]>([]);
const workCenterOptions = ref<WorkCenterOption[]>([]);
const userOptions = ref<UserOption[]>([]);
const editingPlan = ref<MaintenancePlan>();
const selectedTask = ref<MaintenanceTask>();
const selectedRepair = ref<RepairOrder>();
const selectedDowntime = ref<EquipmentDowntime>();
const taskStatusFilter = ref<string>();
const repairStatusFilter = ref<string>();
const downtimeStatusFilter = ref<string>();

const filteredTasks = computed(() =>
  taskStatusFilter.value
    ? tasks.value.filter((item) => item.status === taskStatusFilter.value)
    : tasks.value,
);
const filteredRepairs = computed(() =>
  repairStatusFilter.value
    ? repairs.value.filter((item) => item.status === repairStatusFilter.value)
    : repairs.value,
);
const filteredDowntimes = computed(() =>
  downtimeStatusFilter.value
    ? downtimes.value.filter((item) => item.status === downtimeStatusFilter.value)
    : downtimes.value,
);

const dialogTitle = computed(() => ({
  assignRepair: '指派维修人员',
  closeDowntime: '关闭停机记录',
  completeRepair: '完成维修',
  completeTask: '完成点检/保养任务',
  downtime: '登记设备停机',
  generate: '生成到期运维任务',
  plan: editingPlan.value ? '编辑运维计划' : '新建运维计划',
  repair: '设备故障报修',
}[dialogKind.value]));

const statusText: Record<string, string> = {
  ACTIVE: '启用',
  ASSIGNED: '已指派',
  CANCELLED: '已取消',
  CLOSED: '已关闭',
  COMPLETED: '已完成',
  DISABLED: '停用',
  IN_PROGRESS: '执行中',
  IN_REPAIR: '维修中',
  OPEN: '停机中',
  PENDING: '待执行',
  REPORTED: '已报修',
};

function statusColor(status: string) {
  return {
    ACTIVE: 'green',
    ASSIGNED: 'blue',
    CANCELLED: 'default',
    CLOSED: 'green',
    COMPLETED: 'green',
    CRITICAL: 'red',
    DISABLED: 'default',
    FAIL: 'red',
    IN_PROGRESS: 'processing',
    IN_REPAIR: 'processing',
    MAJOR: 'orange',
    MINOR: 'blue',
    NA: 'default',
    OPEN: 'red',
    PASS: 'green',
    PENDING: 'gold',
    REPORTED: 'orange',
  }[status] ?? 'default';
}

function formatDateTime(value?: string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-';
}

function equipmentLabel(id?: number) {
  const item = equipmentOptions.value.find((option) => option.id === id);
  return item ? `${item.code} · ${item.name}` : '-';
}

async function loadAll() {
  loading.value = true;
  try {
    const [dashboardRow, planRows, taskRows, repairRows, downtimeRows, equipmentRows, centerRows, userRows] = await Promise.all([
      getMaintenanceDashboardApi(),
      getMaintenancePlansApi(),
      getMaintenanceTasksApi(),
      getRepairOrdersApi(),
      getEquipmentDowntimesApi(),
      getMaintenanceEquipmentOptionsApi(),
      getMaintenanceWorkCenterOptionsApi(),
      getMaintenanceUserOptionsApi(),
    ]);
    dashboard.value = dashboardRow;
    plans.value = planRows;
    tasks.value = taskRows;
    repairs.value = repairRows;
    downtimes.value = downtimeRows;
    equipmentOptions.value = equipmentRows;
    workCenterOptions.value = centerRows.filter((item) => item.status === 'ACTIVE');
    userOptions.value = Array.isArray(userRows) ? userRows : userRows.items;
  } finally {
    loading.value = false;
  }
}

function openPlan(record?: MaintenancePlan) {
  dialogKind.value = 'plan';
  editingPlan.value = record;
  form.value = record
    ? {
        assigned_user_id: record.assigned_user_id,
        checklist_items: [...record.checklist_items],
        cycle_unit: record.cycle_unit,
        cycle_value: record.cycle_value,
        equipment_id: record.equipment_id,
        estimated_minutes: record.estimated_minutes,
        lead_days: record.lead_days,
        next_due_date: record.next_due_date,
        plan_name: record.plan_name,
        plan_no: record.plan_no,
        plan_type: record.plan_type,
        remark: record.remark,
        requires_shutdown: record.requires_shutdown,
        status: record.status,
        work_center_id: record.work_center_id,
      }
    : {
        checklist_items: [],
        cycle_unit: 'MONTH',
        cycle_value: 1,
        estimated_minutes: 30,
        lead_days: 0,
        next_due_date: dayjs().add(1, 'month').format('YYYY-MM-DD'),
        plan_type: 'PREVENTIVE',
        requires_shutdown: false,
      };
  dialogVisible.value = true;
}

function openGenerate() {
  dialogKind.value = 'generate';
  form.value = {
    max_tasks: 500,
    through_date: dayjs().add(30, 'day').format('YYYY-MM-DD'),
  };
  dialogVisible.value = true;
}

function openCompleteTask(record: MaintenanceTask) {
  dialogKind.value = 'completeTask';
  selectedTask.value = record;
  form.value = {
    action_taken: '',
    create_repair_on_fail: true,
    findings: '',
    result: 'PASS',
  };
  dialogVisible.value = true;
}

function openRepair() {
  dialogKind.value = 'repair';
  selectedRepair.value = undefined;
  form.value = {
    affects_capacity: true,
    fault_level: 'MINOR',
    reported_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  };
  dialogVisible.value = true;
}

function openAssignRepair(record: RepairOrder) {
  dialogKind.value = 'assignRepair';
  selectedRepair.value = record;
  form.value = { assigned_user_id: record.assigned_user_id };
  dialogVisible.value = true;
}

function openCompleteRepair(record: RepairOrder) {
  dialogKind.value = 'completeRepair';
  selectedRepair.value = record;
  form.value = {
    completed_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
    repair_cost: 0,
  };
  dialogVisible.value = true;
}

function openDowntime() {
  dialogKind.value = 'downtime';
  selectedDowntime.value = undefined;
  form.value = {
    affects_capacity: true,
    category: 'PLANNED',
    source_type: 'MANUAL',
    start_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  };
  dialogVisible.value = true;
}

function openCloseDowntime(record: EquipmentDowntime) {
  dialogKind.value = 'closeDowntime';
  selectedDowntime.value = record;
  form.value = { end_at: dayjs().format('YYYY-MM-DD HH:mm:ss') };
  dialogVisible.value = true;
}

function requireFields(fields: string[]) {
  const missing = fields.some((field) => form.value[field] === undefined || form.value[field] === null || form.value[field] === '');
  if (missing) message.warning('请填写所有必填项');
  return !missing;
}

async function submit() {
  if (dialogKind.value === 'plan' && !requireFields(['plan_name', 'equipment_id', 'plan_type', 'next_due_date'])) return;
  if (dialogKind.value === 'generate' && !requireFields(['through_date'])) return;
  if (dialogKind.value === 'completeTask' && !requireFields(['result'])) return;
  if (dialogKind.value === 'repair' && !requireFields(['equipment_id', 'fault_description'])) return;
  if (dialogKind.value === 'assignRepair' && !requireFields(['assigned_user_id'])) return;
  if (dialogKind.value === 'completeRepair' && !requireFields(['root_cause', 'repair_action'])) return;
  if (dialogKind.value === 'downtime' && !requireFields(['equipment_id', 'category', 'start_at'])) return;
  if (dialogKind.value === 'closeDowntime' && !requireFields(['end_at'])) return;

  saving.value = true;
  try {
    if (dialogKind.value === 'plan') {
      if (editingPlan.value) await updateMaintenancePlanApi(editingPlan.value.id, form.value);
      else await createMaintenancePlanApi(form.value);
      message.success('运维计划已保存');
    } else if (dialogKind.value === 'generate') {
      const generated = await generateDueTasksApi(form.value);
      message.success(`已生成 ${generated.length} 条运维任务`);
      activeTab.value = 'tasks';
    } else if (dialogKind.value === 'completeTask' && selectedTask.value) {
      await completeMaintenanceTaskApi(selectedTask.value.id, form.value);
      message.success('运维任务已完成');
    } else if (dialogKind.value === 'repair') {
      await createRepairOrderApi(form.value);
      message.success('维修工单已创建');
      activeTab.value = 'repairs';
    } else if (dialogKind.value === 'assignRepair' && selectedRepair.value) {
      await assignRepairOrderApi(selectedRepair.value.id, form.value);
      message.success('维修人员已指派');
    } else if (dialogKind.value === 'completeRepair' && selectedRepair.value) {
      await completeRepairOrderApi(selectedRepair.value.id, form.value);
      message.success('维修已完成，关联停机已关闭');
    } else if (dialogKind.value === 'downtime') {
      const data = { ...form.value };
      if (!data.end_at) delete data.end_at;
      await createEquipmentDowntimeApi(data);
      message.success('停机记录已创建');
      activeTab.value = 'downtimes';
    } else if (dialogKind.value === 'closeDowntime' && selectedDowntime.value) {
      await closeEquipmentDowntimeApi(selectedDowntime.value.id, form.value);
      message.success('停机记录已关闭');
    }
    dialogVisible.value = false;
    await loadAll();
  } finally {
    saving.value = false;
  }
}

async function startTask(record: MaintenanceTask) {
  await startMaintenanceTaskApi(record.id);
  message.success(record.requires_shutdown ? '任务已开始，计划停机已自动创建' : '任务已开始');
  await loadAll();
}

async function startRepair(record: RepairOrder) {
  await startRepairOrderApi(record.id);
  message.success('维修已开始');
  await loadAll();
}

async function cancelRepair(record: RepairOrder) {
  await cancelRepairOrderApi(record.id);
  message.success('维修工单已取消');
  await loadAll();
}

onMounted(loadAll);
</script>

<template>
  <Page title="设备运维与停机管理" auto-content-height>
    <div class="mb-3 flex items-center justify-between">
      <a-alert class="mr-3 flex-1" message="运维任务和维修工单产生的停机会自动扣减 APS 工作中心可用产能。" type="info" show-icon />
      <a-space>
        <a-button @click="loadAll">刷新</a-button>
        <a-button @click="openDowntime">登记停机</a-button>
        <a-button type="primary" @click="openRepair">故障报修</a-button>
      </a-space>
    </div>

    <a-tabs v-model:active-key="activeTab">
      <a-tab-pane key="dashboard" tab="运维看板">
        <a-spin :spinning="loading">
          <a-row :gutter="12">
            <a-col :span="6"><a-card><a-statistic title="有效运维计划" :value="dashboard.active_plans" /></a-card></a-col>
            <a-col :span="6"><a-card><a-statistic title="待执行任务" :value="dashboard.pending_tasks" /></a-card></a-col>
            <a-col :span="6"><a-card><a-statistic title="逾期任务" :value="dashboard.overdue_tasks" :value-style="dashboard.overdue_tasks ? { color: '#cf1322' } : {}" /></a-card></a-col>
            <a-col :span="6"><a-card><a-statistic title="执行中任务" :value="dashboard.in_progress_tasks" /></a-card></a-col>
          </a-row>
          <a-row :gutter="12" class="mt-3">
            <a-col :span="6"><a-card><a-statistic title="未关闭维修" :value="dashboard.open_repairs" /></a-card></a-col>
            <a-col :span="6"><a-card><a-statistic title="重大故障" :value="dashboard.critical_repairs" :value-style="dashboard.critical_repairs ? { color: '#cf1322' } : {}" /></a-card></a-col>
            <a-col :span="6"><a-card><a-statistic title="当前停机设备" :value="dashboard.open_downtimes" /></a-card></a-col>
            <a-col :span="6"><a-card><a-statistic title="近 30 天停机(分钟)" :value="Number(dashboard.downtime_minutes_30d)" :precision="1" /></a-card></a-col>
          </a-row>
          <a-card class="mt-3" title="近 30 天运维任务完成率">
            <a-progress :percent="Math.min(100, Number(dashboard.completion_rate_30d))" :status="Number(dashboard.completion_rate_30d) < 80 ? 'exception' : 'success'" />
          </a-card>
          <div class="mt-3 grid grid-cols-2 gap-3">
            <a-card title="近期逾期任务" :body-style="{ padding: '12px' }">
              <a-list :data-source="tasks.filter((item) => item.overdue).slice(0, 8)" size="small">
                <template #renderItem="{ item }">
                  <a-list-item>
                    <a-list-item-meta :title="`${item.task_no} · ${item.equipment_name}`" :description="`${item.plan_name} / 到期 ${item.due_date}`" />
                    <a-tag color="red">逾期</a-tag>
                  </a-list-item>
                </template>
              </a-list>
              <a-empty v-if="!tasks.some((item) => item.overdue)" description="暂无逾期任务" />
            </a-card>
            <a-card title="当前停机" :body-style="{ padding: '12px' }">
              <a-list :data-source="downtimes.filter((item) => item.status === 'OPEN').slice(0, 8)" size="small">
                <template #renderItem="{ item }">
                  <a-list-item>
                    <a-list-item-meta :title="`${item.downtime_no} · ${item.equipment_name}`" :description="`${formatDateTime(item.start_at)} / ${item.reason || '未填写原因'}`" />
                    <a-tag color="red">停机中</a-tag>
                  </a-list-item>
                </template>
              </a-list>
              <a-empty v-if="!downtimes.some((item) => item.status === 'OPEN')" description="当前无停机设备" />
            </a-card>
          </div>
        </a-spin>
      </a-tab-pane>

      <a-tab-pane key="plans" tab="运维计划">
        <div class="mb-3 flex justify-end gap-2">
          <a-button @click="openGenerate">生成到期任务</a-button>
          <a-button type="primary" @click="openPlan()">新建计划</a-button>
        </div>
        <a-table :data-source="plans" :loading="loading" row-key="id" :pagination="{ pageSize: 20 }" :scroll="{ x: 1300 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'type'">{{ record.plan_type === 'INSPECTION' ? '点检' : '预防保养' }}</template>
            <template v-else-if="column.key === 'cycle'">每 {{ record.cycle_value }} {{ { DAY: '天', MONTH: '月', WEEK: '周' }[record.cycle_unit as string] }}</template>
            <template v-else-if="column.key === 'shutdown'"><a-tag :color="record.requires_shutdown ? 'orange' : 'default'">{{ record.requires_shutdown ? '需停机' : '不停机' }}</a-tag></template>
            <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ statusText[record.status] }}</a-tag></template>
            <template v-else-if="column.key === 'action'"><a-button type="link" @click="openPlan(record)">编辑</a-button></template>
          </template>
          <a-table-column title="计划编号" data-index="plan_no" width="190" fixed="left" />
          <a-table-column title="计划名称" data-index="plan_name" width="180" />
          <a-table-column title="设备" data-index="equipment_name" width="160" />
          <a-table-column title="工作中心" data-index="work_center_name" width="150" />
          <a-table-column title="类型" key="type" width="100" />
          <a-table-column title="周期" key="cycle" width="100" />
          <a-table-column title="下次到期" data-index="next_due_date" width="120" />
          <a-table-column title="预计分钟" data-index="estimated_minutes" width="100" />
          <a-table-column title="停机要求" key="shutdown" width="100" />
          <a-table-column title="负责人" data-index="assigned_username" width="110" />
          <a-table-column title="状态" key="status" width="90" />
          <a-table-column title="操作" key="action" width="70" fixed="right" />
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="tasks" tab="点检/保养任务">
        <div class="mb-3 flex justify-between">
          <a-select v-model:value="taskStatusFilter" allow-clear placeholder="全部任务状态" class="w-40" :options="[
            { label: '待执行', value: 'PENDING' },
            { label: '执行中', value: 'IN_PROGRESS' },
            { label: '已完成', value: 'COMPLETED' },
          ]" />
          <a-button type="primary" @click="openGenerate">生成到期任务</a-button>
        </div>
        <a-table :data-source="filteredTasks" :loading="loading" row-key="id" :pagination="{ pageSize: 20 }" :scroll="{ x: 1450 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'due'"><span :class="record.overdue ? 'font-semibold text-red-500' : ''">{{ record.due_date }}{{ record.overdue ? '（逾期）' : '' }}</span></template>
            <template v-else-if="column.key === 'type'">{{ record.task_type === 'INSPECTION' ? '点检' : '预防保养' }}</template>
            <template v-else-if="column.key === 'result'"><a-tag v-if="record.result" :color="statusColor(record.result)">{{ record.result }}</a-tag><span v-else>-</span></template>
            <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ statusText[record.status] }}</a-tag></template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-popconfirm v-if="record.status === 'PENDING'" :title="record.requires_shutdown ? '开始后会自动创建计划停机，确认继续？' : '确认开始该任务？'" @confirm="startTask(record)"><a-button type="link" size="small">开始</a-button></a-popconfirm>
                <a-button v-if="record.status === 'IN_PROGRESS'" type="link" size="small" @click="openCompleteTask(record)">完成</a-button>
              </a-space>
            </template>
          </template>
          <a-table-column title="任务编号" data-index="task_no" width="190" fixed="left" />
          <a-table-column title="计划" data-index="plan_name" width="180" />
          <a-table-column title="设备" data-index="equipment_name" width="150" />
          <a-table-column title="工作中心" data-index="work_center_name" width="150" />
          <a-table-column title="类型" key="type" width="100" />
          <a-table-column title="到期日" key="due" width="145" />
          <a-table-column title="负责人" data-index="assigned_username" width="110" />
          <a-table-column title="预计分钟" data-index="estimated_minutes" width="100" />
          <a-table-column title="结果" key="result" width="80" />
          <a-table-column title="状态" key="status" width="100" />
          <a-table-column title="操作" key="action" width="120" fixed="right" />
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="repairs" tab="故障维修">
        <div class="mb-3 flex justify-between">
          <a-select v-model:value="repairStatusFilter" allow-clear placeholder="全部维修状态" class="w-40" :options="[
            { label: '已报修', value: 'REPORTED' }, { label: '已指派', value: 'ASSIGNED' },
            { label: '维修中', value: 'IN_REPAIR' }, { label: '已完成', value: 'COMPLETED' },
            { label: '已取消', value: 'CANCELLED' },
          ]" />
          <a-button type="primary" @click="openRepair">故障报修</a-button>
        </div>
        <a-table :data-source="filteredRepairs" :loading="loading" row-key="id" :pagination="{ pageSize: 20 }" :scroll="{ x: 1550 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'level'"><a-tag :color="statusColor(record.fault_level)">{{ { CRITICAL: '严重', MAJOR: '重大', MINOR: '一般' }[record.fault_level as string] }}</a-tag></template>
            <template v-else-if="column.key === 'capacity'"><a-tag :color="record.affects_capacity ? 'red' : 'default'">{{ record.affects_capacity ? '影响产能' : '不影响产能' }}</a-tag></template>
            <template v-else-if="column.key === 'reported'">{{ formatDateTime(record.reported_at) }}</template>
            <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ statusText[record.status] }}</a-tag></template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button v-if="['REPORTED', 'ASSIGNED'].includes(record.status)" type="link" size="small" @click="openAssignRepair(record)">指派</a-button>
                <a-popconfirm v-if="['REPORTED', 'ASSIGNED'].includes(record.status)" title="确认开始维修？" @confirm="startRepair(record)"><a-button type="link" size="small">开始</a-button></a-popconfirm>
                <a-button v-if="record.status === 'IN_REPAIR'" type="link" size="small" @click="openCompleteRepair(record)">完成</a-button>
                <a-popconfirm v-if="!['COMPLETED', 'CANCELLED'].includes(record.status)" title="确认取消维修工单并关闭关联停机？" @confirm="cancelRepair(record)"><a-button danger type="link" size="small">取消</a-button></a-popconfirm>
              </a-space>
            </template>
          </template>
          <a-table-column title="维修单号" data-index="repair_no" width="190" fixed="left" />
          <a-table-column title="设备" data-index="equipment_name" width="150" />
          <a-table-column title="工作中心" data-index="work_center_name" width="140" />
          <a-table-column title="等级" key="level" width="90" />
          <a-table-column title="故障描述" data-index="fault_description" width="240" ellipsis />
          <a-table-column title="报修时间" key="reported" width="160" />
          <a-table-column title="维修人员" data-index="assigned_username" width="110" />
          <a-table-column title="产能" key="capacity" width="110" />
          <a-table-column title="维修费用" data-index="repair_cost" width="100" />
          <a-table-column title="状态" key="status" width="100" />
          <a-table-column title="操作" key="action" width="220" fixed="right" />
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="downtimes" tab="停机流水">
        <div class="mb-3 flex justify-between">
          <a-select v-model:value="downtimeStatusFilter" allow-clear placeholder="全部停机状态" class="w-40" :options="[{ label: '停机中', value: 'OPEN' }, { label: '已关闭', value: 'CLOSED' }]" />
          <a-button type="primary" @click="openDowntime">登记停机</a-button>
        </div>
        <a-table :data-source="filteredDowntimes" :loading="loading" row-key="id" :pagination="{ pageSize: 20 }" :scroll="{ x: 1500 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'category'"><a-tag :color="record.category === 'UNPLANNED' ? 'red' : 'orange'">{{ record.category === 'UNPLANNED' ? '非计划' : '计划' }}</a-tag></template>
            <template v-else-if="column.key === 'source'">{{ { INSPECTION: '点检', MAINTENANCE: '保养', MANUAL: '人工', REPAIR: '维修' }[record.source_type as string] }}</template>
            <template v-else-if="column.key === 'period'">{{ formatDateTime(record.start_at) }} → {{ formatDateTime(record.end_at) }}</template>
            <template v-else-if="column.key === 'capacity'"><a-tag :color="record.affects_capacity ? 'red' : 'default'">{{ record.affects_capacity ? '扣减 APS 产能' : '仅记录' }}</a-tag></template>
            <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ statusText[record.status] }}</a-tag></template>
            <template v-else-if="column.key === 'action'"><a-button v-if="record.status === 'OPEN'" type="link" @click="openCloseDowntime(record)">关闭停机</a-button></template>
          </template>
          <a-table-column title="停机编号" data-index="downtime_no" width="190" fixed="left" />
          <a-table-column title="设备" data-index="equipment_name" width="150" />
          <a-table-column title="工作中心" data-index="work_center_name" width="140" />
          <a-table-column title="类别" key="category" width="90" />
          <a-table-column title="来源" key="source" width="80" />
          <a-table-column title="停机区间" key="period" width="310" />
          <a-table-column title="时长(分钟)" data-index="duration_minutes" width="110" />
          <a-table-column title="APS 影响" key="capacity" width="130" />
          <a-table-column title="原因" data-index="reason" width="220" ellipsis />
          <a-table-column title="状态" key="status" width="90" />
          <a-table-column title="操作" key="action" width="100" fixed="right" />
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="dialogVisible" :title="dialogTitle" :confirm-loading="saving" width="720px" @ok="submit">
      <a-form :model="form" layout="vertical">
        <template v-if="dialogKind === 'plan'">
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="计划编号"><a-input v-model:value="form.plan_no" placeholder="留空自动生成" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="计划名称" required><a-input v-model:value="form.plan_name" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="设备" required><a-select v-model:value="form.equipment_id" show-search option-filter-prop="label" :options="equipmentOptions.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="工作中心"><a-select v-model:value="form.work_center_id" allow-clear show-search option-filter-prop="label" :options="workCenterOptions.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="计划类型" required><a-select v-model:value="form.plan_type" :options="[{ label: '设备点检', value: 'INSPECTION' }, { label: '预防保养', value: 'PREVENTIVE' }]" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="周期单位"><a-select v-model:value="form.cycle_unit" :options="[{ label: '天', value: 'DAY' }, { label: '周', value: 'WEEK' }, { label: '月', value: 'MONTH' }]" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="周期间隔"><a-input-number v-model:value="form.cycle_value" :min="1" :max="999" class="w-full" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="下次到期日" required><a-date-picker v-model:value="form.next_due_date" value-format="YYYY-MM-DD" class="w-full" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="提前生成天数"><a-input-number v-model:value="form.lead_days" :min="0" :max="365" class="w-full" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="预计执行分钟"><a-input-number v-model:value="form.estimated_minutes" :min="1" :max="10080" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="负责人"><a-select v-model:value="form.assigned_user_id" allow-clear show-search option-filter-prop="label" :options="userOptions.map((item) => ({ label: `${item.username} · ${item.nickname || ''}`, value: item.id }))" /></a-form-item></a-col>
            <a-col v-if="editingPlan" :span="6"><a-form-item label="状态"><a-select v-model:value="form.status" :options="[{ label: '启用', value: 'ACTIVE' }, { label: '停用', value: 'DISABLED' }]" /></a-form-item></a-col>
            <a-col :span="6"><a-form-item label="执行时停机"><a-switch v-model:checked="form.requires_shutdown" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="检查清单"><a-select v-model:value="form.checklist_items" mode="tags" placeholder="输入检查项后回车，可添加多项" /></a-form-item>
          <a-form-item label="备注"><a-textarea v-model:value="form.remark" :rows="2" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'generate'">
          <a-alert class="mb-4" message="系统会按基准日期和各计划的提前天数生成任务，并自动推进计划的下一到期日。" type="info" show-icon />
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="生成基准日期" required><a-date-picker v-model:value="form.through_date" value-format="YYYY-MM-DD" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="单次最大任务数"><a-input-number v-model:value="form.max_tasks" :min="1" :max="5000" class="w-full" /></a-form-item></a-col>
          </a-row>
        </template>

        <template v-else-if="dialogKind === 'completeTask'">
          <a-descriptions class="mb-4" :column="2" bordered size="small">
            <a-descriptions-item label="任务">{{ selectedTask?.task_no }}</a-descriptions-item>
            <a-descriptions-item label="设备">{{ selectedTask?.equipment_name }}</a-descriptions-item>
            <a-descriptions-item label="计划">{{ selectedTask?.plan_name }}</a-descriptions-item>
            <a-descriptions-item label="检查项">{{ selectedTask?.checklist_items.join('、') || '-' }}</a-descriptions-item>
          </a-descriptions>
          <a-form-item label="执行结果" required><a-radio-group v-model:value="form.result"><a-radio-button value="PASS">合格</a-radio-button><a-radio-button value="FAIL">不合格</a-radio-button><a-radio-button value="NA">不适用</a-radio-button></a-radio-group></a-form-item>
          <a-form-item label="发现问题"><a-textarea v-model:value="form.findings" :rows="3" /></a-form-item>
          <a-form-item label="处理措施"><a-textarea v-model:value="form.action_taken" :rows="3" /></a-form-item>
          <a-form-item v-if="form.result === 'FAIL'" label="不合格时自动报修"><a-switch v-model:checked="form.create_repair_on_fail" /></a-form-item>
          <a-form-item label="备注"><a-textarea v-model:value="form.remark" :rows="2" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'repair'">
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="维修单号"><a-input v-model:value="form.repair_no" placeholder="留空自动生成" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="故障等级"><a-select v-model:value="form.fault_level" :options="[{ label: '一般', value: 'MINOR' }, { label: '重大', value: 'MAJOR' }, { label: '严重', value: 'CRITICAL' }]" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="设备" required><a-select v-model:value="form.equipment_id" show-search option-filter-prop="label" :options="equipmentOptions.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="工作中心"><a-select v-model:value="form.work_center_id" allow-clear show-search option-filter-prop="label" :options="workCenterOptions.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="报修时间"><a-date-picker v-model:value="form.reported_at" show-time value-format="YYYY-MM-DD HH:mm:ss" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="维修人员"><a-select v-model:value="form.assigned_user_id" allow-clear show-search option-filter-prop="label" :options="userOptions.map((item) => ({ label: `${item.username} · ${item.nickname || ''}`, value: item.id }))" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="故障描述" required><a-textarea v-model:value="form.fault_description" :rows="3" /></a-form-item>
          <a-form-item label="影响 APS 产能"><a-switch v-model:checked="form.affects_capacity" /><span class="ml-2 text-gray-500">开启后立即建立非计划停机</span></a-form-item>
          <a-form-item label="备注"><a-textarea v-model:value="form.remark" :rows="2" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'assignRepair'">
          <a-alert class="mb-4" :message="`${selectedRepair?.repair_no} · ${selectedRepair?.equipment_name}`" type="info" />
          <a-form-item label="维修人员" required><a-select v-model:value="form.assigned_user_id" show-search option-filter-prop="label" :options="userOptions.map((item) => ({ label: `${item.username} · ${item.nickname || ''}`, value: item.id }))" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'completeRepair'">
          <a-descriptions class="mb-4" :column="1" bordered size="small">
            <a-descriptions-item label="维修单">{{ selectedRepair?.repair_no }}</a-descriptions-item>
            <a-descriptions-item label="设备">{{ selectedRepair?.equipment_name }}</a-descriptions-item>
            <a-descriptions-item label="故障">{{ selectedRepair?.fault_description }}</a-descriptions-item>
          </a-descriptions>
          <a-form-item label="故障根因" required><a-textarea v-model:value="form.root_cause" :rows="3" /></a-form-item>
          <a-form-item label="维修措施" required><a-textarea v-model:value="form.repair_action" :rows="3" /></a-form-item>
          <a-form-item label="使用备件"><a-textarea v-model:value="form.spare_parts_used" :rows="2" /></a-form-item>
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="维修费用"><a-input-number v-model:value="form.repair_cost" :min="0" :precision="4" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="完成时间"><a-date-picker v-model:value="form.completed_at" show-time value-format="YYYY-MM-DD HH:mm:ss" class="w-full" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="备注"><a-textarea v-model:value="form.remark" :rows="2" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'downtime'">
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="停机编号"><a-input v-model:value="form.downtime_no" placeholder="留空自动生成" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="停机类别"><a-select v-model:value="form.category" :options="[{ label: '计划停机', value: 'PLANNED' }, { label: '非计划停机', value: 'UNPLANNED' }]" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="设备" required><a-select v-model:value="form.equipment_id" show-search option-filter-prop="label" :options="equipmentOptions.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="工作中心"><a-select v-model:value="form.work_center_id" allow-clear show-search option-filter-prop="label" :options="workCenterOptions.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="开始时间" required><a-date-picker v-model:value="form.start_at" show-time value-format="YYYY-MM-DD HH:mm:ss" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="结束时间"><a-date-picker v-model:value="form.end_at" show-time value-format="YYYY-MM-DD HH:mm:ss" class="w-full" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="停机原因"><a-textarea v-model:value="form.reason" :rows="3" /></a-form-item>
          <a-form-item label="影响 APS 产能"><a-switch v-model:checked="form.affects_capacity" /><span class="ml-2 text-gray-500">需同时绑定工作中心才会扣减产能</span></a-form-item>
          <a-form-item label="备注"><a-textarea v-model:value="form.remark" :rows="2" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'closeDowntime'">
          <a-descriptions class="mb-4" :column="1" bordered size="small">
            <a-descriptions-item label="停机记录">{{ selectedDowntime?.downtime_no }}</a-descriptions-item>
            <a-descriptions-item label="设备">{{ equipmentLabel(selectedDowntime?.equipment_id) }}</a-descriptions-item>
            <a-descriptions-item label="开始时间">{{ formatDateTime(selectedDowntime?.start_at) }}</a-descriptions-item>
          </a-descriptions>
          <a-form-item label="结束时间" required><a-date-picker v-model:value="form.end_at" show-time value-format="YYYY-MM-DD HH:mm:ss" class="w-full" /></a-form-item>
          <a-form-item label="关闭备注"><a-textarea v-model:value="form.remark" :rows="3" /></a-form-item>
        </template>
      </a-form>
    </a-modal>
  </Page>
</template>
