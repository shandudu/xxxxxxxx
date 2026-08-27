<script lang="ts" setup>
import type { MaterialOption } from '../../material/api';
import type {
  LotItem,
  LotStatus,
  ObjectType,
  RuleStatus,
  SerialItem,
  SerialStatus,
  TraceNode,
  TraceRule,
  TraceRuleType,
} from '../api';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import { getMaterialOptionsApi } from '../../material/api';
import {
  createLotApi,
  createTraceRelationApi,
  createTraceRuleApi,
  generateSerialsApi,
  getBackwardTraceApi,
  getForwardTraceApi,
  getLotApi,
  getLotListApi,
  getMaterialTraceRuleApi,
  getSerialListApi,
  getTraceRulesApi,
  mergeLotsApi,
  previewTraceRuleApi,
  splitLotApi,
  updateLotStatusApi,
  updateMaterialTraceRuleApi,
  updateSerialStatusApi,
  updateTraceRuleApi,
} from '../api';

interface PageData<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
}

interface TreeItem {
  children: TreeItem[];
  key: string;
  title: string;
}

const activeTab = ref('rules');
const loading = ref(false);
const materials = ref<MaterialOption[]>([]);
const rules = ref<TraceRule[]>([]);
const selectedMaterialId = ref<number>();
const lotKeyword = ref('');
const serialKeyword = ref('');
const lotPage = ref<PageData<LotItem>>({ items: [], page: 1, size: 20, total: 0 });
const serialPage = ref<PageData<SerialItem>>({ items: [], page: 1, size: 20, total: 0 });
const selectedLot = ref<LotItem>();

const ruleModalOpen = ref(false);
const ruleSaving = ref(false);
const rulePreview = ref('');
const ruleForm = ref<Record<string, any>>({});
const materialRuleOpen = ref(false);
const materialRuleForm = reactive<{ lot_rule_id?: number; serial_rule_id?: number }>({});
const lotModalOpen = ref(false);
const lotForm = ref<Record<string, any>>({});
const serialModalOpen = ref(false);
const serialForm = ref<Record<string, any>>({});
const splitModalOpen = ref(false);
const splitForm = reactive({ children: [{ lot_no: '', quantity: undefined as number | undefined }] });
const mergeModalOpen = ref(false);
const mergeSourceIds = ref('');
const mergeTarget = reactive<Record<string, any>>({});
const relationModalOpen = ref(false);
const relationForm = ref<Record<string, any>>({});

const traceCode = ref('');
const traceType = ref<ObjectType>();
const forwardTrace = ref<TraceNode>();
const backwardTrace = ref<TraceNode>();
const traceLoading = ref(false);

const lotRules = computed(() => rules.value.filter((item) => item.rule_type === 'LOT'));
const serialRules = computed(() => rules.value.filter((item) => item.rule_type === 'SERIAL'));
const materialOptions = computed(() =>
  materials.value.map((item) => ({ label: `${item.name} (${item.code})`, value: item.id })),
);

const ruleColumns = [
  { title: '规则编码', dataIndex: 'rule_code', key: 'rule_code' },
  { title: '规则名称', dataIndex: 'rule_name', key: 'rule_name' },
  { title: '类型', dataIndex: 'rule_type', key: 'rule_type' },
  { title: 'Pattern', dataIndex: 'pattern', key: 'pattern' },
  { title: '序列长度', dataIndex: 'sequence_length', key: 'sequence_length' },
  { title: '重置周期', dataIndex: 'sequence_reset_type', key: 'sequence_reset_type' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '操作', key: 'action', width: 100 },
];
const lotColumns = [
  { title: '批次号', dataIndex: 'lot_no', key: 'lot_no' },
  { title: '物料', key: 'material' },
  { title: '类型', dataIndex: 'lot_type', key: 'lot_type' },
  { title: '初始数量', key: 'quantity' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '质量状态', dataIndex: 'quality_status', key: 'quality_status' },
];
const serialColumns = [
  { title: 'SN', dataIndex: 'serial_no', key: 'serial_no' },
  { title: '物料', key: 'material' },
  { title: '所属 Lot', dataIndex: 'lot_no', key: 'lot_no' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '质量状态', dataIndex: 'quality_status', key: 'quality_status' },
  { title: '生产日期', dataIndex: 'production_date', key: 'production_date' },
];

