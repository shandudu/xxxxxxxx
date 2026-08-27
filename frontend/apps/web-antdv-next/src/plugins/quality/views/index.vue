<script lang="ts" setup>
import type { MaterialOption } from '../../material/api';
import type { LocationItem, WarehouseItem } from '../../warehouse/api';
import type {
  Disposition,
  Capa,
  CapaAction,
  CapaVerification,
  CustomerComplaint,
  CustomerReturn,
  AfterSalesOrder,
  Inspection,
  InspectionItem,
  InspectionResultLine,
  InspectionStandard,
  InspectionTemplate,
  Ncr,
  ReworkOrder,
  SamplingPlan,
  OperationDashboardSummary,
  SlaAlert,
} from '../api';

import { computed, onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';
import { useRouter } from 'vue-router';

import { $t } from '#/locales';
import { getMaterialOptionsApi } from '../../material/api';
import { getWarehouseListApi, getWarehouseTreeApi } from '../../warehouse/api';
import {
  activateInspectionTemplateApi,
  closeNcrApi,
  completeInspectionApi,
  createDispositionApi,
  createCapaActionApi,
  createCapaApi,
  createInspectionApi,
  createInspectionItemApi,
  createInspectionStandardApi,
  createInspectionTemplateApi,
  createNcrApi,
  createSamplingPlanApi,
  createReworkWorkOrderApi,
  completeReworkApi,
  closeCapaApi,
  deactivateInspectionTemplateApi,
  executeDispositionApi,
  getDispositionsApi,
  getCapaActionsApi,
  getCapasApi,
  getCapaVerificationsApi,
  getInspectionItemsApi,
  getInspectionResultsApi,
  getInspectionStandardsApi,
  getInspectionsApi,
  getInspectionTemplatesApi,
  getNcrsApi,
  getReworkOrdersApi,
  getSamplingPlansApi,
  setInspectionItemStatusApi,
  setCapaActionStatusApi,
  setSamplingPlanStatusApi,
  startReworkApi,
  submitInspectionResultsApi,
  verifyCapaApi,
  closeCustomerReturnApi,
  createCustomerComplaintApi,
  createCustomerReturnApi,
  getCustomerComplaintsApi,
  getCustomerReturnsApi,
  inspectCustomerReturnApi,
  receiveCustomerReturnApi,
  resolveCustomerReturnApi,
  approveAfterSalesOrderApi,
  completeAfterSalesOrderApi,
  completeAfterSalesRepairTaskApi,
  createAfterSalesOrderApi,
  getAfterSalesOrdersApi,
  getAfterSalesRepairTaskApi,
  startAfterSalesOrderApi,
  getOperationDashboardApi,
  getSlaAlertsApi,
  acknowledgeSlaAlertApi,
  escalateSlaAlertApi,
  closeSlaAlertApi,
} from '../api';

type DialogKind = 'afterSales' | 'capa' | 'capaAction' | 'capaVerify' | 'complete' | 'complaint' | 'disposition' | 'inspection' | 'item' | 'ncr' | 'return' | 'returnInspect' | 'returnResolve' | 'results' | 'sampling' | 'standard' | 'template';

const tab = ref('inspections');
const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const visible = ref(false);
const kind = ref<DialogKind>('inspection');
const inspections = ref<Inspection[]>([]);
const ncrs = ref<Ncr[]>([]);
const dispositions = ref<Disposition[]>([]);
const inspectionItems = ref<InspectionItem[]>([]);
const samplingPlans = ref<SamplingPlan[]>([]);
const templates = ref<InspectionTemplate[]>([]);
const reworkOrders = ref<ReworkOrder[]>([]);
const capas = ref<Capa[]>([]);
const capaActions = ref<CapaAction[]>([]);
const capaVerifications = ref<CapaVerification[]>([]);
const complaints = ref<CustomerComplaint[]>([]);
const customerReturns = ref<CustomerReturn[]>([]);
const afterSalesOrders = ref<AfterSalesOrder[]>([]);
const standards = ref<InspectionStandard[]>([]);
const resultLines = ref<InspectionResultLine[]>([]);
const selectedInspection = ref<Inspection>();
const selectedNcr = ref<Ncr>();
const selectedItem = ref<InspectionItem>();
const selectedSampling = ref<SamplingPlan>();
const selectedTemplate = ref<InspectionTemplate>();
const selectedRework = ref<ReworkOrder>();
const selectedCapa = ref<Capa>();
const selectedReturn = ref<CustomerReturn>();
const selectedAfterSales = ref<AfterSalesOrder>();
const materials = ref<MaterialOption[]>([]);
const warehouses = ref<WarehouseItem[]>([]);
const locations = ref<LocationItem[]>([]);
const form = ref<Record<string, any>>({});
const dashboard = ref<OperationDashboardSummary>();
const slaAlerts = ref<SlaAlert[]>([]);

const dialogTitle = computed(() => ({
  capa: '新建 CAPA / 8D',
  capaAction: '新增整改措施',
  capaVerify: 'CAPA 效果验证',
  complaint: '登记客户投诉',
  afterSales: '创建售后执行单',
  complete: '完成检验',
  disposition: '新建 MRB 处置',
  inspection: '新建检验任务',
  item: '新建检验项目',
  ncr: '新建不合格报告',
  return: '创建退货 RMA',
  returnInspect: '退货检验',
  returnResolve: '登记客户处理结果',
  results: '录入检验结果',
  sampling: '新建抽样方案',
  standard: '添加检验标准',
  template: '新建检验模板',
}[kind.value]));

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
    getMaterialOptionsApi(),
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
    [inspections.value, ncrs.value, inspectionItems.value, samplingPlans.value, templates.value, reworkOrders.value, capas.value, complaints.value, customerReturns.value, afterSalesOrders.value, dashboard.value, slaAlerts.value] = await Promise.all([
      getInspectionsApi(),
      getNcrsApi(),
      getInspectionItemsApi(),
      getSamplingPlansApi(),
      getInspectionTemplatesApi(),
      getReworkOrdersApi(),
      getCapasApi(),
      getCustomerComplaintsApi(),
      getCustomerReturnsApi(),
      getAfterSalesOrdersApi(),
      getOperationDashboardApi(),
      getSlaAlertsApi(),
    ]);
  } finally {
    loading.value = false;
  }
}

async function updateAlert(alert: SlaAlert, action: 'ack' | 'escalate' | 'close') {
  if (action === 'ack') await acknowledgeSlaAlertApi(alert.id);
  if (action === 'escalate') await escalateSlaAlertApi(alert.id, (alert.escalation_level || 0) + 1);
  if (action === 'close') await closeSlaAlertApi(alert.id);
  await load();
}

