<script lang="ts" setup>
import type {
  ApsSchedule,
  Dispatch,
  OperationSchedule,
  Shift,
  UserOption,
  WorkCalendar,
  WorkCenterLoad,
  WorkCenterOption,
  WorkOrderCandidate,
} from '../api';

import { computed, onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';
import dayjs from 'dayjs';

import {
  acceptDispatchApi,
  assignWorkCenterApi,
  cancelDispatchApi,
  createCalendarApi,
  createDispatchApi,
  createShiftApi,
  getCalendarApi,
  getCalendarsApi,
  getDispatchesApi,
  getScheduleApi,
  getScheduleLoadsApi,
  getSchedulesApi,
  getShiftsApi,
  getUserOptionsApi,
  getWorkCenterOptionsApi,
  getWorkOrderCandidatesApi,
  publishScheduleApi,
  runScheduleApi,
  updateCalendarApi,
  updateShiftApi,
  upsertCalendarDayApi,
} from '../api';

type DialogKind = 'assignment' | 'calendar' | 'day' | 'dispatch' | 'schedule' | 'shift';

interface GanttRow {
  key: string;
  label: string;
  items: Array<OperationSchedule & { left: number; width: number }>;
}

const loading = ref(false);
const saving = ref(false);
const activeTab = ref('schedule');
const dialogVisible = ref(false);
const dialogKind = ref<DialogKind>('schedule');
const form = ref<Record<string, any>>({});
const shifts = ref<Shift[]>([]);
const calendars = ref<WorkCalendar[]>([]);
const schedules = ref<ApsSchedule[]>([]);
const dispatches = ref<Dispatch[]>([]);
const candidates = ref<WorkOrderCandidate[]>([]);
const workCenters = ref<WorkCenterOption[]>([]);
const users = ref<UserOption[]>([]);
const loads = ref<WorkCenterLoad[]>([]);
const selectedCalendar = ref<WorkCalendar>();
const selectedSchedule = ref<ApsSchedule>();
const selectedOperation = ref<OperationSchedule>();
const editingShift = ref<Shift>();
const editingCalendar = ref<WorkCalendar>();

const dialogTitle = computed(() => ({
  assignment: '分配工作中心日历',
  calendar: editingCalendar.value ? '编辑工作日历' : '新建工作日历',
  day: '设置日期例外',
  dispatch: '工序派工',
  schedule: '运行有限产能排程',
  shift: editingShift.value ? '编辑班次' : '新建班次',
}[dialogKind.value]));

const ganttRows = computed<GanttRow[]>(() => {
  const schedule = selectedSchedule.value;
  if (!schedule?.operations?.length) return [];
  const start = dayjs(schedule.horizon_start_at).valueOf();
  const end = dayjs(schedule.horizon_end_at).valueOf();
  const span = Math.max(end - start, 1);
  const groups = new Map<string, GanttRow>();
  for (const item of schedule.operations) {
    const key = `${item.work_center_id}-${item.lane_no}`;
    const row = groups.get(key) ?? {
      key,
      label: `${item.work_center_code_snapshot} · 通道 ${item.lane_no}`,
      items: [],
    };
    const itemStart = dayjs(item.planned_start_at).valueOf();
    const itemEnd = dayjs(item.planned_end_at).valueOf();
    const left = Math.max(0, Math.min(100, ((itemStart - start) / span) * 100));
    const right = Math.max(left + 0.5, Math.min(100, ((itemEnd - start) / span) * 100));
    row.items.push({ ...item, left, width: Math.max(0.5, right - left) });
    groups.set(key, row);
  }
  return [...groups.values()].sort((a, b) => a.label.localeCompare(b.label));
});

const totalLoad = computed(() => loads.value.reduce((sum, item) => sum + Number(item.scheduled_load_minutes), 0));
const overloadedCenters = computed(() => loads.value.filter((item) => Number(item.overload_minutes) > 0).length);

function statusColor(status: string) {
  return {
    ACCEPTED: 'blue',
    ACTIVE: 'green',
    CANCELLED: 'default',
    COMPLETED: 'green',
    DISABLED: 'default',
    DISPATCHED: 'cyan',
    FAILED: 'red',
    PLANNED: 'gold',
    PUBLISHED: 'purple',
    RUNNING: 'processing',
  }[status] ?? 'default';
}

function formatDateTime(value?: string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-';
}

async function loadAll() {
  loading.value = true;
  try {
    const [shiftRows, calendarRows, scheduleRows, dispatchRows, orderRows, centerRows, userRows] = await Promise.all([
      getShiftsApi(),
      getCalendarsApi(),
      getSchedulesApi(),
      getDispatchesApi(),
      getWorkOrderCandidatesApi(),
      getWorkCenterOptionsApi(),
      getUserOptionsApi(),
    ]);
    shifts.value = shiftRows;
    calendars.value = calendarRows;
    schedules.value = scheduleRows;
    dispatches.value = dispatchRows;
    candidates.value = orderRows;
    workCenters.value = centerRows;
    users.value = Array.isArray(userRows) ? userRows : userRows.items;
    if (selectedSchedule.value) await selectSchedule(selectedSchedule.value);
    if (selectedCalendar.value) await selectCalendar(selectedCalendar.value);
  } finally {
    loading.value = false;
  }
}

async function selectSchedule(row: ApsSchedule) {
  selectedSchedule.value = await getScheduleApi(row.id);
  loads.value = await getScheduleLoadsApi(row.id);
}

async function selectCalendar(row: WorkCalendar) {
  selectedCalendar.value = await getCalendarApi(row.id);
}

function open(kind: DialogKind, record?: Shift | WorkCalendar | OperationSchedule) {
  dialogKind.value = kind;
  editingShift.value = undefined;
  editingCalendar.value = undefined;
  selectedOperation.value = undefined;
  if (kind === 'schedule') {
    const start = dayjs().add(1, 'day').hour(8).minute(0).second(0);
    form.value = {
      direction: 'FORWARD',
      horizon: [start.format('YYYY-MM-DD HH:mm:ss'), start.add(7, 'day').hour(18).format('YYYY-MM-DD HH:mm:ss')],
      include_move_time: true,
      include_queue_time: true,
      schedule_name: `APS ${start.format('YYYY-MM-DD')}`,
      work_order_ids: [],
    };
  } else if (kind === 'shift') {
    editingShift.value = record as Shift | undefined;
    form.value = record ? { ...record } : {
      break_minutes: 60,
      end_time: '17:00:00',
      spans_next_day: false,
      start_time: '08:00:00',
      status: 'ACTIVE',
    };
  } else if (kind === 'calendar') {
    editingCalendar.value = record as WorkCalendar | undefined;
    form.value = record ? { ...record } : {
      status: 'ACTIVE',
      timezone_name: 'Asia/Hong_Kong',
      weekday_mask: '1,2,3,4,5',
    };
  } else if (kind === 'day') {
    if (!selectedCalendar.value) return;
    form.value = { capacity_factor: 1, is_working_day: true, work_date: dayjs().format('YYYY-MM-DD') };
  } else if (kind === 'assignment') {
    if (!selectedCalendar.value) return;
    form.value = { capacity_factor: 1, effective_from: dayjs().format('YYYY-MM-DD'), priority: 0 };
  } else {
    selectedOperation.value = record as OperationSchedule;
    form.value = {
      dispatch_quantity: selectedOperation.value.planned_quantity,
      priority: 0,
      schedule_operation_id: selectedOperation.value.id,
    };
  }
  dialogVisible.value = true;
}

async function submit() {
  saving.value = true;
  try {
    if (dialogKind.value === 'schedule') {
      const { horizon, ...data } = form.value;
      selectedSchedule.value = await runScheduleApi({
        ...data,
        horizon_end_at: horizon?.[1],
        horizon_start_at: horizon?.[0],
      });
      message.success('APS 排程已完成');
      activeTab.value = 'schedule';
    } else if (dialogKind.value === 'shift') {
      const data = { ...form.value };
      if (editingShift.value) await updateShiftApi(editingShift.value.id, data);
      else await createShiftApi(data);
      message.success('班次已保存');
    } else if (dialogKind.value === 'calendar') {
      const data = { ...form.value };
      if (editingCalendar.value) selectedCalendar.value = await updateCalendarApi(editingCalendar.value.id, data);
      else selectedCalendar.value = await createCalendarApi(data);
      message.success('工作日历已保存');
    } else if (dialogKind.value === 'day' && selectedCalendar.value) {
      selectedCalendar.value = await upsertCalendarDayApi(selectedCalendar.value.id, form.value);
      message.success('日期例外已保存');
    } else if (dialogKind.value === 'assignment' && selectedCalendar.value) {
      selectedCalendar.value = await assignWorkCenterApi(selectedCalendar.value.id, form.value);
      message.success('工作中心日历已分配');
    } else {
      await createDispatchApi(form.value);
      message.success('派工单已创建');
    }
    dialogVisible.value = false;
    await loadAll();
  } finally {
    saving.value = false;
  }
}

async function publishSchedule() {
  if (!selectedSchedule.value) return;
  selectedSchedule.value = await publishScheduleApi(selectedSchedule.value.id);
  message.success('排程已发布，工单计划时间已更新');
  await loadAll();
}

async function dispatchAction(row: Dispatch, action: 'accept' | 'cancel') {
  if (action === 'accept') await acceptDispatchApi(row.id);
  else await cancelDispatchApi(row.id);
  message.success(action === 'accept' ? '派工已接收' : '派工已取消');
  await loadAll();
}

onMounted(loadAll);
</script>

<template>
  <Page title="APS 有限产能排程" auto-content-height>
    <a-tabs v-model:active-key="activeTab" class="h-full">
      <a-tab-pane key="schedule" tab="排程与甘特图">
        <div class="flex min-h-[700px] gap-3">
          <a-card class="w-[380px] shrink-0" :body-style="{ padding: '12px' }">
            <template #title>排程版本</template>
            <template #extra><a-button type="primary" @click="open('schedule')">运行 APS</a-button></template>
            <a-table
              :data-source="schedules"
              :loading="loading"
              :pagination="{ pageSize: 15 }"
              row-key="id"
              size="small"
              @row="(row: ApsSchedule) => ({ onClick: () => selectSchedule(row) })"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
              </template>
              <a-table-column title="排程编号" data-index="schedule_no" />
              <a-table-column title="方向" data-index="direction" width="90" />
              <a-table-column title="状态" data-index="status" key="status" width="95" />
            </a-table>
          </a-card>

          <a-card class="min-w-0 flex-1" :body-style="{ padding: '12px' }">
            <template #title>{{ selectedSchedule?.schedule_name ?? '排程详情' }}</template>
            <template #extra>
              <a-space v-if="selectedSchedule">
                <a-button @click="selectSchedule(selectedSchedule)">刷新</a-button>
                <a-button v-if="selectedSchedule.status === 'COMPLETED'" type="primary" @click="publishSchedule">发布排程</a-button>
              </a-space>
            </template>
            <a-empty v-if="!selectedSchedule" description="请选择或运行一个 APS 排程" />
            <template v-else>
              <a-row :gutter="12" class="mb-3">
                <a-col :span="6"><a-statistic title="生产工单" :value="selectedSchedule.work_order_count" /></a-col>
                <a-col :span="6"><a-statistic title="计划工序" :value="selectedSchedule.operation_count" /></a-col>
                <a-col :span="6"><a-statistic title="超期工序" :value="selectedSchedule.overdue_operation_count" :value-style="selectedSchedule.overdue_operation_count ? { color: '#cf1322' } : {}" /></a-col>
                <a-col :span="6"><a-statistic title="排程方向" :value="selectedSchedule.direction" /></a-col>
              </a-row>
              <a-alert
                v-if="selectedSchedule.overdue_operation_count"
                class="mb-3"
                message="部分工序超出排程时间窗，请扩展计划区间或调整工作中心产能。"
                type="warning"
                show-icon
              />
              <div class="gantt-shell">
                <div class="gantt-axis">
                  <span>{{ formatDateTime(selectedSchedule.horizon_start_at) }}</span>
                  <strong>有限产能甘特图</strong>
                  <span>{{ formatDateTime(selectedSchedule.horizon_end_at) }}</span>
                </div>
                <div v-for="row in ganttRows" :key="row.key" class="gantt-row">
                  <div class="gantt-label">{{ row.label }}</div>
                  <div class="gantt-track">
                    <div
                      v-for="item in row.items"
                      :key="item.id"
                      class="gantt-bar"
                      :class="{ overdue: item.is_overdue, published: item.status !== 'PLANNED' }"
                      :style="{ left: `${item.left}%`, width: `${item.width}%` }"
                      :title="`${item.work_order_no_snapshot} / ${item.operation_name_snapshot}\n${formatDateTime(item.planned_start_at)} - ${formatDateTime(item.planned_end_at)}`"
                      @click="selectedOperation = item"
                    >
                      {{ item.work_order_no_snapshot }} · {{ item.operation_name_snapshot }}
                    </div>
                  </div>
                </div>
              </div>
              <a-table class="mt-3" :data-source="selectedSchedule.operations" row-key="id" size="small" :pagination="{ pageSize: 10 }" :scroll="{ x: 1250 }">
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
                  <template v-else-if="column.key === 'time'">{{ formatDateTime(record.planned_start_at) }} → {{ formatDateTime(record.planned_end_at) }}</template>
                  <template v-else-if="column.key === 'action'">
                    <a-button v-if="['PUBLISHED', 'DISPATCHED'].includes(record.status)" type="link" size="small" @click="open('dispatch', record)">派工</a-button>
                  </template>
                </template>
                <a-table-column title="工单" data-index="work_order_no_snapshot" width="160" fixed="left" />
                <a-table-column title="产品" data-index="product_name_snapshot" width="150" />
                <a-table-column title="工序" data-index="operation_name_snapshot" width="130" />
                <a-table-column title="工作中心" data-index="work_center_name_snapshot" width="150" />
                <a-table-column title="通道" data-index="lane_no" width="70" />
                <a-table-column title="计划时间" key="time" width="280" />
                <a-table-column title="负荷(分钟)" data-index="load_minutes" width="110" />
                <a-table-column title="状态" data-index="status" key="status" width="105" />
                <a-table-column title="操作" key="action" width="80" fixed="right" />
              </a-table>
            </template>
          </a-card>
        </div>
      </a-tab-pane>

      <a-tab-pane key="load" tab="工作中心负荷">
        <a-empty v-if="!selectedSchedule" description="请先在排程页选择一个排程版本" />
        <template v-else>
          <a-row :gutter="12" class="mb-4">
            <a-col :span="8"><a-card><a-statistic title="工作中心" :value="loads.length" /></a-card></a-col>
            <a-col :span="8"><a-card><a-statistic title="总计划负荷(分钟)" :value="totalLoad" /></a-card></a-col>
            <a-col :span="8"><a-card><a-statistic title="超负荷中心" :value="overloadedCenters" :value-style="overloadedCenters ? { color: '#cf1322' } : {}" /></a-card></a-col>
          </a-row>
          <a-table :data-source="loads" row-key="work_center_id" :pagination="false">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'rate'">
                <a-progress :percent="Math.min(100, Number(record.utilization_rate))" :status="Number(record.utilization_rate) > 100 ? 'exception' : 'active'" />
                <span>{{ Number(record.utilization_rate).toFixed(2) }}%</span>
              </template>
              <template v-else-if="column.key === 'overload'">
                <span :class="Number(record.overload_minutes) > 0 ? 'text-red-500' : ''">{{ record.overload_minutes }}</span>
              </template>
            </template>
            <a-table-column title="工作中心编码" data-index="work_center_code" />
            <a-table-column title="工作中心" data-index="work_center_name" />
            <a-table-column title="并行通道" data-index="parallel_capacity" width="100" />
            <a-table-column title="可用分钟" data-index="available_minutes" />
            <a-table-column title="计划负荷" data-index="scheduled_load_minutes" />
            <a-table-column title="利用率" key="rate" width="260" />
            <a-table-column title="超负荷分钟" key="overload" />
          </a-table>
        </template>
      </a-tab-pane>

      <a-tab-pane key="calendar" tab="班次与工作日历">
        <div class="grid grid-cols-2 gap-3">
          <a-card title="生产班次" :body-style="{ padding: '12px' }">
            <template #extra><a-button type="primary" @click="open('shift')">新建班次</a-button></template>
            <a-table :data-source="shifts" row-key="id" size="small" :pagination="false">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'time'">{{ record.start_time }} - {{ record.end_time }}{{ record.spans_next_day ? '（跨日）' : '' }}</template>
                <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
                <template v-else-if="column.key === 'action'"><a-button type="link" @click="open('shift', record)">编辑</a-button></template>
              </template>
              <a-table-column title="编码" data-index="shift_code" />
              <a-table-column title="名称" data-index="shift_name" />
              <a-table-column title="工作时段" key="time" width="190" />
              <a-table-column title="休息分钟" data-index="break_minutes" width="90" />
              <a-table-column title="状态" data-index="status" key="status" width="90" />
              <a-table-column title="操作" key="action" width="70" />
            </a-table>
          </a-card>

          <a-card title="工作日历" :body-style="{ padding: '12px' }">
            <template #extra><a-button type="primary" @click="open('calendar')">新建日历</a-button></template>
            <a-table :data-source="calendars" row-key="id" size="small" :pagination="false" @row="(row: WorkCalendar) => ({ onClick: () => selectCalendar(row) })">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
                <template v-else-if="column.key === 'action'"><a-button type="link" @click.stop="open('calendar', record)">编辑</a-button></template>
              </template>
              <a-table-column title="编码" data-index="calendar_code" />
              <a-table-column title="名称" data-index="calendar_name" />
              <a-table-column title="工作日" data-index="weekday_mask" />
              <a-table-column title="默认班次" data-index="default_shift_name" />
              <a-table-column title="状态" data-index="status" key="status" width="90" />
              <a-table-column title="操作" key="action" width="70" />
            </a-table>
          </a-card>
        </div>
        <a-card class="mt-3" :title="selectedCalendar?.calendar_name ?? '日历详情'" :body-style="{ padding: '12px' }">
          <template #extra>
            <a-space v-if="selectedCalendar">
              <a-button @click="open('day')">设置日期例外</a-button>
              <a-button type="primary" @click="open('assignment')">分配工作中心</a-button>
            </a-space>
          </template>
          <a-empty v-if="!selectedCalendar" description="请选择一个工作日历" />
          <a-tabs v-else>
            <a-tab-pane key="assignments" tab="工作中心分配">
              <a-table :data-source="selectedCalendar.assignments" row-key="id" size="small" :pagination="false">
                <a-table-column title="工作中心编码" data-index="work_center_code" />
                <a-table-column title="工作中心" data-index="work_center_name" />
                <a-table-column title="生效日期" data-index="effective_from" />
                <a-table-column title="失效日期" data-index="effective_to" />
                <a-table-column title="产能系数" data-index="capacity_factor" />
                <a-table-column title="优先级" data-index="priority" />
              </a-table>
            </a-tab-pane>
            <a-tab-pane key="days" tab="日期例外">
              <a-table :data-source="selectedCalendar.days" row-key="id" size="small" :pagination="{ pageSize: 10 }">
                <a-table-column title="日期" data-index="work_date" />
                <a-table-column title="工作日" data-index="is_working_day" />
                <a-table-column title="班次 ID" data-index="shift_id" />
                <a-table-column title="产能系数" data-index="capacity_factor" />
                <a-table-column title="备注" data-index="remark" />
              </a-table>
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="dispatch" tab="车间派工">
        <div class="mb-3 flex items-center justify-between">
          <a-alert class="flex-1" message="发布排程后，可按人员、班组或工位拆分派工；派工总量不能超过工序计划量。" type="info" show-icon />
          <a-button class="ml-3" @click="loadAll">刷新</a-button>
        </div>
        <a-table :data-source="dispatches" row-key="id" :pagination="{ pageSize: 20 }" :scroll="{ x: 1300 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
            <template v-else-if="column.key === 'time'">{{ formatDateTime(record.planned_start_at) }} → {{ formatDateTime(record.planned_end_at) }}</template>
            <template v-else-if="column.key === 'assignee'">{{ record.assigned_username || record.assigned_team || record.workstation_code }}</template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button v-if="record.status === 'DISPATCHED'" type="link" size="small" @click="dispatchAction(record, 'accept')">接收</a-button>
                <a-popconfirm v-if="['DISPATCHED', 'ACCEPTED'].includes(record.status)" title="确认取消该派工？" @confirm="dispatchAction(record, 'cancel')"><a-button type="link" danger size="small">取消</a-button></a-popconfirm>
              </a-space>
            </template>
          </template>
          <a-table-column title="派工单号" data-index="dispatch_no" width="190" fixed="left" />
          <a-table-column title="工单" data-index="work_order_no" width="150" />
          <a-table-column title="工序" data-index="operation_name" width="130" />
          <a-table-column title="工作中心" data-index="work_center_name" width="150" />
          <a-table-column title="人员/班组/工位" key="assignee" width="180" />
          <a-table-column title="数量" data-index="dispatch_quantity" width="100" />
          <a-table-column title="优先级" data-index="priority" width="80" />
          <a-table-column title="计划时间" key="time" width="280" />
          <a-table-column title="状态" data-index="status" key="status" width="110" />
          <a-table-column title="操作" key="action" width="130" fixed="right" />
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="dialogVisible" :title="dialogTitle" :confirm-loading="saving" width="680px" @ok="submit">
      <a-form layout="vertical" :model="form">
        <template v-if="dialogKind === 'schedule'">
          <a-row :gutter="16">
            <a-col :span="14"><a-form-item label="排程名称" required><a-input v-model:value="form.schedule_name" /></a-form-item></a-col>
            <a-col :span="10"><a-form-item label="排程方向"><a-radio-group v-model:value="form.direction"><a-radio-button value="FORWARD">前向</a-radio-button><a-radio-button value="BACKWARD">后向</a-radio-button></a-radio-group></a-form-item></a-col>
          </a-row>
          <a-form-item label="计划时间窗" required><a-range-picker v-model:value="form.horizon" show-time value-format="YYYY-MM-DD HH:mm:ss" class="w-full" /></a-form-item>
          <a-form-item label="生产工单" required>
            <a-select v-model:value="form.work_order_ids" mode="multiple" show-search :options="candidates.map((item) => ({ label: `${item.work_order_no} · ${item.product_name} · ${item.operation_count} 道工序`, value: item.id }))" />
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="8"><a-form-item label="计入排队时间"><a-switch v-model:checked="form.include_queue_time" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="计入搬运时间"><a-switch v-model:checked="form.include_move_time" /></a-form-item></a-col>
          </a-row>
          <a-alert message="未分配工作日历的工作中心按周一至周五 08:00-17:00 作为默认可用时间。" type="info" show-icon />
        </template>

        <template v-else-if="dialogKind === 'shift'">
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="班次编码" required><a-input v-model:value="form.shift_code" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="班次名称" required><a-input v-model:value="form.shift_name" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="开始时间" required><a-time-picker v-model:value="form.start_time" value-format="HH:mm:ss" class="w-full" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="结束时间" required><a-time-picker v-model:value="form.end_time" value-format="HH:mm:ss" class="w-full" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="休息分钟"><a-input-number v-model:value="form.break_minutes" :min="0" class="w-full" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="跨自然日"><a-switch v-model:checked="form.spans_next_day" /></a-form-item></a-col>
            <a-col v-if="editingShift" :span="8"><a-form-item label="状态"><a-select v-model:value="form.status" :options="[{ label: '启用', value: 'ACTIVE' }, { label: '停用', value: 'DISABLED' }]" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="备注"><a-textarea v-model:value="form.remark" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'calendar'">
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="日历编码" required><a-input v-model:value="form.calendar_code" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="日历名称" required><a-input v-model:value="form.calendar_name" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="工作日"><a-select v-model:value="form.weekday_mask" :options="[{ label: '周一至周五', value: '1,2,3,4,5' }, { label: '周一至周六', value: '1,2,3,4,5,6' }, { label: '每天', value: '1,2,3,4,5,6,7' }]" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="默认班次"><a-select v-model:value="form.default_shift_id" allow-clear :options="shifts.filter((item) => item.status === 'ACTIVE').map((item) => ({ label: `${item.shift_code} · ${item.shift_name}`, value: item.id }))" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="时区"><a-input v-model:value="form.timezone_name" /></a-form-item></a-col>
            <a-col v-if="editingCalendar" :span="12"><a-form-item label="状态"><a-select v-model:value="form.status" :options="[{ label: '启用', value: 'ACTIVE' }, { label: '停用', value: 'DISABLED' }]" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="备注"><a-textarea v-model:value="form.remark" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'day'">
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="日期" required><a-date-picker v-model:value="form.work_date" value-format="YYYY-MM-DD" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="是否工作日"><a-switch v-model:checked="form.is_working_day" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="覆盖班次"><a-select v-model:value="form.shift_id" allow-clear :options="shifts.filter((item) => item.status === 'ACTIVE').map((item) => ({ label: item.shift_name, value: item.id }))" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="产能系数"><a-input-number v-model:value="form.capacity_factor" :min="0" :max="10" :step="0.1" class="w-full" /></a-form-item></a-col>
          </a-row>
          <a-form-item label="备注"><a-textarea v-model:value="form.remark" /></a-form-item>
        </template>

        <template v-else-if="dialogKind === 'assignment'">
          <a-form-item label="工作中心" required><a-select v-model:value="form.work_center_id" show-search :options="workCenters.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item>
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="生效日期" required><a-date-picker v-model:value="form.effective_from" value-format="YYYY-MM-DD" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="失效日期"><a-date-picker v-model:value="form.effective_to" value-format="YYYY-MM-DD" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="产能系数"><a-input-number v-model:value="form.capacity_factor" :min="0.01" :max="10" :step="0.1" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="优先级"><a-input-number v-model:value="form.priority" class="w-full" /></a-form-item></a-col>
          </a-row>
        </template>

        <template v-else>
          <a-descriptions class="mb-3" :column="1" bordered size="small">
            <a-descriptions-item label="工单">{{ selectedOperation?.work_order_no_snapshot }}</a-descriptions-item>
            <a-descriptions-item label="工序">{{ selectedOperation?.operation_name_snapshot }}</a-descriptions-item>
            <a-descriptions-item label="工作中心">{{ selectedOperation?.work_center_name_snapshot }}</a-descriptions-item>
            <a-descriptions-item label="计划时间">{{ formatDateTime(selectedOperation?.planned_start_at) }} → {{ formatDateTime(selectedOperation?.planned_end_at) }}</a-descriptions-item>
          </a-descriptions>
          <a-form-item label="指派人员"><a-select v-model:value="form.assigned_user_id" allow-clear show-search :options="users.map((item) => ({ label: `${item.username} · ${item.nickname}`, value: item.id }))" /></a-form-item>
          <a-row :gutter="16">
            <a-col :span="12"><a-form-item label="班组"><a-input v-model:value="form.assigned_team" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="工位编码"><a-input v-model:value="form.workstation_code" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="派工数量"><a-input-number v-model:value="form.dispatch_quantity" :min="0.000001" class="w-full" /></a-form-item></a-col>
            <a-col :span="12"><a-form-item label="优先级"><a-input-number v-model:value="form.priority" class="w-full" /></a-form-item></a-col>
          </a-row>
          <a-alert message="人员、班组、工位至少填写一项。" type="info" show-icon />
        </template>
      </a-form>
    </a-modal>
  </Page>
</template>

<style scoped>
.gantt-shell {
  overflow: auto;
  border: 1px solid hsl(var(--border));
  border-radius: 8px;
  background: linear-gradient(90deg, rgb(148 163 184 / 8%) 1px, transparent 1px);
  background-size: 10% 100%;
}

.gantt-axis {
  display: grid;
  grid-template-columns: 240px 1fr 240px;
  align-items: center;
  min-width: 980px;
  padding: 9px 12px;
  color: #64748b;
  text-align: center;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.gantt-axis span:first-child { text-align: left; }
.gantt-axis span:last-child { text-align: right; }

.gantt-row {
  display: grid;
  grid-template-columns: 180px minmax(800px, 1fr);
  min-height: 52px;
  border-bottom: 1px solid #eef2f7;
}

.gantt-label {
  display: flex;
  align-items: center;
  padding: 0 12px;
  overflow: hidden;
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #fff;
  border-right: 1px solid #eef2f7;
}

.gantt-track { position: relative; margin: 8px 0; }

.gantt-bar {
  position: absolute;
  top: 0;
  height: 34px;
  padding: 7px 8px;
  overflow: hidden;
  font-size: 12px;
  color: #fff;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  background: linear-gradient(135deg, #1677ff, #69b1ff);
  border-radius: 5px;
  box-shadow: 0 2px 5px rgb(22 119 255 / 25%);
}

.gantt-bar.published { background: linear-gradient(135deg, #722ed1, #b37feb); }
.gantt-bar.overdue { background: linear-gradient(135deg, #cf1322, #ff7875); }
</style>