function statusColor(status: string) {
  if (status === 'ACTIVE' || status === 'PASS') return 'green';
  if (status === 'HOLD' || status === 'UNINSPECTED') return 'orange';
  return 'default';
}

function nodeToTree(node?: TraceNode): TreeItem[] {
  if (!node) return [];
  return [{
    key: `${node.object_type}-${node.object_id}`,
    title: `${node.code} · ${node.material_code ?? ''} ${node.material_name ?? ''}`,
    children: node.children.flatMap((item) => nodeToTree(item)),
  }];
}

const forwardTree = computed(() => nodeToTree(forwardTrace.value));
const backwardTree = computed(() => nodeToTree(backwardTrace.value));

async function loadMaterials() {
  materials.value = await getMaterialOptionsApi();
}

async function loadRules() {
  rules.value = await getTraceRulesApi();
}

async function loadLots(page = lotPage.value.page) {
  const data = await getLotListApi({
    page,
    size: lotPage.value.size,
    keyword: lotKeyword.value || undefined,
    material_id: selectedMaterialId.value,
  });
  lotPage.value = data;
  if (selectedLot.value) {
    const matching = data.items.find((item) => item.id === selectedLot.value?.id);
    if (matching) selectedLot.value = matching;
  }
}

async function loadSerials(page = serialPage.value.page) {
  serialPage.value = await getSerialListApi({
    page,
    size: serialPage.value.size,
    keyword: serialKeyword.value || undefined,
    material_id: selectedMaterialId.value,
  });
}

async function refreshData() {
  loading.value = true;
  try {
    await Promise.all([loadRules(), loadLots(1), loadSerials(1)]);
  } finally {
    loading.value = false;
  }
}

function openCreateRule() {
  rulePreview.value = '';
  ruleForm.value = {
    rule_code: '',
    rule_name: '',
    rule_type: 'LOT' as TraceRuleType,
    pattern: '{MATERIAL}-{YYYYMMDD}-{SEQ}',
    sequence_length: 4,
    sequence_reset_type: 'DAILY',
    status: 'ACTIVE' as RuleStatus,
  };
  ruleModalOpen.value = true;
}

function openEditRule(rule: TraceRule) {
  rulePreview.value = rule.example || '';
  ruleForm.value = { ...rule };
  ruleModalOpen.value = true;
}

async function previewRule() {
  if (!ruleForm.value.pattern) return;
  const result = await previewTraceRuleApi({
    pattern: ruleForm.value.pattern,
    sequence_length: ruleForm.value.sequence_length,
    prefix: ruleForm.value.prefix || undefined,
    material_id: selectedMaterialId.value,
  });
  rulePreview.value = result.example;
}

async function saveRule() {
  if (!ruleForm.value.rule_code || !ruleForm.value.rule_name || !ruleForm.value.pattern) {
    message.warning('请填写规则编码、名称和 Pattern');
    return;
  }
  ruleSaving.value = true;
  try {
    if (ruleForm.value.id) await updateTraceRuleApi(ruleForm.value.id, ruleForm.value);
    else await createTraceRuleApi(ruleForm.value);
    ruleModalOpen.value = false;
    await loadRules();
    message.success('编码规则已保存');
  } finally {
    ruleSaving.value = false;
  }
}