function drillAlert(alert: SlaAlert) {
  tab.value = alert.entity_type === 'NCR' ? 'ncrs' : alert.entity_type === 'CAPA' ? 'capas' : alert.entity_type === 'RMA' ? 'rma' : alert.entity_type === 'AFTER_SALES' ? 'afterSales' : 'rma';
}

async function selectInspection(row: Inspection) {
  selectedInspection.value = row;
  resultLines.value = await getInspectionResultsApi(row.id);
}

async function selectNcr(row: Ncr) {
  selectedNcr.value = row;
  dispositions.value = await getDispositionsApi(row.id);
}

async function selectTemplate(row: InspectionTemplate) {
  selectedTemplate.value = row;
  standards.value = await getInspectionStandardsApi(row.id);
}

function selectRework(row: ReworkOrder) {
  selectedRework.value = row;
}

function selectReturn(row: CustomerReturn) {
  selectedReturn.value = row;
}

function selectAfterSales(row: AfterSalesOrder) {
  selectedAfterSales.value = row;
}

async function approveAfterSales() {
  if (!selectedAfterSales.value) return;
  selectedAfterSales.value = await approveAfterSalesOrderApi(selectedAfterSales.value.id);
  await load();
}

async function startAfterSales() {
  if (!selectedAfterSales.value) return;
  selectedAfterSales.value = await startAfterSalesOrderApi(selectedAfterSales.value.id);
  await load();
}

async function completeAfterSales() {
  if (!selectedAfterSales.value) return;
  if (selectedAfterSales.value.resolution_type === 'REPAIR') {
    const task = await getAfterSalesRepairTaskApi(selectedAfterSales.value.id);
    if (task.status === 'OPEN') await completeAfterSalesRepairTaskApi(selectedAfterSales.value.id, { result_notes: '维修完成' });
  }
  selectedAfterSales.value = await completeAfterSalesOrderApi(selectedAfterSales.value.id);
  message.success('售后执行单已完成');
  await load();
}

async function receiveReturn() {
  if (!selectedReturn.value) return;
  selectedReturn.value = await receiveCustomerReturnApi(selectedReturn.value.id);
  message.success('RMA 已接收并生成客户退货库存流水');
  await load();
}

async function inspectReturn() {
  if (!selectedReturn.value?.lines[0]) return;
  await open('returnInspect');
}

async function resolveReturn() {
  if (!selectedReturn.value) return;
  await open('returnResolve');
}

async function closeReturn() {
  if (!selectedReturn.value) return;
  selectedReturn.value = await closeCustomerReturnApi(selectedReturn.value.id);
  message.success('RMA 与客户投诉已闭环');
  await load();
}

async function selectCapa(row: Capa) {
  selectedCapa.value = row;
  [capaActions.value, capaVerifications.value] = await Promise.all([
    getCapaActionsApi(row.id),
    getCapaVerificationsApi(row.id),
  ]);
}

async function createReworkWorkOrder() {
  if (!selectedRework.value) return;
  selectedRework.value = await createReworkWorkOrderApi(selectedRework.value.id);
  message.success('返工生产工单已创建并发布');
  await load();
}

async function startRework() {
  if (!selectedRework.value) return;
  selectedRework.value = await startReworkApi(selectedRework.value.id);
  message.success('返工已开始');
  await load();
}

async function completeRework() {
  if (!selectedRework.value) return;
  selectedRework.value = await completeReworkApi(selectedRework.value.id);
  message.success('返工已完成，已生成复检任务');
  await load();
}

function openProduction() {
  if (selectedRework.value?.production_work_order_id) router.push('/mes/production');
}

function locationOptions(warehouseId?: number) {
  return locations.value
    .filter((item) => item.warehouse_id === warehouseId && item.storage_enabled)
    .map((item) => ({ label: `${item.location_code} · ${item.location_name}`, value: item.id }));
}

function inspectionItem(id: number) {
  return inspectionItems.value.find((item) => item.id === id);
}

async function open(dialog: DialogKind) {
  kind.value = dialog;
  if (dialog === 'inspection') form.value = { inspection_type: 'INCOMING', sample_quantity: 1 };
  if (dialog === 'complete' && selectedInspection.value) form.value = { accepted_quantity: selectedInspection.value.sample_quantity, rejected_quantity: 0, result: 'PASS', conclusion: '' };
  if (dialog === 'ncr' && selectedInspection.value) form.value = { inspection_id: selectedInspection.value.id, nonconforming_quantity: selectedInspection.value.rejected_quantity || 1, severity: 'MAJOR', defect_description: '' };
  if (dialog === 'disposition' && selectedNcr.value) form.value = { ncr_id: selectedNcr.value.id, disposition_type: 'REWORK', quantity: selectedNcr.value.nonconforming_quantity, decision_reason: '' };
  if (dialog === 'capa' && selectedNcr.value) form.value = { ncr_id: selectedNcr.value.id, d2_problem_description: selectedNcr.value.defect_description, d4_root_cause: '', d5_corrective_plan: '' };
  if (dialog === 'capaAction') form.value = { action_type: 'CORRECTIVE', description: '' };
  if (dialog === 'capaVerify') form.value = { result: 'PASS', notes: '' };
  if (dialog === 'complaint') form.value = { customer_id: undefined, shipment_id: undefined, material_id: undefined, lot_id: undefined, quantity: undefined, title: '', description: '' };
  if (dialog === 'return') form.value = { complaint_id: complaints.value.find((item) => !item.rma_id)?.id, shipment_id: undefined, shipment_line_id: undefined, material_id: undefined, lot_id: undefined, warehouse_id: warehouses.value[0]?.id, location_id: undefined, quantity: 1 };
  if (dialog === 'returnInspect' && selectedReturn.value?.lines[0]) form.value = { line_id: selectedReturn.value.lines[0].id, accepted_quantity: 0, rejected_quantity: selectedReturn.value.lines[0].quantity, result: 'FAIL', conclusion: '' };
  if (dialog === 'returnResolve') form.value = { resolution_type: 'REFUND', resolution_notes: '' };
  if (dialog === 'afterSales' && selectedReturn.value) form.value = { resolution_type: selectedReturn.value.resolution_type, replacement_material_id: undefined, replacement_lot_id: undefined, execution_notes: '' };
  if (dialog === 'item') form.value = { item_code: '', item_name: '', value_type: 'NUMERIC', unit_label: '' };
  if (dialog === 'sampling') form.value = { plan_code: '', plan_name: '', sample_size: 1, acceptance_number: 0 };
  if (dialog === 'template') form.value = { template_code: '', template_name: '', material_id: undefined, template_version: 'V1', inspection_type: 'INCOMING' };
  if (dialog === 'standard') form.value = { line_no: standards.value.length + 1, inspection_item_id: inspectionItems.value.find((item) => item.status === 'ACTIVE')?.id, required: true };
  if (dialog === 'results' && selectedInspection.value) {
    const template = templates.value.find((item) => item.status === 'ACTIVE' && item.material_id === selectedInspection.value?.material_id && item.inspection_type === selectedInspection.value?.inspection_type);
    if (!template) {
      message.warning('没有匹配且已生效的检验模板');
      return;
    }
    const rows = await getInspectionStandardsApi(template.id);
    form.value = {
      template_id: template.id,
      results: rows.map((row) => ({ standard_id: row.id })),
      standards: rows,
    };
  }
  visible.value = true;
}

