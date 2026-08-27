<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  CycleAnalysis,
  DowntimePareto,
  EquipmentReliability,
  MetricGrain,
  PerformanceDashboard,
  PerformanceQuery,
  PerformanceSnapshot,
  PerformanceTarget,
  PerformanceTrendPoint,
  WorkCenterOption,
  WorkCenterPerformance,
} from '../api';

import { computed, nextTick, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';
import { message } from 'antdv-next';
import dayjs from 'dayjs';

import {
  getCycleAnalysisApi,
  getDowntimeParetoApi,
  getEquipmentReliabilityApi,
  getPerformanceDashboardApi,
  getPerformanceSnapshotsApi,
  getPerformanceTargetsApi,
  getPerformanceTrendApi,
  getPerformanceWorkCenterOptionsApi,
  getWorkCenterPerformanceApi,
  rebuildPerformanceSnapshotsApi,
  updatePerformanceTargetApi,
} from '../api';

type DialogKind = 'rebuild' | 'target';

const emptyDashboard: PerformanceDashboard = {
  actual_run_minutes: 0,
  availability_rate: 0,
  calendar_minutes: 0,
  failure_count: 0,
  good_quantity: 0,
  ideal_run_minutes: 0,
  idle_capacity_minutes: 0,
  oee_rate: 0,
  on_target_center_count: 0,
  operating_minutes: 0,
  performance_rate: 0,
  period_end: '',
  period_start: '',
  planned_downtime_minutes: 0,
  planned_production_minutes: 0,
  quality_rate: 0,
  scrap_quantity: 0,
  source_execution_count: 0,
  target_oee_rate: 85,
  throughput_per_hour: 0,
  total_quantity: 0,
  unplanned_downtime_minutes: 0,
  utilization_rate: 0,
  work_center_count: 0,
};

const loading = ref(false);
const saving = ref(false);
const activeTab = ref('overview');
const dateRange = ref<[string, string]>([
  dayjs().subtract(29, 'day').format('YYYY-MM-DD'),
  dayjs().format('YYYY-MM-DD'),
]);
const snapshotRange = ref<[string, string]>([...dateRange.value]);
const selectedCenterId = ref<number>();
const grain = ref<MetricGrain>('DAY');
const dashboard = ref<PerformanceDashboard>({ ...emptyDashboard });
const workCenters = ref<WorkCenterPerformance[]>([]);
const trend = ref<PerformanceTrendPoint[]>([]);
const reliability = ref<EquipmentReliability[]>([]);
const cycles = ref<CycleAnalysis[]>([]);
const pareto = ref<DowntimePareto[]>([]);
const targets = ref<PerformanceTarget[]>([]);
const snapshots = ref<PerformanceSnapshot[]>([]);
const centerOptions = ref<WorkCenterOption[]>([]);
const dialogVisible = ref(false);
const dialogKind = ref<DialogKind>('target');
const dialogForm = ref<Record<string, any>>({});
const editingTarget = ref<PerformanceTarget>();

const trendChartRef = ref<EchartsUIType>();
const capacityChartRef = ref<EchartsUIType>();
const reliabilityChartRef = ref<EchartsUIType>();
const paretoChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTrend } = useEcharts(trendChartRef);
const { renderEcharts: renderCapacity } = useEcharts(capacityChartRef);
const { renderEcharts: renderReliability } = useEcharts(reliabilityChartRef);
const { renderEcharts: renderPareto } = useEcharts(paretoChartRef);

const queryParams = computed<PerformanceQuery>(() => {
  const params: PerformanceQuery = {
    end_date: dateRange.value[1],
    start_date: dateRange.value[0],
  };
  if (selectedCenterId.value) params.work_center_id = selectedCenterId.value;
  return params;
});

const activeCenterOptions = computed(() =>
  centerOptions.value
    .filter((item) => item.status === 'ACTIVE' && item.production_enabled)
    .map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id })),
);

const dialogTitle = computed(() =>
  dialogKind.value === 'target'
    ? `配置绩效目标${editingTarget.value ? ` · ${editingTarget.value.work_center_name}` : ''}`
    : '重建制造绩效日快照',
);

const targetGap = computed(
  () => Number(dashboard.value.oee_rate) - Number(dashboard.value.target_oee_rate),
);