async function openMaterialRules() {
  if (!selectedMaterialId.value) {
    message.warning('请先选择物料');
    return;
  }
  const data = await getMaterialTraceRuleApi(selectedMaterialId.value);
  materialRuleForm.lot_rule_id = data.lot_rule_id;
  materialRuleForm.serial_rule_id = data.serial_rule_id;
  materialRuleOpen.value = true;
}

async function saveMaterialRules() {
  if (!selectedMaterialId.value) return;
  await updateMaterialTraceRuleApi(selectedMaterialId.value, materialRuleForm);
  materialRuleOpen.value = false;
  message.success('物料追溯规则已保存');
}

function openCreateLot() {
  lotForm.value = {
    material_id: selectedMaterialId.value,
    lot_no: '',
    generate_by_rule: true,
    lot_type: 'INTERNAL',
    source_type: 'MANUAL',
    quantity: undefined,
    status: 'ACTIVE',
    quality_status: 'UNINSPECTED',
  };
  lotModalOpen.value = true;
}

async function saveLot() {
  if (!lotForm.value.material_id) {
    message.warning('请选择物料');
    return;
  }
  await createLotApi(lotForm.value);
  lotModalOpen.value = false;
  await loadLots(1);
  message.success('Lot 已创建');
}

async function selectLot(item: LotItem) {
  selectedLot.value = await getLotApi(item.id);
}

async function toggleLotStatus() {
  if (!selectedLot.value) return;
  const status: LotStatus = selectedLot.value.status === 'ACTIVE' ? 'HOLD' : 'ACTIVE';
  selectedLot.value = await updateLotStatusApi(selectedLot.value.id, status);
  await loadLots();
}

function openSplitLot() {
  if (!selectedLot.value) return;
  splitForm.children = [
    { lot_no: `${selectedLot.value.lot_no}-A`, quantity: undefined },
    { lot_no: `${selectedLot.value.lot_no}-B`, quantity: undefined },
  ];
  splitModalOpen.value = true;
}

async function saveSplitLot() {
  if (!selectedLot.value) return;
  const children = splitForm.children.filter(
    (item): item is { lot_no: string; quantity: number } =>
      Boolean(item.lot_no) && typeof item.quantity === 'number' && item.quantity > 0,
  );
  await splitLotApi(selectedLot.value.id, {
    children,
  });
  splitModalOpen.value = false;
  await loadLots(1);
  message.success('Lot 拆分完成');
}

function openMergeLots() {
  const materialId = selectedMaterialId.value || selectedLot.value?.material_id;
  mergeSourceIds.value = selectedLot.value ? String(selectedLot.value.id) : '';
  Object.assign(mergeTarget, {
    material_id: materialId,
    lot_no: '',
    quantity: undefined,
    lot_type: 'INTERNAL',
    quality_status: 'UNINSPECTED',
  });
  mergeModalOpen.value = true;
}

async function saveMergeLots() {
  const sourceLotIds = mergeSourceIds.value.split(',').map(Number).filter(Boolean);
  if (sourceLotIds.length < 2 || !mergeTarget.material_id || !mergeTarget.lot_no) {
    message.warning('请输入至少两个源 Lot ID，并填写目标 Lot');
    return;
  }
  await mergeLotsApi({ source_lot_ids: sourceLotIds, target_lot: mergeTarget });
  mergeModalOpen.value = false;
  await loadLots(1);
  message.success('Lot 合并完成');
}

function openGenerateSerials() {
  serialForm.value = {
    material_id: selectedMaterialId.value || selectedLot.value?.material_id,
    lot_id: selectedLot.value?.id,
    quantity: 1,
    source_type: 'MANUAL',
  };
  serialModalOpen.value = true;
}

async function saveGenerateSerials() {
  if (!serialForm.value.material_id || !serialForm.value.quantity) {
    message.warning('请选择物料并填写数量');
    return;
  }
  const result = await generateSerialsApi(serialForm.value);
  serialModalOpen.value = false;
  await loadSerials(1);
  message.success(`已生成 ${result.count} 个 SN`);
}