async function submit() {
  saving.value = true;
  try {
    if (kind.value === 'inspection') await createInspectionApi(form.value);
    if (kind.value === 'complete' && selectedInspection.value) selectedInspection.value = await completeInspectionApi(selectedInspection.value.id, form.value);
    if (kind.value === 'ncr') {
      selectedNcr.value = await createNcrApi(form.value);
      tab.value = 'ncrs';
    }
    if (kind.value === 'disposition') await createDispositionApi(form.value);
    if (kind.value === 'capa') {
      selectedCapa.value = await createCapaApi(form.value);
      tab.value = 'capas';
    }
    if (kind.value === 'capaAction' && selectedCapa.value) await createCapaActionApi(selectedCapa.value.id, form.value);
    if (kind.value === 'capaVerify' && selectedCapa.value) await verifyCapaApi(selectedCapa.value.id, form.value);
    if (kind.value === 'complaint') await createCustomerComplaintApi(form.value);
    if (kind.value === 'return') await createCustomerReturnApi({ ...form.value, lines: [{ shipment_line_id: form.value.shipment_line_id, material_id: form.value.material_id, lot_id: form.value.lot_id, warehouse_id: form.value.warehouse_id, location_id: form.value.location_id, quantity: form.value.quantity }] });
    if (kind.value === 'returnInspect' && selectedReturn.value) selectedReturn.value = await inspectCustomerReturnApi(selectedReturn.value.id, form.value);
    if (kind.value === 'returnResolve' && selectedReturn.value) selectedReturn.value = await resolveCustomerReturnApi(selectedReturn.value.id, form.value);
    if (kind.value === 'afterSales' && selectedReturn.value) selectedAfterSales.value = await createAfterSalesOrderApi(selectedReturn.value.id, form.value);
    if (kind.value === 'item') await createInspectionItemApi(form.value);
    if (kind.value === 'sampling') await createSamplingPlanApi(form.value);
    if (kind.value === 'template') await createInspectionTemplateApi(form.value);
    if (kind.value === 'standard' && selectedTemplate.value) await createInspectionStandardApi(selectedTemplate.value.id, form.value);
    if (kind.value === 'results' && selectedInspection.value) {
      const { standards: _standards, ...payload } = form.value;
      resultLines.value = await submitInspectionResultsApi(selectedInspection.value.id, payload);
    }
    visible.value = false;
    message.success('保存成功');
    await load();
    if (selectedNcr.value) await selectNcr(selectedNcr.value);
    if (selectedTemplate.value) await selectTemplate(selectedTemplate.value);
    if (selectedCapa.value) await selectCapa(selectedCapa.value);
    if (selectedReturn.value) {
      const fresh = customerReturns.value.find((item) => item.id === selectedReturn.value?.id);
      if (fresh) selectedReturn.value = fresh;
    }
    if (selectedAfterSales.value) {
      const fresh = afterSalesOrders.value.find((item) => item.id === selectedAfterSales.value?.id);
      if (fresh) selectedAfterSales.value = fresh;
    }
  } finally {
    saving.value = false;
  }
}

async function completeCapaAction(action: CapaAction) {
  if (!selectedCapa.value) return;
  await setCapaActionStatusApi(selectedCapa.value.id, action.id, { status: 'COMPLETED', evidence: action.evidence });
  message.success('整改措施已完成');
  await selectCapa(selectedCapa.value);
  await load();
}

async function closeCapa() {
  if (!selectedCapa.value) return;
  selectedCapa.value = await closeCapaApi(selectedCapa.value.id);
  message.success('CAPA 已关闭');
  await selectCapa(selectedCapa.value);
  await load();
}

async function execute(row: Disposition) {
  await executeDispositionApi(row.id);
  message.success($t('quality.executed'));
  if (selectedNcr.value) await selectNcr(selectedNcr.value);
  await load();
}

async function closeNcr() {
  if (!selectedNcr.value) return;
  selectedNcr.value = await closeNcrApi(selectedNcr.value.id);
  message.success($t('quality.closed'));
  await load();
}