function numberValue(value: null | number | string | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatNumber(value: null | number | string | undefined, precision = 1) {
  return numberValue(value).toLocaleString('zh-CN', {
    maximumFractionDigits: precision,
    minimumFractionDigits: precision,
  });
}

function formatOptional(value: null | number | string | undefined, precision = 1) {
  return value === undefined || value === null ? '-' : formatNumber(value, precision);
}

function formatDateTime(value?: string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-';
}

function metricColor(value: null | number | string | undefined, target: number | string = 85) {
  const current = numberValue(value);
  const expected = numberValue(target);
  if (current >= expected) return '#16a34a';
  if (current >= expected * 0.85) return '#fa8c16';
  return '#ef4444';
}

function renderTrendChart() {
  renderTrend({
    color: ['#2563eb', '#16a34a', '#f59e0b', '#8b5cf6'],
    grid: { bottom: 28, containLabel: true, left: 18, right: 18, top: 48 },
    legend: { data: ['OEE', '时间开动率', '性能开动率', '质量率'], top: 4 },
    series: [
      {
        areaStyle: { opacity: 0.08 },
        data: trend.value.map((item) => numberValue(item.oee_rate)),
        name: 'OEE',
        smooth: true,
        type: 'line',
      },
      {
        data: trend.value.map((item) => numberValue(item.availability_rate)),
        name: '时间开动率',
        smooth: true,
        type: 'line',
      },
      {
        data: trend.value.map((item) => numberValue(item.performance_rate)),
        name: '性能开动率',
        smooth: true,
        type: 'line',
      },
      {
        data: trend.value.map((item) => numberValue(item.quality_rate)),
        name: '质量率',
        smooth: true,
        type: 'line',
      },
    ],
    tooltip: { trigger: 'axis', valueFormatter: (value: unknown) => `${formatNumber(Number(value), 2)}%` },
    xAxis: {
      boundaryGap: false,
      data: trend.value.map((item) =>
        item.period_start === item.period_end
          ? item.period_start.slice(5)
          : `${item.period_start.slice(5)}~${item.period_end.slice(5)}`,
      ),
      type: 'category',
    },
    yAxis: { max: 100, min: 0, name: '%', type: 'value' },
  });
}

function renderCapacityChart() {
  renderCapacity({
    color: ['#0ea5e9', '#22c55e', '#cbd5e1'],
    grid: { bottom: 40, containLabel: true, left: 18, right: 18, top: 48 },
    legend: { data: ['实绩运行', '闲置产能', '计划生产'], top: 4 },
    series: [
      {
        data: workCenters.value.map((item) => numberValue(item.actual_run_minutes)),
        name: '实绩运行',
        stack: 'capacity',
        type: 'bar',
      },
      {
        data: workCenters.value.map((item) => numberValue(item.idle_capacity_minutes)),
        name: '闲置产能',
        stack: 'capacity',
        type: 'bar',
      },
      {
        data: workCenters.value.map((item) => numberValue(item.planned_production_minutes)),
        name: '计划生产',
        symbol: 'circle',
        type: 'line',
      },
    ],
    tooltip: { trigger: 'axis', valueFormatter: (value: unknown) => `${formatNumber(Number(value), 1)} 分钟` },
    xAxis: {
      axisLabel: { interval: 0, rotate: workCenters.value.length > 8 ? 25 : 0 },
      data: workCenters.value.map((item) => item.work_center_code),
      type: 'category',
    },
    yAxis: { name: '产能分钟', type: 'value' },
  });
}

function renderReliabilityChart() {
  renderReliability({
    color: ['#ef4444', '#f59e0b'],
    grid: { bottom: 45, containLabel: true, left: 18, right: 48, top: 48 },
    legend: { data: ['故障次数', '非计划停机'], top: 4 },
    series: [
      {
        data: reliability.value.map((item) => item.failure_count),
        name: '故障次数',
        type: 'bar',
        yAxisIndex: 0,
      },
      {
        data: reliability.value.map((item) => numberValue(item.unplanned_downtime_minutes)),
        name: '非计划停机',
        type: 'line',
        yAxisIndex: 1,
      },
    ],
    tooltip: { trigger: 'axis' },
    xAxis: {
      axisLabel: { interval: 0, rotate: reliability.value.length > 8 ? 25 : 0 },
      data: reliability.value.map((item) => item.equipment_code),
      type: 'category',
    },
    yAxis: [
      { minInterval: 1, name: '次', type: 'value' },
      { name: '分钟', type: 'value' },
    ],
  });
}

function renderParetoChart() {
  renderPareto({
    color: ['#6366f1', '#ef4444'],
    grid: { bottom: 60, containLabel: true, left: 18, right: 48, top: 48 },
    legend: { data: ['停机分钟', '累计占比'], top: 4 },
    series: [
      {
        data: pareto.value.map((item) => numberValue(item.downtime_minutes)),
        name: '停机分钟',
        type: 'bar',
      },
      {
        data: pareto.value.map((item) => numberValue(item.cumulative_percentage)),
        name: '累计占比',
        type: 'line',
        yAxisIndex: 1,
      },
    ],
    tooltip: { trigger: 'axis' },
    xAxis: {
      axisLabel: { interval: 0, rotate: 24 },
      data: pareto.value.map((item) => item.reason),
      type: 'category',
    },
    yAxis: [
      { name: '分钟', type: 'value' },
      { max: 100, min: 0, name: '%', type: 'value' },
    ],
  });
}

async function renderVisibleCharts() {
  await nextTick();
  if (activeTab.value === 'overview') renderTrendChart();
  if (activeTab.value === 'centers') renderCapacityChart();
  if (activeTab.value === 'reliability') {
    renderReliabilityChart();
    renderParetoChart();
  }
}

async function loadAll() {
  loading.value = true;
  try {
    const params = queryParams.value;
    const [
      dashboardRow,
      centerRows,
      trendRows,
      reliabilityRows,
      cycleRows,
      paretoRows,
      targetRows,
      snapshotRows,
      optionRows,
    ] = await Promise.all([
      getPerformanceDashboardApi(params),
      getWorkCenterPerformanceApi(params),
      getPerformanceTrendApi({ ...params, grain: grain.value }),
      getEquipmentReliabilityApi(params),
      getCycleAnalysisApi(params),
      getDowntimeParetoApi({ ...params, top_n: 10 }),
      getPerformanceTargetsApi(),
      getPerformanceSnapshotsApi(params),
      getPerformanceWorkCenterOptionsApi(),
    ]);
    dashboard.value = dashboardRow;
    workCenters.value = centerRows;
    trend.value = trendRows;
    reliability.value = reliabilityRows;
    cycles.value = cycleRows;
    pareto.value = paretoRows;
    targets.value = targetRows;
    snapshots.value = snapshotRows;
    centerOptions.value = optionRows;
  } finally {
    loading.value = false;
  }
  await renderVisibleCharts();
}

function openTarget(record: PerformanceTarget) {
  dialogKind.value = 'target';
  editingTarget.value = record;
  dialogForm.value = {
    availability_target: numberValue(record.availability_target),
    ideal_cycle_seconds:
      record.ideal_cycle_seconds == null
        ? undefined
        : numberValue(record.ideal_cycle_seconds),
    oee_target: numberValue(record.oee_target),
    performance_target: numberValue(record.performance_target),
    quality_target: numberValue(record.quality_target),
    remark: record.remark,
    status: record.status,
  };
  dialogVisible.value = true;
}

function openRebuild() {
  dialogKind.value = 'rebuild';
  editingTarget.value = undefined;
  snapshotRange.value = [...dateRange.value];
  dialogForm.value = {
    work_center_ids: selectedCenterId.value ? [selectedCenterId.value] : [],
  };
  dialogVisible.value = true;
}

async function submitDialog() {
  saving.value = true;
  try {
    if (dialogKind.value === 'target' && editingTarget.value) {
      const data = { ...dialogForm.value };
      if (!data.ideal_cycle_seconds) data.ideal_cycle_seconds = null;
      await updatePerformanceTargetApi(editingTarget.value.work_center_id, data);
      message.success('绩效目标已保存');
    } else {
      const [startDate, endDate] = snapshotRange.value;
      if (dayjs(endDate).diff(dayjs(startDate), 'day') > 92) {
        message.warning('单次最多重建 93 天快照');
        return;
      }
      const result = await rebuildPerformanceSnapshotsApi({
        end_date: endDate,
        start_date: startDate,
        work_center_ids: dialogForm.value.work_center_ids ?? [],
      });
      message.success(
        `已重建 ${result.work_center_count} 个工作中心、${result.snapshot_count} 条日快照`,
      );
    }
    dialogVisible.value = false;
    await loadAll();
  } finally {
    saving.value = false;
  }
}

watch(activeTab, renderVisibleCharts);
onMounted(loadAll);
</script>

<template>
  <Page title="制造绩效分析" auto-content-height>
    <a-card class="mb-3" :body-style="{ padding: '14px 16px' }">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div class="text-base font-semibold">OEE · 设备可靠性 · 节拍 · 产能</div>
          <div class="mt-1 text-xs text-gray-500">
            基于 APS 工作日历、生产实绩和设备停机实时计算；日快照可重复重建。
          </div>
        </div>
        <a-space wrap>
          <a-range-picker
            v-model:value="dateRange"
            value-format="YYYY-MM-DD"
            :allow-clear="false"
          />
          <a-select
            v-model:value="selectedCenterId"
            allow-clear
            class="w-56"
            placeholder="全部工作中心"
            show-search
            :filter-option="(input: string, option: any) => option.label.toLowerCase().includes(input.toLowerCase())"
            :options="activeCenterOptions"
          />
          <a-select
            v-model:value="grain"
            class="w-28"
            :options="[
              { label: '按日', value: 'DAY' },
              { label: '按周', value: 'WEEK' },
              { label: '按月', value: 'MONTH' },
            ]"
          />
          <a-button @click="openRebuild">重建快照</a-button>
          <a-button type="primary" :loading="loading" @click="loadAll">查询分析</a-button>
        </a-space>
      </div>
    </a-card>

    <a-alert
      v-if="!loading && dashboard.source_execution_count === 0"
      class="mb-3"
      message="当前范围没有已完成的生产执行，OEE 的性能率、质量率和节拍会显示为 0；请检查报工状态、工艺标准和日期范围。"
      show-icon
      type="warning"
    />

    <a-spin :spinning="loading">
      <a-tabs v-model:active-key="activeTab">
        <a-tab-pane key="overview" tab="绩效总览">
          <a-row :gutter="12">
            <a-col :span="6">
              <a-card class="metric-card oee-card">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="metric-label">综合设备效率 OEE</div>
                    <div class="metric-value" :style="{ color: metricColor(dashboard.oee_rate, dashboard.target_oee_rate) }">
                      {{ formatNumber(dashboard.oee_rate, 2) }}<span>%</span>
                    </div>
                    <div class="metric-note">
                      目标 {{ formatNumber(dashboard.target_oee_rate, 1) }}%，
                      <span :class="targetGap >= 0 ? 'text-green-600' : 'text-red-500'">
                        {{ targetGap >= 0 ? '高' : '低' }} {{ formatNumber(Math.abs(targetGap), 2) }} 个百分点
                      </span>
                    </div>
                  </div>
                  <a-progress
                    type="dashboard"
                    :width="88"
                    :percent="Math.min(100, numberValue(dashboard.oee_rate))"
                    :stroke-color="metricColor(dashboard.oee_rate, dashboard.target_oee_rate)"
                    :show-info="false"
                  />
                </div>
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card class="metric-card">
                <div class="metric-label">时间开动率 A</div>
                <div class="metric-value" :style="{ color: metricColor(dashboard.availability_rate, 90) }">
                  {{ formatNumber(dashboard.availability_rate, 2) }}<span>%</span>
                </div>
                <a-progress :percent="Math.min(100, numberValue(dashboard.availability_rate))" :show-info="false" />
                <div class="metric-note">运行 {{ formatNumber(dashboard.operating_minutes) }} / 计划 {{ formatNumber(dashboard.planned_production_minutes) }} 分钟</div>
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card class="metric-card">
                <div class="metric-label">性能开动率 P</div>
                <div class="metric-value" :style="{ color: metricColor(dashboard.performance_rate, 95) }">
                  {{ formatNumber(dashboard.performance_rate, 2) }}<span>%</span>
                </div>
                <a-progress :percent="Math.min(100, numberValue(dashboard.performance_rate))" :show-info="false" stroke-color="#f59e0b" />
                <div class="metric-note">理论 {{ formatNumber(dashboard.ideal_run_minutes) }} / 运行 {{ formatNumber(dashboard.operating_minutes) }} 分钟</div>
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card class="metric-card">
                <div class="metric-label">质量率 Q</div>
                <div class="metric-value" :style="{ color: metricColor(dashboard.quality_rate, 99) }">
                  {{ formatNumber(dashboard.quality_rate, 2) }}<span>%</span>
                </div>
                <a-progress :percent="Math.min(100, numberValue(dashboard.quality_rate))" :show-info="false" stroke-color="#8b5cf6" />
                <div class="metric-note">良品 {{ formatNumber(dashboard.good_quantity, 2) }} / 总数 {{ formatNumber(dashboard.total_quantity, 2) }}</div>
              </a-card>
            </a-col>
          </a-row>

          <a-row :gutter="12" class="mt-3">
            <a-col :span="4"><a-card><a-statistic title="MTBF（分钟）" :value="numberValue(dashboard.mtbf_minutes)" :precision="1" /></a-card></a-col>
            <a-col :span="4"><a-card><a-statistic title="MTTR（分钟）" :value="numberValue(dashboard.mttr_minutes)" :precision="1" /></a-card></a-col>
            <a-col :span="4"><a-card><a-statistic title="实际节拍（秒/件）" :value="numberValue(dashboard.actual_cycle_seconds)" :precision="2" /></a-card></a-col>
            <a-col :span="4"><a-card><a-statistic title="理想节拍（秒/件）" :value="numberValue(dashboard.ideal_cycle_seconds)" :precision="2" /></a-card></a-col>
            <a-col :span="4"><a-card><a-statistic title="良品小时产出" :value="numberValue(dashboard.throughput_per_hour)" :precision="2" /></a-card></a-col>
            <a-col :span="4"><a-card><a-statistic title="产能利用率" :value="numberValue(dashboard.utilization_rate)" :precision="2" suffix="%" /></a-card></a-col>
          </a-row>

          <a-row :gutter="12" class="mt-3">
            <a-col :span="6"><a-card><a-statistic title="非计划停机（分钟）" :value="numberValue(dashboard.unplanned_downtime_minutes)" :precision="1" :value-style="{ color: '#ef4444' }" /></a-card></a-col>
            <a-col :span="6"><a-card><a-statistic title="计划停机（分钟）" :value="numberValue(dashboard.planned_downtime_minutes)" :precision="1" /></a-card></a-col>
            <a-col :span="6"><a-card><a-statistic title="故障次数" :value="dashboard.failure_count" /></a-card></a-col>
            <a-col :span="6"><a-card><a-statistic title="达标工作中心" :value="dashboard.on_target_center_count" :suffix="`/ ${dashboard.work_center_count}`" /></a-card></a-col>
          </a-row>

          <a-card class="mt-3" title="OEE 与 A/P/Q 趋势">
            <EchartsUI ref="trendChartRef" height="360px" />
          </a-card>
        </a-tab-pane>

        <a-tab-pane key="centers" tab="工作中心与产能">
          <a-card title="工作中心产能构成">
            <EchartsUI ref="capacityChartRef" height="340px" />
          </a-card>
          <a-table
            class="mt-3"
            :data-source="workCenters"
            row-key="work_center_id"
            :pagination="{ pageSize: 20 }"
            :scroll="{ x: 1850 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'center'">
                <div class="font-medium">{{ record.work_center_code }}</div>
                <div class="text-xs text-gray-500">{{ record.work_center_name }} · {{ record.parallel_capacity }} 通道</div>
              </template>
              <template v-else-if="column.key === 'oee'">
                <a-tag :color="record.oee_on_target ? 'green' : 'red'">{{ formatNumber(record.oee_rate, 2) }}%</a-tag>
                <div class="mt-1 text-xs text-gray-500">目标 {{ formatNumber(record.oee_target, 1) }}%</div>
              </template>
              <template v-else-if="column.key === 'rates'">
                A {{ formatNumber(record.availability_rate, 1) }}% · P {{ formatNumber(record.performance_rate, 1) }}% · Q {{ formatNumber(record.quality_rate, 1) }}%
              </template>
              <template v-else-if="column.key === 'capacity'">
                <div>计划 {{ formatNumber(record.planned_production_minutes) }}</div>
                <div class="text-xs text-gray-500">运行 {{ formatNumber(record.operating_minutes) }} / 实绩 {{ formatNumber(record.actual_run_minutes) }}</div>
              </template>
              <template v-else-if="column.key === 'downtime'">
                <span class="text-red-500">非计划 {{ formatNumber(record.unplanned_downtime_minutes) }}</span>
                <div class="text-xs text-gray-500">计划 {{ formatNumber(record.planned_downtime_minutes) }}</div>
              </template>
              <template v-else-if="column.key === 'quantity'">
                <div>良品 {{ formatNumber(record.good_quantity, 2) }}</div>
                <div class="text-xs text-gray-500">废品 {{ formatNumber(record.scrap_quantity, 2) }}</div>
              </template>
              <template v-else-if="column.key === 'cycle'">
                <div>实际 {{ formatOptional(record.actual_cycle_seconds, 2) }} 秒</div>
                <div class="text-xs text-gray-500">理想 {{ formatOptional(record.ideal_cycle_seconds, 2) }} 秒</div>
              </template>
              <template v-else-if="column.key === 'reliability'">
                <div>{{ record.failure_count }} 次 · MTBF {{ formatOptional(record.mtbf_minutes) }}</div>
                <div class="text-xs text-gray-500">MTTR {{ formatOptional(record.mttr_minutes) }} 分钟</div>
              </template>
            </template>
            <a-table-column title="工作中心" key="center" fixed="left" width="190" />
            <a-table-column title="OEE" key="oee" width="120" />
            <a-table-column title="A / P / Q" key="rates" width="260" />
            <a-table-column title="产能分钟" key="capacity" width="220" />
            <a-table-column title="停机分钟" key="downtime" width="170" />
            <a-table-column title="数量" key="quantity" width="160" />
            <a-table-column title="节拍" key="cycle" width="180" />
            <a-table-column title="小时产出" data-index="throughput_per_hour" width="110" />
            <a-table-column title="利用率(%)" data-index="utilization_rate" width="110" />
            <a-table-column title="可靠性" key="reliability" width="220" />
            <a-table-column title="执行记录" data-index="source_execution_count" width="100" fixed="right" />
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="reliability" tab="设备可靠性与 Pareto">
          <div class="grid grid-cols-2 gap-3">
            <a-card title="设备故障与非计划停机">
              <EchartsUI ref="reliabilityChartRef" height="340px" />
            </a-card>
            <a-card title="非计划停机原因 Pareto">
              <EchartsUI ref="paretoChartRef" height="340px" />
            </a-card>
          </div>
          <a-table class="mt-3" :data-source="reliability" row-key="equipment_id" :pagination="{ pageSize: 20 }" :scroll="{ x: 1300 }">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'equipment'">
                <div class="font-medium">{{ record.equipment_code }}</div>
                <div class="text-xs text-gray-500">{{ record.equipment_name }}</div>
              </template>
              <template v-else-if="column.key === 'availability'"><a-progress :percent="Math.min(100, numberValue(record.availability_rate))" size="small" /></template>
              <template v-else-if="column.key === 'last'">{{ formatDateTime(record.last_failure_at) }}</template>
            </template>
            <a-table-column title="设备" key="equipment" fixed="left" width="200" />
            <a-table-column title="故障次数" data-index="failure_count" width="100" />
            <a-table-column title="计划停机(分)" data-index="planned_downtime_minutes" width="130" />
            <a-table-column title="非计划停机(分)" data-index="unplanned_downtime_minutes" width="145" />
            <a-table-column title="总停机(分)" data-index="total_downtime_minutes" width="120" />
            <a-table-column title="设备可用率" key="availability" width="210" />
            <a-table-column title="MTBF(分)" data-index="mtbf_minutes" width="120" />
            <a-table-column title="MTTR(分)" data-index="mttr_minutes" width="120" />
            <a-table-column title="最近故障" key="last" width="170" fixed="right" />
          </a-table>
          <a-table class="mt-3" :data-source="pareto" row-key="rank" :pagination="false">
            <a-table-column title="排名" data-index="rank" width="80" />
            <a-table-column title="停机原因" data-index="reason" />
            <a-table-column title="事件数" data-index="event_count" width="100" />
            <a-table-column title="停机分钟" data-index="downtime_minutes" width="130" />
            <a-table-column title="占比(%)" data-index="percentage" width="120" />
            <a-table-column title="累计占比(%)" data-index="cumulative_percentage" width="130" />
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="cycle" tab="工序节拍分析">
          <a-alert class="mb-3" message="理想节拍优先取工艺路线标准；工艺标准缺失时使用工作中心备用理想节拍。" show-icon type="info" />
          <a-table
            :data-source="cycles"
            :pagination="{ pageSize: 20 }"
            :scroll="{ x: 1600 }"
            :row-key="(record: CycleAnalysis) => `${record.work_center_id}-${record.operation_id}-${record.product_code}`"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'center'">{{ record.work_center_code }} · {{ record.work_center_name }}</template>
              <template v-else-if="column.key === 'operation'">{{ record.operation_code }} · {{ record.operation_name }}</template>
              <template v-else-if="column.key === 'product'">{{ record.product_code }} · {{ record.product_name }}</template>
              <template v-else-if="column.key === 'quantity'">{{ formatNumber(record.good_quantity, 2) }} 良 / {{ formatNumber(record.scrap_quantity, 2) }} 废</template>
              <template v-else-if="column.key === 'cycle'">
                <div>实际 {{ formatOptional(record.actual_cycle_seconds, 3) }} 秒/件</div>
                <div class="text-xs text-gray-500">理想 {{ formatOptional(record.ideal_cycle_seconds, 3) }} 秒/件</div>
              </template>
              <template v-else-if="column.key === 'efficiency'"><a-tag :color="numberValue(record.cycle_efficiency_rate) >= 95 ? 'green' : 'orange'">{{ formatNumber(record.cycle_efficiency_rate, 2) }}%</a-tag></template>
            </template>
            <a-table-column title="工作中心" key="center" width="220" fixed="left" />
            <a-table-column title="工序" key="operation" width="220" />
            <a-table-column title="产品" key="product" width="240" />
            <a-table-column title="执行数" data-index="execution_count" width="90" />
            <a-table-column title="完成数量" key="quantity" width="190" />
            <a-table-column title="实绩分钟" data-index="actual_run_minutes" width="110" />
            <a-table-column title="理论分钟" data-index="ideal_run_minutes" width="110" />
            <a-table-column title="节拍" key="cycle" width="220" />
            <a-table-column title="节拍效率" key="efficiency" width="120" fixed="right" />
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="configuration" tab="目标与日快照">
          <a-card title="工作中心绩效目标">
            <template #extra><a-button type="primary" @click="openRebuild">重建日快照</a-button></template>
            <a-table :data-source="targets" row-key="work_center_id" :pagination="{ pageSize: 20 }">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'center'">{{ record.work_center_code }} · {{ record.work_center_name }}</template>
                <template v-else-if="column.key === 'status'"><a-tag :color="record.status === 'ACTIVE' ? 'green' : 'default'">{{ record.status === 'ACTIVE' ? '启用' : '停用' }}</a-tag></template>
                <template v-else-if="column.key === 'configured'"><a-tag :color="record.configured ? 'blue' : 'default'">{{ record.configured ? '已配置' : '系统默认' }}</a-tag></template>
                <template v-else-if="column.key === 'action'"><a-button type="link" @click="openTarget(record)">配置</a-button></template>
              </template>
              <a-table-column title="工作中心" key="center" />
              <a-table-column title="A 目标(%)" data-index="availability_target" width="110" />
              <a-table-column title="P 目标(%)" data-index="performance_target" width="110" />
              <a-table-column title="Q 目标(%)" data-index="quality_target" width="110" />
              <a-table-column title="OEE 目标(%)" data-index="oee_target" width="130" />
              <a-table-column title="备用节拍(秒)" data-index="ideal_cycle_seconds" width="130" />
              <a-table-column title="状态" key="status" width="90" />
              <a-table-column title="来源" key="configured" width="100" />
              <a-table-column title="操作" key="action" width="80" />
            </a-table>
          </a-card>

          <a-card class="mt-3" title="日绩效快照">
            <a-table :data-source="snapshots" row-key="id" :pagination="{ pageSize: 20 }" :scroll="{ x: 1500 }">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'center'">{{ record.work_center_code }} · {{ record.work_center_name }}</template>
                <template v-else-if="column.key === 'oee'"><a-tag :color="numberValue(record.oee_rate) >= 85 ? 'green' : 'orange'">{{ formatNumber(record.oee_rate, 2) }}%</a-tag></template>
                <template v-else-if="column.key === 'rates'">{{ formatNumber(record.availability_rate, 1) }} / {{ formatNumber(record.performance_rate, 1) }} / {{ formatNumber(record.quality_rate, 1) }}</template>
                <template v-else-if="column.key === 'calculated'">{{ formatDateTime(record.calculated_at) }}</template>
              </template>
              <a-table-column title="日期" data-index="metric_date" width="120" fixed="left" />
              <a-table-column title="工作中心" key="center" width="220" fixed="left" />
              <a-table-column title="OEE" key="oee" width="100" />
              <a-table-column title="A / P / Q(%)" key="rates" width="210" />
              <a-table-column title="运行分钟" data-index="operating_minutes" width="110" />
              <a-table-column title="非计划停机" data-index="unplanned_downtime_minutes" width="120" />
              <a-table-column title="良品" data-index="good_quantity" width="110" />
              <a-table-column title="废品" data-index="scrap_quantity" width="110" />
              <a-table-column title="实际节拍" data-index="actual_cycle_seconds" width="110" />
              <a-table-column title="故障数" data-index="failure_count" width="90" />
              <a-table-column title="MTBF" data-index="mtbf_minutes" width="110" />
              <a-table-column title="MTTR" data-index="mttr_minutes" width="110" />
              <a-table-column title="计算时间" key="calculated" width="170" fixed="right" />
            </a-table>
          </a-card>
        </a-tab-pane>
      </a-tabs>
    </a-spin>

    <a-modal v-model:open="dialogVisible" :title="dialogTitle" :confirm-loading="saving" width="760px" @ok="submitDialog">
      <a-form v-if="dialogKind === 'target'" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item label="时间开动率 A 目标(%)"><a-input-number v-model:value="dialogForm.availability_target" class="w-full" :min="0" :max="100" :precision="2" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="性能开动率 P 目标(%)"><a-input-number v-model:value="dialogForm.performance_target" class="w-full" :min="0" :max="100" :precision="2" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="质量率 Q 目标(%)"><a-input-number v-model:value="dialogForm.quality_target" class="w-full" :min="0" :max="100" :precision="2" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="OEE 目标(%)"><a-input-number v-model:value="dialogForm.oee_target" class="w-full" :min="0" :max="100" :precision="2" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="备用理想节拍(秒/件)"><a-input-number v-model:value="dialogForm.ideal_cycle_seconds" class="w-full" :min="0.000001" :precision="6" placeholder="工艺标准缺失时使用" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="状态"><a-select v-model:value="dialogForm.status" :options="[{ label: '启用', value: 'ACTIVE' }, { label: '停用', value: 'DISABLED' }]" /></a-form-item></a-col>
        </a-row>
        <a-form-item label="备注"><a-textarea v-model:value="dialogForm.remark" :rows="3" /></a-form-item>
      </a-form>
      <a-form v-else layout="vertical">
        <a-alert class="mb-3" message="日快照用于长期趋势和经营报表；同一天同一工作中心会更新原记录。单次最多 93 天。" show-icon type="info" />
        <a-form-item label="快照日期范围" required>
          <a-range-picker v-model:value="snapshotRange" value-format="YYYY-MM-DD" :allow-clear="false" class="w-full" />
        </a-form-item>
        <a-form-item label="工作中心（留空表示全部）">
          <a-select v-model:value="dialogForm.work_center_ids" mode="multiple" allow-clear :options="activeCenterOptions" placeholder="全部工作中心" />
        </a-form-item>
      </a-form>
    </a-modal>
  </Page>
</template>

<style scoped>
.metric-card {
  min-height: 176px;
  overflow: hidden;
  position: relative;
}

.oee-card::after {
  background: radial-gradient(circle, rgb(37 99 235 / 12%) 0%, transparent 68%);
  content: '';
  height: 190px;
  pointer-events: none;
  position: absolute;
  right: -55px;
  top: -70px;
  width: 190px;
}

.metric-label {
  color: rgb(107 114 128);
  font-size: 13px;
  font-weight: 500;
}

.metric-value {
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1.35;
  margin: 10px 0;
}

.metric-value span {
  font-size: 16px;
  font-weight: 500;
  margin-left: 2px;
}

.metric-note {
  color: rgb(107 114 128);
  font-size: 12px;
  margin-top: 8px;
}
</style>