async function toggleSerialStatus(item: SerialItem) {
  const status: SerialStatus = item.status === 'ACTIVE' ? 'HOLD' : 'ACTIVE';
  await updateSerialStatusApi(item.id, status);
  await loadSerials();
}

function openCreateRelation() {
  relationForm.value = {
    source_type: 'LOT',
    source_id: selectedLot.value?.id,
    target_type: 'LOT',
    target_id: undefined,
    relation_type: 'CONSUMED_TO',
  };
  relationModalOpen.value = true;
}

async function saveRelation() {
  await createTraceRelationApi(relationForm.value);
  relationModalOpen.value = false;
  message.success('追溯关系已创建');
}

async function lookupTrace() {
  const code = traceCode.value.trim();
  if (!code) return;
  traceLoading.value = true;
  forwardTrace.value = undefined;
  backwardTrace.value = undefined;
  try {
    let type: ObjectType = 'LOT';
    let forward: TraceNode;
    try {
      forward = await getForwardTraceApi('LOT', code);
    } catch {
      type = 'SERIAL';
      forward = await getForwardTraceApi('SERIAL', code);
    }
    traceType.value = type;
    forwardTrace.value = forward;
    backwardTrace.value = await getBackwardTraceApi(type, code);
  } catch {
    message.error('未找到 Lot 或 SN，请检查编码');
  } finally {
    traceLoading.value = false;
  }
}

onMounted(async () => {
  await loadMaterials();
  await refreshData();
});
</script>