async function toggleItemStatus() {
  if (!selectedItem.value) return;
  selectedItem.value = await setInspectionItemStatusApi(selectedItem.value.id, selectedItem.value.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE');
  await load();
}

async function toggleSamplingStatus() {
  if (!selectedSampling.value) return;
  selectedSampling.value = await setSamplingPlanStatusApi(selectedSampling.value.id, selectedSampling.value.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE');
  await load();
}

async function toggleTemplateStatus() {
  if (!selectedTemplate.value) return;
  selectedTemplate.value = selectedTemplate.value.status === 'ACTIVE'
    ? await deactivateInspectionTemplateApi(selectedTemplate.value.id)
    : await activateInspectionTemplateApi(selectedTemplate.value.id);
  await load();
}

onMounted(async () => {
  await loadOptions();
  await load();
});
</script>

<template>
  <Page :title="$t('quality.menu')">
    <div class="flex h-full min-h-0 gap-4">
      <a-card class="min-w-0 flex-1" :bordered="false">
        <div class="mb-3 flex gap-2">
          <a-button v-if="tab === 'inspections'" type="primary" @click="open('inspection')">{{ $t('quality.createInspection') }}</a-button>
          <a-button v-if="tab === 'items'" type="primary" @click="open('item')">新建检验项目</a-button>
          <a-button v-if="tab === 'sampling'" type="primary" @click="open('sampling')">新建抽样方案</a-button>
          <a-button v-if="tab === 'templates'" type="primary" @click="open('template')">新建检验模板</a-button>
          <a-button v-if="tab === 'rma'" type="primary" @click="open('complaint')">登记客户投诉</a-button>
          <a-button v-if="tab === 'rma'" @click="open('return')">创建退货 RMA</a-button>
          <a-button v-if="tab === 'afterSales'" @click="load">刷新售后执行单</a-button>
          <a-button @click="load">{{ $t('quality.refresh') }}</a-button>
        </div>
        <a-tabs v-model:active-key="tab">
          <a-tab-pane key="operation" tab="运营驾驶舱">
            <div v-if="dashboard" class="grid grid-cols-2 gap-3 md:grid-cols-4">
              <a-statistic title="NCR 超期" :value="dashboard.overdue_counts.NCR || 0" />
              <a-statistic title="CAPA 超期" :value="dashboard.overdue_counts.CAPA || 0" />
              <a-statistic title="RMA 超期" :value="dashboard.overdue_counts.RMA || 0" />
              <a-statistic title="售后超期" :value="dashboard.overdue_counts.AFTER_SALES || 0" />
              <a-statistic title="开放告警" :value="dashboard.open_alerts" />
              <a-statistic title="责任人待办" :value="dashboard.owner_todo_count" />
              <a-statistic title="库存事务" :value="dashboard.inventory_impact.transaction_count" />
              <a-statistic title="库存绝对影响" :value="dashboard.inventory_impact.absolute_quantity" />
            </div>
            <a-divider>重复问题 Top</a-divider>
            <a-table :data-source="dashboard?.repeated_defects || []" row-key="key" size="small" :pagination="false">
              <a-table-column title="缺陷描述" data-index="key" /><a-table-column title="次数" data-index="count" />
            </a-table>
            <a-divider>SLA 告警与升级待办</a-divider>
            <a-table :data-source="slaAlerts" row-key="id" size="small" :pagination="{ pageSize: 8 }">
              <a-table-column title="对象" data-index="entity_type" /><a-table-column title="编号" data-index="alert_no" /><a-table-column title="状态" data-index="status" /><a-table-column title="截止" data-index="due_at" /><a-table-column title="升级" data-index="escalation_level" />
            </a-table>
            <div v-for="alert in slaAlerts" :key="`alert-actions-${alert.id}`" class="mt-2 flex gap-2">
              <a-button size="small" @click="drillAlert(alert)">{{ alert.alert_no }} 下钻</a-button>
              <a-button v-if="alert.status !== 'ACKNOWLEDGED' && alert.status !== 'CLOSED'" size="small" @click="updateAlert(alert, 'ack')">确认</a-button>
              <a-button v-if="alert.status !== 'CLOSED'" size="small" @click="updateAlert(alert, 'escalate')">升级</a-button>
              <a-button v-if="alert.status !== 'CLOSED'" size="small" type="primary" @click="updateAlert(alert, 'close')">关闭</a-button>
            </div>
          </a-tab-pane>
          <a-tab-pane key="inspections" :tab="$t('quality.inspections')">
            <a-table :loading="loading" :data-source="inspections" row-key="id" @row="(row: Inspection) => ({ onClick: () => selectInspection(row) })">
              <a-table-column :title="$t('quality.inspectionNo')" data-index="inspection_no" />
              <a-table-column :title="$t('quality.type')" data-index="inspection_type" />
              <a-table-column :title="$t('quality.sample')" data-index="sample_quantity" />
              <a-table-column :title="$t('quality.result')" data-index="result" />
              <a-table-column :title="$t('quality.status')" data-index="status" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="ncrs" :tab="$t('quality.ncrs')">
            <a-table :loading="loading" :data-source="ncrs" row-key="id" @row="(row: Ncr) => ({ onClick: () => selectNcr(row) })">
              <a-table-column :title="$t('quality.ncrNo')" data-index="ncr_no" />
              <a-table-column :title="$t('quality.severity')" data-index="severity" />
              <a-table-column :title="$t('quality.quantity')" data-index="nonconforming_quantity" />
              <a-table-column :title="$t('quality.status')" data-index="status" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="items" tab="检验项目">
            <a-table :data-source="inspectionItems" row-key="id" @row="(row: InspectionItem) => ({ onClick: () => selectedItem = row })">
              <a-table-column title="项目编码" data-index="item_code" />
              <a-table-column title="项目名称" data-index="item_name" />
              <a-table-column title="值类型" data-index="value_type" />
              <a-table-column title="状态" data-index="status" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="sampling" tab="抽样方案">
            <a-table :data-source="samplingPlans" row-key="id" @row="(row: SamplingPlan) => ({ onClick: () => selectedSampling = row })">
              <a-table-column title="方案编码" data-index="plan_code" />
              <a-table-column title="方案名称" data-index="plan_name" />
              <a-table-column title="样本数" data-index="sample_size" />
              <a-table-column title="接收数" data-index="acceptance_number" />
              <a-table-column title="状态" data-index="status" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="templates" tab="检验模板">
            <a-table :data-source="templates" row-key="id" @row="(row: InspectionTemplate) => ({ onClick: () => selectTemplate(row) })">
              <a-table-column title="模板编码" data-index="template_code" />
              <a-table-column title="模板名称" data-index="template_name" />
              <a-table-column title="版本" data-index="template_version" />
              <a-table-column title="检验类型" data-index="inspection_type" />
              <a-table-column title="状态" data-index="status" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="rework" tab="返工工作台">
            <a-table :loading="loading" :data-source="reworkOrders" row-key="id" :pagination="{ pageSize: 20 }" @row="(row: ReworkOrder) => ({ onClick: () => selectRework(row) })">
              <a-table-column title="返工单号" data-index="rework_no" />
              <a-table-column title="返工数量" data-index="quantity" />
              <a-table-column title="生产工单 ID" data-index="production_work_order_id" />
              <a-table-column title="状态" data-index="status" />
              <a-table-column title="复检 ID" data-index="reinspection_id" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="capas" tab="CAPA / 8D">
            <a-table :loading="loading" :data-source="capas" row-key="id" :pagination="{ pageSize: 20 }" @row="(row: Capa) => ({ onClick: () => selectCapa(row) })">
              <a-table-column title="CAPA 编号" data-index="capa_no" />
              <a-table-column title="NCR ID" data-index="ncr_id" />
              <a-table-column title="状态" data-index="status" />
              <a-table-column title="责任人" data-index="owner_id" />
              <a-table-column title="截止时间" data-index="due_at" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="rma" tab="客户投诉 / RMA">
            <a-table :loading="loading" :data-source="customerReturns" row-key="id" :pagination="{ pageSize: 20 }" @row="(row: CustomerReturn) => ({ onClick: () => selectReturn(row) })">
              <a-table-column title="RMA 编号" data-index="return_no" />
              <a-table-column title="投诉 ID" data-index="complaint_id" />
              <a-table-column title="NCR ID" data-index="ncr_id" />
              <a-table-column title="状态" data-index="status" />
            </a-table>
            <a-divider>未转 RMA 的投诉</a-divider>
            <a-table :data-source="complaints.filter((item) => !item.rma_id)" row-key="id" size="small" :pagination="false">
              <a-table-column title="投诉编号" data-index="complaint_no" />
              <a-table-column title="客户" data-index="customer_name_snapshot" />
              <a-table-column title="标题" data-index="title" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="afterSales" tab="售后执行">
            <a-table :loading="loading" :data-source="afterSalesOrders" row-key="id" :pagination="{ pageSize: 20 }" @row="(row: AfterSalesOrder) => ({ onClick: () => selectAfterSales(row) })">
              <a-table-column title="执行单号" data-index="execution_no" /><a-table-column title="RMA ID" data-index="return_id" /><a-table-column title="类型" data-index="resolution_type" /><a-table-column title="状态" data-index="status" /><a-table-column title="库存流水" data-index="stock_transaction_id" />
            </a-table>
          </a-tab-pane>
        </a-tabs>
      </a-card>

      <a-card class="w-[520px] shrink-0" :bordered="false">
        <template v-if="tab === 'operation'">
          <a-empty v-if="!dashboard" />
          <template v-else>
            <a-descriptions :column="1" size="small">
              <a-descriptions-item label="NCR 平均关闭时长">{{ dashboard.average_close_hours.NCR || 0 }} 小时</a-descriptions-item>
              <a-descriptions-item label="CAPA 平均关闭时长">{{ dashboard.average_close_hours.CAPA || 0 }} 小时</a-descriptions-item>
              <a-descriptions-item label="投诉平均关闭时长">{{ dashboard.average_close_hours.COMPLAINT || 0 }} 小时</a-descriptions-item>
              <a-descriptions-item label="RMA 平均关闭时长">{{ dashboard.average_close_hours.RMA || 0 }} 小时</a-descriptions-item>
              <a-descriptions-item label="库存净变动">{{ dashboard.inventory_impact.quantity_delta }}</a-descriptions-item>
            </a-descriptions>
          </template>
        </template>
        <template v-else-if="tab === 'inspections'">
          <a-empty v-if="!selectedInspection" />
          <template v-else>
            <a-descriptions :column="1">
              <a-descriptions-item :label="$t('quality.inspectionNo')">{{ selectedInspection.inspection_no }}</a-descriptions-item>
              <a-descriptions-item :label="$t('quality.status')">{{ selectedInspection.status }}</a-descriptions-item>
              <a-descriptions-item :label="$t('quality.result')">{{ selectedInspection.result || '-' }}</a-descriptions-item>
            </a-descriptions>
            <div class="my-3 flex gap-2">
              <a-button v-if="selectedInspection.status === 'PENDING'" @click="open('results')">录入检验结果</a-button>
              <a-button v-if="selectedInspection.status === 'PENDING'" type="primary" @click="open('complete')">{{ $t('quality.complete') }}</a-button>
              <a-button v-if="selectedInspection.status === 'COMPLETED' && selectedInspection.result !== 'PASS'" @click="open('ncr')">{{ $t('quality.createNcr') }}</a-button>
            </div>
            <a-table :data-source="resultLines" row-key="id" size="small" :pagination="false">
              <a-table-column title="检验项目" data-index="item_name_snapshot" />
              <a-table-column title="类型" data-index="value_type_snapshot" />
              <a-table-column title="合格" data-index="is_qualified" />
            </a-table>
          </template>
        </template>
        <template v-else-if="tab === 'ncrs'">
          <a-empty v-if="!selectedNcr" />
          <template v-else>
            <a-descriptions :column="1">
              <a-descriptions-item :label="$t('quality.ncrNo')">{{ selectedNcr.ncr_no }}</a-descriptions-item>
              <a-descriptions-item :label="$t('quality.defect')">{{ selectedNcr.defect_description }}</a-descriptions-item>
              <a-descriptions-item :label="$t('quality.status')">{{ selectedNcr.status }}</a-descriptions-item>
            </a-descriptions>
            <div class="my-3 flex gap-2">
              <a-button v-if="!['DISPOSED', 'CLOSED'].includes(selectedNcr.status)" type="primary" @click="open('disposition')">{{ $t('quality.createDisposition') }}</a-button>
              <a-button v-if="selectedNcr.status !== 'CLOSED' && !capas.some((item) => item.ncr_id === selectedNcr?.id)" @click="open('capa')">创建 CAPA / 8D</a-button>
              <a-button v-if="selectedNcr.status === 'DISPOSED'" @click="closeNcr">{{ $t('quality.close') }}</a-button>
            </div>
            <a-list :data-source="dispositions">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta :title="`${item.disposition_type} · ${item.quantity}`" :description="item.status" />
                  <template #actions><a-button v-if="item.status === 'APPROVED'" type="link" @click="execute(item)">{{ $t('quality.execute') }}</a-button></template>
                </a-list-item>
              </template>
            </a-list>
          </template>
        </template>
        <template v-else-if="tab === 'items'">
          <a-empty v-if="!selectedItem" />
          <template v-else><a-descriptions :column="1"><a-descriptions-item label="项目">{{ selectedItem.item_code }} · {{ selectedItem.item_name }}</a-descriptions-item><a-descriptions-item label="值类型">{{ selectedItem.value_type }}</a-descriptions-item><a-descriptions-item label="状态">{{ selectedItem.status }}</a-descriptions-item></a-descriptions><a-button class="mt-3" @click="toggleItemStatus">{{ selectedItem.status === 'ACTIVE' ? '停用' : '启用' }}</a-button></template>
        </template>
        <template v-else-if="tab === 'sampling'">
          <a-empty v-if="!selectedSampling" />
          <template v-else><a-descriptions :column="1"><a-descriptions-item label="方案">{{ selectedSampling.plan_code }} · {{ selectedSampling.plan_name }}</a-descriptions-item><a-descriptions-item label="抽样规则">样本 {{ selectedSampling.sample_size }}，接收 {{ selectedSampling.acceptance_number }}</a-descriptions-item><a-descriptions-item label="状态">{{ selectedSampling.status }}</a-descriptions-item></a-descriptions><a-button class="mt-3" @click="toggleSamplingStatus">{{ selectedSampling.status === 'ACTIVE' ? '停用' : '启用' }}</a-button></template>
        </template>
        <template v-else-if="tab === 'rework'">
          <a-empty v-if="!selectedRework" />
          <template v-else>
            <a-descriptions :column="1" size="small">
              <a-descriptions-item label="返工单号">{{ selectedRework.rework_no }}</a-descriptions-item>
              <a-descriptions-item label="NCR ID">{{ selectedRework.ncr_id }}</a-descriptions-item>
              <a-descriptions-item label="返工数量">{{ selectedRework.quantity }}</a-descriptions-item>
              <a-descriptions-item label="生产工单 ID">{{ selectedRework.production_work_order_id || '-' }}</a-descriptions-item>
              <a-descriptions-item label="复检 ID">{{ selectedRework.reinspection_id || '-' }}</a-descriptions-item>
              <a-descriptions-item label="状态"><a-tag>{{ selectedRework.status }}</a-tag></a-descriptions-item>
            </a-descriptions>
            <div class="my-3 flex flex-wrap gap-2">
              <a-button v-if="['PLANNED', 'AWAITING_RETEST'].includes(selectedRework.status) && !selectedRework.production_work_order_id" type="primary" @click="createReworkWorkOrder">创建生产工单</a-button>
              <a-button v-if="selectedRework.production_work_order_id" @click="openProduction">打开生产工单</a-button>
              <a-button v-if="selectedRework.production_work_order_id && ['PLANNED', 'AWAITING_RETEST'].includes(selectedRework.status)" type="primary" @click="startRework">开始返工</a-button>
              <a-button v-if="selectedRework.status === 'IN_PROGRESS'" type="primary" @click="completeRework">完成返工并生成复检</a-button>
              <a-button v-if="selectedRework.reinspection_id" @click="tab = 'inspections'">查看复检</a-button>
            </div>
            <a-alert v-if="selectedRework.status === 'IN_PROGRESS'" type="info" show-icon message="请先在生产模块完成报工，生产工单达到 COMPLETED 后再点击“完成返工并生成复检”。" />
            <a-alert v-if="selectedRework.status === 'AWAITING_RETEST'" type="warning" show-icon message="返工已完成，需在检验页完成 RETEST；PASS 后才会放行。" />
          </template>
        </template>
        <template v-else-if="tab === 'capas'">
          <a-empty v-if="!selectedCapa" />
          <template v-else>
            <a-descriptions :column="1" size="small">
              <a-descriptions-item label="CAPA 编号">{{ selectedCapa.capa_no }}</a-descriptions-item>
              <a-descriptions-item label="NCR ID">{{ selectedCapa.ncr_id }}</a-descriptions-item>
              <a-descriptions-item label="状态"><a-tag>{{ selectedCapa.status }}</a-tag></a-descriptions-item>
              <a-descriptions-item label="D2 问题描述">{{ selectedCapa.d2_problem_description || '-' }}</a-descriptions-item>
              <a-descriptions-item label="D4 根因">{{ selectedCapa.d4_root_cause || '-' }}</a-descriptions-item>
              <a-descriptions-item label="D5 纠正方案">{{ selectedCapa.d5_corrective_plan || '-' }}</a-descriptions-item>
            </a-descriptions>
            <div class="my-3 flex flex-wrap gap-2">
              <a-button v-if="!['CLOSED', 'CANCELLED'].includes(selectedCapa.status)" type="primary" @click="open('capaAction')">新增整改措施</a-button>
              <a-button v-if="!['CLOSED', 'CANCELLED'].includes(selectedCapa.status)" @click="open('capaVerify')">提交效果验证</a-button>
              <a-button v-if="selectedCapa.status === 'VERIFYING'" type="primary" @click="closeCapa">关闭 CAPA</a-button>
            </div>
            <a-divider>整改措施</a-divider>
            <a-list :data-source="capaActions" size="small">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta :title="`${item.action_type} · ${item.description}`" :description="`${item.action_no} · ${item.status}`" />
                  <template #actions><a-button v-if="['OPEN', 'IN_PROGRESS'].includes(item.status)" type="link" @click="completeCapaAction(item)">标记完成</a-button></template>
                </a-list-item>
              </template>
            </a-list>
            <a-divider>效果验证记录</a-divider>
            <a-list :data-source="capaVerifications" size="small">
              <template #renderItem="{ item }"><a-list-item><a-list-item-meta :title="item.result" :description="item.notes || '-'" /></a-list-item></template>
            </a-list>
          </template>
        </template>
        <template v-else-if="tab === 'rma'">
          <a-empty v-if="!selectedReturn" description="请选择 RMA" />
          <template v-else>
            <a-descriptions :column="1" size="small">
              <a-descriptions-item label="RMA 编号">{{ selectedReturn.return_no }}</a-descriptions-item>
              <a-descriptions-item label="投诉 ID">{{ selectedReturn.complaint_id }}</a-descriptions-item>
              <a-descriptions-item label="状态"><a-tag>{{ selectedReturn.status }}</a-tag></a-descriptions-item>
              <a-descriptions-item label="NCR ID">{{ selectedReturn.ncr_id || '-' }}</a-descriptions-item>
              <a-descriptions-item label="处理结果">{{ selectedReturn.resolution_type || '-' }}</a-descriptions-item>
            </a-descriptions>
            <div class="my-3 flex flex-wrap gap-2">
              <a-button v-if="selectedReturn.status === 'AUTHORIZED'" type="primary" @click="receiveReturn">接收退货</a-button>
              <a-button v-if="['RECEIVED', 'INSPECTED'].includes(selectedReturn.status) && !selectedReturn.lines[0]?.inspection_id" @click="inspectReturn">退货检验</a-button>
              <a-button v-if="selectedReturn.status === 'INSPECTED'" @click="resolveReturn">登记处理结果</a-button>
              <a-button v-if="selectedReturn.status === 'RESOLVED'" @click="open('afterSales')">创建售后执行单</a-button>
              <a-button v-if="selectedReturn.status === 'RESOLVED'" type="primary" @click="closeReturn">关闭 RMA</a-button>
            </div>
            <a-table :data-source="selectedReturn.lines" row-key="id" size="small" :pagination="false">
              <a-table-column title="行号" data-index="line_no" /><a-table-column title="物料 ID" data-index="material_id" /><a-table-column title="数量" data-index="quantity" /><a-table-column title="库存流水" data-index="stock_transaction_id" /><a-table-column title="检验" data-index="inspection_id" />
            </a-table>
          </template>
        </template>
        <template v-else-if="tab === 'afterSales'">
          <a-empty v-if="!selectedAfterSales" description="请选择售后执行单" />
          <template v-else>
            <a-descriptions :column="1" size="small"><a-descriptions-item label="执行单号">{{ selectedAfterSales.execution_no }}</a-descriptions-item><a-descriptions-item label="处理类型">{{ selectedAfterSales.resolution_type }}</a-descriptions-item><a-descriptions-item label="状态"><a-tag>{{ selectedAfterSales.status }}</a-tag></a-descriptions-item><a-descriptions-item label="库存流水">{{ selectedAfterSales.stock_transaction_id || '-' }}</a-descriptions-item></a-descriptions>
            <div class="my-3 flex flex-wrap gap-2"><a-button v-if="selectedAfterSales.status === 'DRAFT'" type="primary" @click="approveAfterSales">审批</a-button><a-button v-if="selectedAfterSales.status === 'APPROVED'" @click="startAfterSales">开始执行</a-button><a-button v-if="selectedAfterSales.status === 'IN_PROGRESS'" type="primary" @click="completeAfterSales">完成执行</a-button></div>
          </template>
        </template>
        <template v-else>
          <a-empty v-if="!selectedTemplate" />
          <template v-else>
            <a-descriptions :column="1"><a-descriptions-item label="模板">{{ selectedTemplate.template_code }} / {{ selectedTemplate.template_version }}</a-descriptions-item><a-descriptions-item label="状态">{{ selectedTemplate.status }}</a-descriptions-item></a-descriptions>
            <div class="my-3 flex gap-2"><a-button v-if="selectedTemplate.status === 'DRAFT'" type="primary" @click="open('standard')">添加标准</a-button><a-button @click="toggleTemplateStatus">{{ selectedTemplate.status === 'ACTIVE' ? '停用' : '生效' }}</a-button></div>
            <a-table :data-source="standards" row-key="id" size="small" :pagination="false"><a-table-column title="行号" data-index="line_no" /><a-table-column title="检验项目 ID" data-index="inspection_item_id" /><a-table-column title="下限" data-index="lower_limit" /><a-table-column title="上限" data-index="upper_limit" /></a-table>
          </template>
        </template>
      </a-card>
    </div>

    <a-modal v-model:open="visible" :title="dialogTitle" :confirm-loading="saving" width="680px" @ok="submit">
      <a-form layout="vertical" :model="form">
        <template v-if="kind === 'afterSales'">
          <a-form-item label="处理类型"><a-input v-model:value="form.resolution_type" disabled /></a-form-item>
          <a-form-item v-if="form.resolution_type === 'REPLACEMENT'" label="替换物料 ID" required><a-input-number v-model:value="form.replacement_material_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item v-if="form.resolution_type === 'REPLACEMENT'" label="替换批次 ID"><a-input-number v-model:value="form.replacement_lot_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item label="执行说明"><a-textarea v-model:value="form.execution_notes" /></a-form-item>
        </template>
        <template v-else-if="kind === 'complaint'">
          <a-form-item label="客户 ID" required><a-input-number v-model:value="form.customer_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item label="发货单 ID"><a-input-number v-model:value="form.shipment_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item label="物料 ID"><a-input-number v-model:value="form.material_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item label="批次 ID"><a-input-number v-model:value="form.lot_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item label="投诉标题" required><a-input v-model:value="form.title" /></a-form-item>
          <a-form-item label="投诉描述" required><a-textarea v-model:value="form.description" /></a-form-item>
        </template>
        <template v-else-if="kind === 'return'">
          <a-form-item label="投诉 ID" required><a-input-number v-model:value="form.complaint_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item label="发货行 ID"><a-input-number v-model:value="form.shipment_line_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item label="物料 ID" required><a-input-number v-model:value="form.material_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item label="批次 ID"><a-input-number v-model:value="form.lot_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item label="仓库" required><a-select v-model:value="form.warehouse_id" :options="warehouses.map((item) => ({ label: `${item.warehouse_code} · ${item.warehouse_name}`, value: item.id }))" @change="form.location_id = undefined" /></a-form-item>
          <a-form-item label="库位" required><a-select v-model:value="form.location_id" :options="locationOptions(form.warehouse_id)" /></a-form-item>
          <a-form-item label="退货数量" required><a-input-number v-model:value="form.quantity" class="w-full" :min="0.000001" /></a-form-item>
        </template>
        <template v-else-if="kind === 'returnInspect'">
          <a-form-item label="退货明细 ID"><a-input-number v-model:value="form.line_id" class="w-full" disabled /></a-form-item>
          <a-form-item label="合格数量"><a-input-number v-model:value="form.accepted_quantity" class="w-full" :min="0" /></a-form-item>
          <a-form-item label="拒收数量"><a-input-number v-model:value="form.rejected_quantity" class="w-full" :min="0" /></a-form-item>
          <a-form-item label="检验结果"><a-select v-model:value="form.result" :options="['PASS', 'FAIL', 'PARTIAL'].map((value) => ({ label: value, value }))" /></a-form-item>
          <a-form-item label="结论"><a-textarea v-model:value="form.conclusion" /></a-form-item>
        </template>
        <template v-else-if="kind === 'returnResolve'">
          <a-form-item label="客户处理结果" required><a-select v-model:value="form.resolution_type" :options="['REFUND', 'REPLACEMENT', 'REPAIR', 'SCRAP', 'NO_DEFECT'].map((value) => ({ label: value, value }))" /></a-form-item>
          <a-form-item label="处理说明"><a-textarea v-model:value="form.resolution_notes" /></a-form-item>
        </template>
        <template v-else-if="kind === 'capa'">
          <a-form-item label="NCR ID"><a-input-number v-model:value="form.ncr_id" class="w-full" disabled /></a-form-item>
          <a-form-item label="D2 问题描述" required><a-textarea v-model:value="form.d2_problem_description" /></a-form-item>
          <a-form-item label="D3 临时遏制措施"><a-textarea v-model:value="form.d3_containment_summary" /></a-form-item>
          <a-form-item label="D4 根本原因" required><a-textarea v-model:value="form.d4_root_cause" /></a-form-item>
          <a-form-item label="D5 永久纠正方案" required><a-textarea v-model:value="form.d5_corrective_plan" /></a-form-item>
          <a-form-item label="D7 预防再发生"><a-textarea v-model:value="form.d7_prevention_summary" /></a-form-item>
        </template>
        <template v-else-if="kind === 'capaAction'">
          <a-form-item label="措施类型" required><a-select v-model:value="form.action_type" :options="['CONTAINMENT', 'CORRECTIVE', 'PREVENTIVE'].map((value) => ({ label: value, value }))" /></a-form-item>
          <a-form-item label="措施描述" required><a-textarea v-model:value="form.description" /></a-form-item>
        </template>
        <template v-else-if="kind === 'capaVerify'">
          <a-form-item label="验证结果" required><a-select v-model:value="form.result" :options="['PASS', 'FAIL'].map((value) => ({ label: value, value }))" /></a-form-item>
          <a-form-item label="验证说明"><a-textarea v-model:value="form.notes" /></a-form-item>
        </template>
        <template v-else-if="kind === 'inspection'">
          <a-form-item :label="$t('quality.type')"><a-select v-model:value="form.inspection_type" :options="['INCOMING', 'PROCESS', 'FINAL', 'RETEST'].map((value) => ({ label: value, value }))" /></a-form-item>
          <a-form-item :label="$t('quality.material')"><a-select v-model:value="form.material_id" show-search :options="materials.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item>
          <a-form-item :label="$t('quality.lot')"><a-input-number v-model:value="form.lot_id" class="w-full" :min="1" /></a-form-item>
          <a-form-item :label="$t('quality.sample')"><a-input-number v-model:value="form.sample_quantity" class="w-full" :min="0.000001" /></a-form-item>
        </template>
        <template v-else-if="kind === 'complete'">
          <a-form-item :label="$t('quality.accepted')"><a-input-number v-model:value="form.accepted_quantity" class="w-full" :min="0" /></a-form-item>
          <a-form-item :label="$t('quality.rejected')"><a-input-number v-model:value="form.rejected_quantity" class="w-full" :min="0" /></a-form-item>
          <a-form-item :label="$t('quality.result')"><a-select v-model:value="form.result" :options="['PASS', 'FAIL', 'PARTIAL'].map((value) => ({ label: value, value }))" /></a-form-item>
          <a-form-item :label="$t('quality.conclusion')"><a-textarea v-model:value="form.conclusion" /></a-form-item>
        </template>
        <template v-else-if="kind === 'ncr'">
          <a-form-item :label="$t('quality.quantity')"><a-input-number v-model:value="form.nonconforming_quantity" class="w-full" :min="0.000001" /></a-form-item>
          <a-form-item :label="$t('quality.severity')"><a-select v-model:value="form.severity" :options="['MINOR', 'MAJOR', 'CRITICAL'].map((value) => ({ label: value, value }))" /></a-form-item>
          <a-form-item :label="$t('quality.defect')"><a-textarea v-model:value="form.defect_description" /></a-form-item>
        </template>
        <template v-else-if="kind === 'disposition'">
          <a-form-item :label="$t('quality.disposition')"><a-select v-model:value="form.disposition_type" :options="['USE_AS_IS', 'REWORK', 'RETURN_TO_SUPPLIER', 'SCRAP', 'REINSPECT'].map((value) => ({ label: value, value }))" /></a-form-item>
          <a-form-item :label="$t('quality.quantity')"><a-input-number v-model:value="form.quantity" class="w-full" :min="0.000001" /></a-form-item>
          <template v-if="['SCRAP', 'RETURN_TO_SUPPLIER'].includes(form.disposition_type)"><a-form-item :label="$t('quality.warehouse')"><a-select v-model:value="form.warehouse_id" :options="warehouses.map((item) => ({ label: `${item.warehouse_code} · ${item.warehouse_name}`, value: item.id }))" @change="form.location_id = undefined" /></a-form-item><a-form-item :label="$t('quality.location')"><a-select v-model:value="form.location_id" :options="locationOptions(form.warehouse_id)" /></a-form-item></template>
          <a-form-item :label="$t('quality.reason')"><a-textarea v-model:value="form.decision_reason" /></a-form-item>
        </template>
        <template v-else-if="kind === 'item'">
          <a-form-item label="项目编码" required><a-input v-model:value="form.item_code" /></a-form-item><a-form-item label="项目名称" required><a-input v-model:value="form.item_name" /></a-form-item><a-form-item label="值类型" required><a-select v-model:value="form.value_type" :options="['NUMERIC', 'BOOLEAN', 'TEXT'].map((value) => ({ label: value, value }))" /></a-form-item><a-form-item label="单位"><a-input v-model:value="form.unit_label" /></a-form-item>
        </template>
        <template v-else-if="kind === 'sampling'">
          <a-form-item label="方案编码" required><a-input v-model:value="form.plan_code" /></a-form-item><a-form-item label="方案名称" required><a-input v-model:value="form.plan_name" /></a-form-item><a-form-item label="样本数" required><a-input-number v-model:value="form.sample_size" class="w-full" :min="1" /></a-form-item><a-form-item label="接收数" required><a-input-number v-model:value="form.acceptance_number" class="w-full" :min="0" /></a-form-item>
        </template>
        <template v-else-if="kind === 'template'">
          <a-form-item label="模板编码" required><a-input v-model:value="form.template_code" /></a-form-item><a-form-item label="模板名称" required><a-input v-model:value="form.template_name" /></a-form-item><a-form-item label="物料" required><a-select v-model:value="form.material_id" show-search :options="materials.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" /></a-form-item><a-form-item label="版本" required><a-input v-model:value="form.template_version" /></a-form-item><a-form-item label="检验类型"><a-select v-model:value="form.inspection_type" :options="['INCOMING', 'PROCESS', 'FINAL', 'RETEST'].map((value) => ({ label: value, value }))" /></a-form-item><a-form-item label="抽样方案"><a-select v-model:value="form.sampling_plan_id" allow-clear :options="samplingPlans.filter((item) => item.status === 'ACTIVE').map((item) => ({ label: `${item.plan_code} · ${item.plan_name}`, value: item.id }))" /></a-form-item>
        </template>
        <template v-else-if="kind === 'standard'">
          <a-form-item label="行号" required><a-input-number v-model:value="form.line_no" class="w-full" :min="1" /></a-form-item><a-form-item label="检验项目" required><a-select v-model:value="form.inspection_item_id" :options="inspectionItems.filter((item) => item.status === 'ACTIVE').map((item) => ({ label: `${item.item_code} · ${item.item_name}`, value: item.id }))" /></a-form-item><a-form-item label="下限"><a-input-number v-model:value="form.lower_limit" class="w-full" /></a-form-item><a-form-item label="上限"><a-input-number v-model:value="form.upper_limit" class="w-full" /></a-form-item><a-form-item label="布尔期望值"><a-switch v-model:checked="form.expected_boolean" /></a-form-item><a-form-item label="文本期望值"><a-input v-model:value="form.expected_text" /></a-form-item><a-form-item label="必检"><a-switch v-model:checked="form.required" /></a-form-item>
        </template>
        <template v-else>
          <div v-for="(result, index) in form.results" :key="result.standard_id" class="mb-3 rounded border p-3">
            <div class="mb-2 font-medium">{{ inspectionItem(form.standards[index].inspection_item_id)?.item_name }}</div>
            <a-input-number v-if="inspectionItem(form.standards[index].inspection_item_id)?.value_type === 'NUMERIC'" v-model:value="result.numeric_value" class="w-full" />
            <a-switch v-else-if="inspectionItem(form.standards[index].inspection_item_id)?.value_type === 'BOOLEAN'" v-model:checked="result.boolean_value" />
            <a-input v-else v-model:value="result.text_value" />
          </div>
        </template>
      </a-form>
    </a-modal>
  </Page>
</template>
