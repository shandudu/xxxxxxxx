<script lang="ts" setup>
import { onMounted, reactive, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';
import { getConfigurableTip } from '#/utils/dict';

import type { MaterialOption } from '../../material/api';
import type { WorkOrder } from '../../production/api';
import type { EquipmentOption, MoldCavity, MoldDashboard, MoldItem, MoldMaintenance, MoldMount } from '../api';
import { getMaterialOptionsApi } from '../../material/api';
import { getWorkOrdersApi } from '../../production/api';
import {
  completeMoldMaintenanceApi, createMoldApi, createMoldMaintenanceApi, getEquipmentOptionsApi,
  getMoldCavitiesApi, getMoldDashboardApi, getMoldMaintenanceApi, getMoldMountsApi, getMoldsApi,
  mountMoldApi, recordMoldQualityApi, startMoldMaintenanceApi, unmountMoldApi, updateMoldCavityApi,
} from '../api';

const loading = ref(false);
const tip = (key: string) =>
  getConfigurableTip(`equipment.mold.${key}`, `equipment.moldTips.${key}`);
const dashboard = ref<MoldDashboard>();
const molds = ref<MoldItem[]>([]);
const cavities = ref<MoldCavity[]>([]);
const mounts = ref<MoldMount[]>([]);
const maintenance = ref<MoldMaintenance[]>([]);
const tools = ref<EquipmentOption[]>([]);
const machines = ref<EquipmentOption[]>([]);
const materials = ref<MaterialOption[]>([]);
const workOrders = ref<WorkOrder[]>([]);
const selectedMoldId = ref<number>();
const form = reactive({ mold_code: '', mold_name: '', tool_equipment_id: undefined as number | undefined, product_material_id: undefined as number | undefined, mold_type: 'INJECTION', cavity_count: 2, designed_life_shots: 100000, maintenance_interval_shots: 10000, acquisition_cost: 0 });
const mountForm = reactive({ mold_id: undefined as number | undefined, equipment_id: undefined as number | undefined, work_order_id: undefined as number | undefined });

const option = (rows: Array<{ id: number; code: string; name: string }>) => rows.map((row) => ({ label: `${row.code} · ${row.name}`, value: row.id }));
const moldOption = () => molds.value.map((row) => ({ label: `${row.mold_code} · ${row.mold_name}`, value: row.id }));
const workOrderOption = () => workOrders.value.filter((row) => ['RELEASED', 'IN_PROGRESS'].includes(row.status)).map((row) => ({ label: `${row.work_order_no} · ${row.product_name_snapshot}`, value: row.id }));
function color(status: string) { return ['AVAILABLE', 'COMPLETED', 'ACTIVE'].includes(status) ? 'green' : ['MOUNTED', 'PLANNED', 'IN_PROGRESS', 'MAINTENANCE'].includes(status) ? 'orange' : 'red'; }
function lifePercent(row: MoldItem) { return Math.min(100, Number((row.current_shots * 100 / row.designed_life_shots).toFixed(2))); }

async function load() {
  loading.value = true;
  try {
    [dashboard.value, molds.value, mounts.value, maintenance.value, tools.value, machines.value, materials.value, workOrders.value] = await Promise.all([
      getMoldDashboardApi(), getMoldsApi(), getMoldMountsApi(), getMoldMaintenanceApi(),
      getEquipmentOptionsApi({ equipment_type: 'TOOL' }), getEquipmentOptionsApi({ equipment_type: 'PRODUCTION', production_enabled: true }),
      getMaterialOptionsApi(), getWorkOrdersApi(),
    ]);
    if (selectedMoldId.value) cavities.value = await getMoldCavitiesApi(selectedMoldId.value);
  } finally { loading.value = false; }
}

async function createMold() {
  if (!form.mold_code || !form.mold_name || !form.tool_equipment_id || !form.product_material_id) return message.warning(tip('fieldsRequired'));
  await createMoldApi(form); message.success(tip('created'));
  Object.assign(form, { mold_code: '', mold_name: '', tool_equipment_id: undefined, product_material_id: undefined }); await load();
}
async function selectMold(id: number) { selectedMoldId.value = id; cavities.value = await getMoldCavitiesApi(id); }
async function mount() { if (!mountForm.mold_id || !mountForm.equipment_id) return message.warning(tip('mountFieldsRequired')); await mountMoldApi(mountForm.mold_id, mountForm); message.success(tip('mounted')); await load(); }
async function unmount(row: MoldItem) { await unmountMoldApi(row.id, { remark: '生产结束下模' }); message.success(tip('unmounted')); await load(); }
async function createMaintenance(row: MoldItem, type = 'PREVENTIVE') { await createMoldMaintenanceApi(row.id, { maintenance_type: type, trigger_type: 'MANUAL', description: type === 'PREVENTIVE' ? '计划预防保养' : '模具故障维修' }); message.success(tip('taskCreated')); await load(); }
async function startMaintenance(row: MoldMaintenance) { await startMoldMaintenanceApi(row.id); message.success(tip('taskStarted')); await load(); }
async function completeMaintenance(row: MoldMaintenance) { await completeMoldMaintenanceApi(row.id, { findings: '模具状态检查完成', action_taken: '清洁、润滑并更换磨损件', labor_cost: 100, material_cost: 50, external_cost: 0 }); message.success(tip('maintenanceCompleted')); await load(); }
async function cavityDecision(row: MoldCavity, failed: boolean) { if (failed) await recordMoldQualityApi(row.mold_id, { cavity_id: row.id, inspected_quantity: 10, defect_quantity: 1, result: 'FAIL', defect_code: 'DIMENSION', notes: '穴位尺寸异常' }); else await updateMoldCavityApi(row.id, { status: 'ACTIVE', remark: '维修验证合格，恢复穴位' }); message.success(tip('cavityUpdated')); await load(); }

onMounted(load);
</script>

<template>
  <Page title="模具全生命周期" auto-content-height>
    <div v-if="dashboard" class="mb-4 grid grid-cols-7 gap-3">
      <a-card size="small" title="模具总数">{{ dashboard.total_molds }}</a-card><a-card size="small" title="在机">{{ dashboard.mounted_molds }}</a-card>
      <a-card size="small" title="保养到期">{{ dashboard.maintenance_due }}</a-card><a-card size="small" title="寿命预警">{{ dashboard.life_warning }}</a-card>
      <a-card size="small" title="超寿命">{{ dashboard.life_exceeded }}</a-card><a-card size="small" title="封锁穴位">{{ dashboard.blocked_cavities }}</a-card>
      <a-card size="small" title="生命周期成本">{{ dashboard.total_lifecycle_cost }}</a-card>
    </div>
    <a-tabs>
      <a-tab-pane key="asset" tab="模具台账与寿命">
        <a-card title="新增模具" size="small" class="mb-4"><a-space wrap>
          <a-input v-model:value="form.mold_code" placeholder="模具编码" /><a-input v-model:value="form.mold_name" placeholder="模具名称" />
          <a-select v-model:value="form.tool_equipment_id" placeholder="工装设备" style="width:220px" :options="option(tools)" />
          <a-select v-model:value="form.product_material_id" show-search placeholder="产品物料" style="width:250px" :options="option(materials)" />
          <span>穴位</span><a-input-number v-model:value="form.cavity_count" :min="1" /><span>设计寿命</span><a-input-number v-model:value="form.designed_life_shots" :min="1" />
          <span>保养周期</span><a-input-number v-model:value="form.maintenance_interval_shots" :min="1" /><span>购置成本</span><a-input-number v-model:value="form.acquisition_cost" :min="0" />
          <a-button type="primary" @click="createMold">建档</a-button>
        </a-space></a-card>
        <a-table :data-source="molds" :loading="loading" row-key="id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'"><a-tag :color="color(record.status)">{{ record.status }}</a-tag></template>
            <template v-else-if="column.key === 'life'"><a-progress :percent="lifePercent(record)" size="small" /></template>
            <template v-else-if="column.key === 'action'"><a-space><a-button type="link" @click="selectMold(record.id)">穴位</a-button><a-button v-if="record.status === 'MOUNTED'" type="link" @click="unmount(record)">下模</a-button><a-button type="link" @click="createMaintenance(record)">保养</a-button><a-button danger type="link" @click="createMaintenance(record, 'REPAIR')">维修</a-button></a-space></template>
          </template>
          <a-table-column title="编码" data-index="mold_code" /><a-table-column title="名称" data-index="mold_name" /><a-table-column title="类型" data-index="mold_type" />
          <a-table-column title="穴位" data-index="cavity_count" /><a-table-column title="当前冲次" data-index="current_shots" /><a-table-column title="寿命" key="life" />
          <a-table-column title="保养后冲次" data-index="shots_since_maintenance" /><a-table-column title="状态" key="status" /><a-table-column title="操作" key="action" />
        </a-table>
      </a-tab-pane>
      <a-tab-pane key="mount" tab="上下模与生产">
        <a-space wrap class="mb-4"><a-select v-model:value="mountForm.mold_id" placeholder="模具" style="width:240px" :options="moldOption()" /><a-select v-model:value="mountForm.equipment_id" placeholder="生产设备" style="width:240px" :options="option(machines)" /><a-select v-model:value="mountForm.work_order_id" placeholder="绑定工单" style="width:280px" :options="workOrderOption()" /><a-button type="primary" @click="mount">上模</a-button></a-space>
        <a-table :data-source="mounts" row-key="id" size="small"><a-table-column title="上下模单" data-index="mount_no" /><a-table-column title="模具ID" data-index="mold_id" /><a-table-column title="设备ID" data-index="equipment_id" /><a-table-column title="工单ID" data-index="work_order_id" /><a-table-column title="开模冲次" data-index="opening_shots" /><a-table-column title="生产数量" data-index="produced_quantity" /><a-table-column title="状态" data-index="status" /></a-table>
      </a-tab-pane>
      <a-tab-pane key="cavity" tab="穴位质量">
        <a-table :data-source="cavities" row-key="id" size="small"><template #bodyCell="{ column, record }"><template v-if="column.key === 'status'"><a-tag :color="color(record.status)">{{ record.status }}</a-tag></template><template v-else-if="column.key === 'action'"><a-space><a-button danger type="link" @click="cavityDecision(record, true)">记录不良</a-button><a-button type="link" @click="cavityDecision(record, false)">恢复</a-button></a-space></template></template><a-table-column title="穴位" data-index="cavity_no" /><a-table-column title="冲次" data-index="current_shots" /><a-table-column title="检查数" data-index="inspected_quantity" /><a-table-column title="不良数" data-index="defect_quantity" /><a-table-column title="缺陷" data-index="last_defect_code" /><a-table-column title="状态" key="status" /><a-table-column title="操作" key="action" /></a-table>
      </a-tab-pane>
      <a-tab-pane key="maintenance" tab="保养维修与成本">
        <a-table :data-source="maintenance" row-key="id" size="small"><template #bodyCell="{ column, record }"><template v-if="column.key === 'status'"><a-tag :color="color(record.status)">{{ record.status }}</a-tag></template><template v-else-if="column.key === 'action'"><a-button v-if="record.status === 'PLANNED'" type="link" @click="startMaintenance(record)">开始</a-button><a-button v-if="record.status === 'IN_PROGRESS'" type="link" @click="completeMaintenance(record)">完工入账</a-button></template></template><a-table-column title="任务单" data-index="order_no" /><a-table-column title="模具ID" data-index="mold_id" /><a-table-column title="类型" data-index="maintenance_type" /><a-table-column title="触发" data-index="trigger_type" /><a-table-column title="说明" data-index="description" /><a-table-column title="状态" key="status" /><a-table-column title="成本" data-index="total_cost" /><a-table-column title="操作" key="action" /></a-table>
      </a-tab-pane>
    </a-tabs>
  </Page>
</template>