<template>
  <Page auto-content-height>
    <a-tabs v-model:active-key="activeTab">
      <a-tab-pane key="rules" tab="追溯编码规则">
        <a-card :loading="loading">
          <template #extra><a-button type="primary" @click="openCreateRule">新增规则</a-button></template>
          <a-table :columns="ruleColumns" :data-source="rules" :pagination="false" :row-key="(item: TraceRule) => item.id" size="small">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
              <template v-else-if="column.key === 'action'"><a-button type="link" size="small" @click="openEditRule(record)">配置</a-button></template>
            </template>
          </a-table>
          <a-alert class="mt-4" type="info" show-icon message="支持 {YYYY}、{YY}、{MM}、{DD}、{YYYYMMDD}、{MATERIAL}、{MATERIAL_CODE} 与 {SEQ}。编码序列由数据库行锁原子预留。" />
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="lots" tab="批次 / SN">
        <div class="mb-3 flex flex-wrap gap-2">
          <a-select v-model:value="selectedMaterialId" allow-clear class="w-64" :options="materialOptions" placeholder="按物料筛选" @change="refreshData" />
          <a-button :disabled="!selectedMaterialId" @click="openMaterialRules">物料编码规则</a-button>
          <a-button type="primary" @click="openCreateLot">创建 Lot</a-button>
          <a-button @click="openMergeLots">合并 Lot</a-button>
          <a-button @click="openCreateRelation">创建追溯关系</a-button>
        </div>
        <div class="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div class="space-y-3">
            <a-card title="Lot 列表" :loading="loading">
              <template #extra><a-input-search v-model:value="lotKeyword" allow-clear placeholder="Lot 编号" @search="loadLots(1)" /></template>
              <a-table :columns="lotColumns" :data-source="lotPage.items" :pagination="false" :row-key="(item: LotItem) => item.id" size="small">
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'lot_no'"><a-button type="link" class="h-auto p-0" @click="selectLot(record)">{{ record.lot_no }}</a-button></template>
                  <template v-else-if="column.key === 'material'">{{ record.material_code }} {{ record.material_name }}</template>
                  <template v-else-if="column.key === 'quantity'">{{ record.quantity ?? '-' }} {{ record.unit_code }}</template>
                  <template v-else-if="column.key === 'status' || column.key === 'quality_status'"><a-tag :color="statusColor(record[column.key])">{{ record[column.key] }}</a-tag></template>
                </template>
              </a-table>
              <div class="mt-3 flex justify-end"><a-pagination :current="lotPage.page" :page-size="lotPage.size" :total="lotPage.total" @change="(page) => loadLots(page)" /></div>
            </a-card>
            <a-card title="SN 列表" :loading="loading">
              <template #extra><a-space><a-input-search v-model:value="serialKeyword" allow-clear placeholder="SN 编号" @search="loadSerials(1)" /><a-button type="primary" @click="openGenerateSerials">批量生成 SN</a-button></a-space></template>
              <a-table :columns="serialColumns" :data-source="serialPage.items" :pagination="false" :row-key="(item: SerialItem) => item.id" size="small">
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'material'">{{ record.material_code }} {{ record.material_name }}</template>
                  <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)" class="cursor-pointer" @click="toggleSerialStatus(record)">{{ record.status }}</a-tag></template>
                  <template v-else-if="column.key === 'quality_status'"><a-tag :color="statusColor(record.quality_status)">{{ record.quality_status }}</a-tag></template>
                </template>
              </a-table>
              <div class="mt-3 flex justify-end"><a-pagination :current="serialPage.page" :page-size="serialPage.size" :total="serialPage.total" @change="(page) => loadSerials(page)" /></div>
            </a-card>
          </div>
          <a-card title="Lot 详情">
            <a-empty v-if="!selectedLot" description="请选择 Lot" />
            <template v-else>
              <a-descriptions :column="1" size="small">
                <a-descriptions-item label="批次号">{{ selectedLot.lot_no }}</a-descriptions-item>
                <a-descriptions-item label="物料">{{ selectedLot.material_code }} {{ selectedLot.material_name }}</a-descriptions-item>
                <a-descriptions-item label="批次类型">{{ selectedLot.lot_type }}</a-descriptions-item>
                <a-descriptions-item label="初始数量">{{ selectedLot.quantity }} {{ selectedLot.unit_code }}</a-descriptions-item>
                <a-descriptions-item label="来源">{{ selectedLot.source_type || '-' }} {{ selectedLot.source_ref_no || '' }}</a-descriptions-item>
                <a-descriptions-item label="供应商批次">{{ selectedLot.supplier_lot_no || '-' }}</a-descriptions-item>
                <a-descriptions-item label="生产日期">{{ selectedLot.production_date || '-' }}</a-descriptions-item>
                <a-descriptions-item label="有效期">{{ selectedLot.expiry_date || '-' }}</a-descriptions-item>
                <a-descriptions-item label="状态"><a-tag :color="statusColor(selectedLot.status)">{{ selectedLot.status }}</a-tag></a-descriptions-item>
                <a-descriptions-item label="质量状态"><a-tag :color="statusColor(selectedLot.quality_status)">{{ selectedLot.quality_status }}</a-tag></a-descriptions-item>
              </a-descriptions>
              <a-space class="mt-4" wrap>
                <a-button @click="toggleLotStatus">{{ selectedLot.status === 'ACTIVE' ? '冻结' : '启用' }}</a-button>
                <a-button :disabled="selectedLot.status !== 'ACTIVE'" @click="openSplitLot">拆分 Lot</a-button>
                <a-button @click="openGenerateSerials">生成 SN</a-button>
              </a-space>
            </template>
          </a-card>
        </div>
      </a-tab-pane>

      <a-tab-pane key="query" tab="追溯查询">
        <a-card>
          <div class="mb-4 flex max-w-2xl gap-2">
            <a-input-search v-model:value="traceCode" allow-clear enter-button="查询 Lot / SN" placeholder="输入批次号或 SN，系统自动识别" :loading="traceLoading" @search="lookupTrace" />
          </div>
          <a-alert v-if="traceType" class="mb-4" type="info" show-icon :message="`已识别为 ${traceType}，最大追溯深度为 30 层。`" />
          <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <a-card title="反向追溯 · 来源"><a-empty v-if="!backwardTrace" description="查询后显示原料来源" /><a-tree v-else :default-expand-all="true" :tree-data="backwardTree" /></a-card>
            <a-card title="正向追溯 · 去向"><a-empty v-if="!forwardTrace" description="查询后显示下游去向" /><a-tree v-else :default-expand-all="true" :tree-data="forwardTree" /></a-card>
          </div>
        </a-card>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="ruleModalOpen" :confirm-loading="ruleSaving" :title="ruleForm.id ? '配置编码规则' : '新增编码规则'" width="680px" @ok="saveRule">
      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12"><a-form-item label="规则编码" required><a-input v-model:value="ruleForm.rule_code" :disabled="Boolean(ruleForm.id)" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="规则名称" required><a-input v-model:value="ruleForm.rule_name" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="类型"><a-select v-model:value="ruleForm.rule_type" :options="[{ label: 'Lot', value: 'LOT' }, { label: 'SN', value: 'SERIAL' }]" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="序列长度"><a-input-number v-model:value="ruleForm.sequence_length" class="w-full" :min="1" :max="20" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="重置周期"><a-select v-model:value="ruleForm.sequence_reset_type" :options="['NEVER', 'YEARLY', 'MONTHLY', 'DAILY'].map(value => ({ label: value, value }))" /></a-form-item></a-col>
        </a-row>
        <a-form-item label="Pattern" required><a-input v-model:value="ruleForm.pattern" /></a-form-item>
        <a-form-item label="Prefix"><a-input v-model:value="ruleForm.prefix" /></a-form-item>
        <a-form-item label="预览物料（Pattern 使用 MATERIAL 时必填）"><a-select v-model:value="selectedMaterialId" allow-clear :options="materialOptions" /></a-form-item>
        <a-form-item label="状态"><a-select v-model:value="ruleForm.status" :options="[{ label: 'ACTIVE', value: 'ACTIVE' }, { label: 'DISABLED', value: 'DISABLED' }]" /></a-form-item>
        <a-form-item label="备注"><a-textarea v-model:value="ruleForm.remark" :rows="2" /></a-form-item>
        <a-space><a-button @click="previewRule">预览</a-button><a-tag v-if="rulePreview" color="blue">{{ rulePreview }}</a-tag></a-space>
      </a-form>
    </a-modal>

    <a-modal v-model:open="materialRuleOpen" title="物料追溯编码规则" @ok="saveMaterialRules">
      <a-form layout="vertical">
        <a-form-item label="Lot 编码规则"><a-select v-model:value="materialRuleForm.lot_rule_id" allow-clear :options="lotRules.map(item => ({ label: `${item.rule_name} (${item.rule_code})`, value: item.id }))" /></a-form-item>
        <a-form-item label="SN 编码规则"><a-select v-model:value="materialRuleForm.serial_rule_id" allow-clear :options="serialRules.map(item => ({ label: `${item.rule_name} (${item.rule_code})`, value: item.id }))" /></a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="lotModalOpen" title="创建 Lot" @ok="saveLot">
      <a-form layout="vertical">
        <a-form-item label="物料" required><a-select v-model:value="lotForm.material_id" :options="materialOptions" /></a-form-item>
        <a-form-item label="按规则生成"><a-switch v-model:checked="lotForm.generate_by_rule" /></a-form-item>
        <a-form-item v-if="!lotForm.generate_by_rule" label="批次号" required><a-input v-model:value="lotForm.lot_no" /></a-form-item>
        <a-row :gutter="16"><a-col :span="12"><a-form-item label="批次类型"><a-select v-model:value="lotForm.lot_type" :options="['SUPPLIER', 'INTERNAL', 'WIP', 'FINISHED', 'REWORK', 'OTHER'].map(value => ({ label: value, value }))" /></a-form-item></a-col><a-col :span="12"><a-form-item label="初始数量"><a-input-number v-model:value="lotForm.quantity" class="w-full" :min="0" /></a-form-item></a-col></a-row>
        <a-form-item label="生产日期（ISO 8601）"><a-input v-model:value="lotForm.production_date" placeholder="2026-08-08T10:00:00" /></a-form-item>
        <a-form-item label="备注"><a-textarea v-model:value="lotForm.remark" /></a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="serialModalOpen" title="批量生成 SN" @ok="saveGenerateSerials">
      <a-form layout="vertical"><a-form-item label="物料" required><a-select v-model:value="serialForm.material_id" :options="materialOptions" /></a-form-item><a-form-item label="所属 Lot"><a-select v-model:value="serialForm.lot_id" allow-clear :options="lotPage.items.map(item => ({ label: item.lot_no, value: item.id }))" /></a-form-item><a-form-item label="生成数量" required><a-input-number v-model:value="serialForm.quantity" class="w-full" :min="1" :max="10000" /></a-form-item></a-form>
    </a-modal>

    <a-modal v-model:open="splitModalOpen" title="Lot 拆分" @ok="saveSplitLot">
      <a-alert class="mb-3" type="info" show-icon message="子 Lot 数量总和不得超过原 Lot 初始数量；本操作不扣减库存。" />
      <div v-for="(child, index) in splitForm.children" :key="index" class="mb-2 flex gap-2"><a-input v-model:value="child.lot_no" placeholder="子 Lot 编号" /><a-input-number v-model:value="child.quantity" :min="0.000001" placeholder="数量" /><a-button danger @click="splitForm.children.splice(index, 1)">删除</a-button></div>
      <a-button @click="splitForm.children.push({ lot_no: '', quantity: undefined })">添加子 Lot</a-button>
    </a-modal>

    <a-modal v-model:open="mergeModalOpen" title="Lot 合并" @ok="saveMergeLots">
      <a-form layout="vertical"><a-form-item label="源 Lot ID（逗号分隔，至少两个）" required><a-input v-model:value="mergeSourceIds" /></a-form-item><a-form-item label="目标物料" required><a-select v-model:value="mergeTarget.material_id" :options="materialOptions" /></a-form-item><a-form-item label="目标 Lot 编号" required><a-input v-model:value="mergeTarget.lot_no" /></a-form-item><a-form-item label="初始数量"><a-input-number v-model:value="mergeTarget.quantity" class="w-full" :min="0" /></a-form-item></a-form>
    </a-modal>

    <a-modal v-model:open="relationModalOpen" title="创建追溯关系" @ok="saveRelation">
      <a-form layout="vertical"><a-row :gutter="12"><a-col :span="12"><a-form-item label="来源类型"><a-select v-model:value="relationForm.source_type" :options="['LOT', 'SERIAL'].map(value => ({ label: value, value }))" /></a-form-item></a-col><a-col :span="12"><a-form-item label="来源 ID"><a-input-number v-model:value="relationForm.source_id" class="w-full" :min="1" /></a-form-item></a-col><a-col :span="12"><a-form-item label="目标类型"><a-select v-model:value="relationForm.target_type" :options="['LOT', 'SERIAL'].map(value => ({ label: value, value }))" /></a-form-item></a-col><a-col :span="12"><a-form-item label="目标 ID"><a-input-number v-model:value="relationForm.target_id" class="w-full" :min="1" /></a-form-item></a-col></a-row><a-form-item label="关系类型"><a-select v-model:value="relationForm.relation_type" :options="['CONSUMED_TO', 'PRODUCED_FROM', 'SPLIT_TO', 'MERGED_TO', 'PACKED_INTO', 'REWORK_TO'].map(value => ({ label: value, value }))" /></a-form-item><a-form-item label="数量"><a-input-number v-model:value="relationForm.quantity" class="w-full" :min="0" /></a-form-item></a-form>
    </a-modal>
  </Page>
</template>
