<script lang="ts" setup>
import { onMounted, reactive, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import type { SupplierOption } from '../../purchasing/api';
import type {
  SupplierCorrectiveAction,
  SupplierQualityAssessment,
  SupplierQualityDashboard,
  SupplierQualityPolicy,
} from '../api';
import { getPurchasingSupplierOptionsApi } from '../../purchasing/api';
import {
  getSqmDashboardApi,
  getSupplierQualityAssessmentsApi,
  getSupplierQualityPoliciesApi,
  getSupplierScarsApi,
  issueSupplierScarApi,
  recalculateAllSupplierQualityApi,
  recalculateSupplierQualityApi,
  reinspectSupplierScarApi,
  respondSupplierScarApi,
  upsertSupplierQualityPolicyApi,
  verifySupplierScarApi,
} from '../api';

const loading = ref(false);
const dashboard = ref<SupplierQualityDashboard>();
const scars = ref<SupplierCorrectiveAction[]>([]);
const policies = ref<SupplierQualityPolicy[]>([]);
const assessments = ref<SupplierQualityAssessment[]>([]);
const suppliers = ref<SupplierOption[]>([]);
const selectedSupplierId = ref<number>();
const responseOpen = ref(false);
const selectedScar = ref<SupplierCorrectiveAction>();
const responseForm = reactive({
  containment_action: '',
  root_cause: '',
  corrective_action: '',
  preventive_action: '',
  response_evidence: '',
});
const policyForm = reactive({
  supplier_id: undefined as number | undefined,
  rolling_days: 180,
  minimum_inspections: 1,
  excellent_score: 95,
  qualified_score: 85,
  conditional_score: 70,
  quality_weight: 70,
  delivery_weight: 30,
  auto_apply: true,
  block_on_open_critical_scar: true,
  status: 'ACTIVE',
});

async function load() {
  loading.value = true;
  try {
    [dashboard.value, scars.value, policies.value, assessments.value, suppliers.value] = await Promise.all([
      getSqmDashboardApi(),
      getSupplierScarsApi(),
      getSupplierQualityPoliciesApi(),
      getSupplierQualityAssessmentsApi({ limit: 200 }),
      getPurchasingSupplierOptionsApi(),
    ]);
  } finally {
    loading.value = false;
  }
}

function supplierName(id: number) {
  const row = suppliers.value.find((item) => item.id === id);
  return row ? `${row.code} · ${row.name}` : `供应商 ${id}`;
}

async function issue(row: SupplierCorrectiveAction) {
  await issueSupplierScarApi(row.id);
  message.success('SCAR 已发布，整改时限默认为 14 天');
  await load();
}

function openResponse(row: SupplierCorrectiveAction) {
  selectedScar.value = row;
  Object.assign(responseForm, {
    containment_action: row.containment_action ?? '',
    root_cause: row.root_cause ?? '',
    corrective_action: row.corrective_action ?? '',
    preventive_action: row.preventive_action ?? '',
    response_evidence: row.response_evidence ?? '',
  });
  responseOpen.value = true;
}

async function submitResponse() {
  if (!selectedScar.value) return;
  if (!responseForm.containment_action || !responseForm.root_cause || !responseForm.corrective_action || !responseForm.preventive_action) {
    return message.warning('请完整填写遏制、根因、纠正和预防措施');
  }
  await respondSupplierScarApi(selectedScar.value.id, responseForm);
  responseOpen.value = false;
  message.success('供应商整改回复已提交');
  await load();
}

async function reinspect(row: SupplierCorrectiveAction) {
  const result = await reinspectSupplierScarApi(row.id);
  message.success(`复验单已创建：${result.reinspection_id}，请在质量检验页完成后再验证`);
  await load();
}

async function verify(row: SupplierCorrectiveAction) {
  await verifySupplierScarApi(row.id, { verification_notes: '整改复验结果已确认' });
  message.success('SCAR 验证完成，供应商评分已自动重算');
  await load();
}

async function recalculate() {
  if (!selectedSupplierId.value) return message.warning('请选择供应商');
  const result = await recalculateSupplierQualityApi(selectedSupplierId.value);
  message.success(`评分完成：${result.grade} 级 / ${result.procurement_decision}`);
  await load();
}

async function recalculateAll() {
  const rows = await recalculateAllSupplierQualityApi();
  message.success(`已重算 ${rows.length} 家供应商`);
  await load();
}

async function savePolicy() {
  if (!policyForm.supplier_id) return message.warning('请选择供应商');
  await upsertSupplierQualityPolicyApi(policyForm.supplier_id, policyForm);
  message.success('供应商评分与采购策略已保存');
  await load();
}

function decisionColor(decision: string) {
  return decision === 'SUSPENDED' ? 'red' : decision === 'CONDITIONAL' ? 'orange' : decision === 'APPROVED' ? 'green' : 'default';
}

onMounted(load);
</script>

<template>
  <Page title="供应商质量管理 SQM" auto-content-height>
    <div v-if="dashboard" class="mb-4 grid grid-cols-5 gap-3">
      <a-card size="small" title="待整改 SCAR">{{ dashboard.open_scar_count }}</a-card>
      <a-card size="small" title="整改逾期">{{ dashboard.overdue_scar_count }}</a-card>
      <a-card size="small" title="等待复验">{{ dashboard.retest_pending_count }}</a-card>
      <a-card size="small" title="条件采购">{{ dashboard.conditional_supplier_count }}</a-card>
      <a-card size="small" title="暂停采购">{{ dashboard.suspended_supplier_count }}</a-card>
    </div>

    <a-tabs>
      <a-tab-pane key="scar" tab="供应商整改 SCAR">
        <a-table :data-source="scars" :loading="loading" row-key="id" size="small" :pagination="{ pageSize: 15 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'supplier'">{{ supplierName(record.supplier_id) }}</template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button v-if="record.status === 'DRAFT'" type="link" @click="issue(record)">发布</a-button>
                <a-button v-if="['ISSUED', 'REJECTED'].includes(record.status)" type="link" @click="openResponse(record)">录入整改</a-button>
                <a-button v-if="record.status === 'RESPONDED'" type="link" @click="reinspect(record)">发起复验</a-button>
                <a-button v-if="record.status === 'RETEST_PENDING'" type="link" @click="verify(record)">验证关闭</a-button>
              </a-space>
            </template>
          </template>
          <a-table-column title="SCAR 单号" data-index="scar_no" />
          <a-table-column title="供应商" key="supplier" />
          <a-table-column title="NCR ID" data-index="ncr_id" />
          <a-table-column title="物料 ID" data-index="material_id" />
          <a-table-column title="不合格数量" data-index="nonconforming_quantity" />
          <a-table-column title="严重度" data-index="severity" />
          <a-table-column title="状态" data-index="status" />
          <a-table-column title="整改期限" data-index="due_at" />
          <a-table-column title="复验单 ID" data-index="reinspection_id" />
          <a-table-column title="操作" key="action" />
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="score" tab="评分与采购决策">
        <a-card :bordered="false" class="mb-4">
          <a-space wrap>
            <a-select v-model:value="selectedSupplierId" show-search placeholder="选择供应商" style="width: 280px" :options="suppliers.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" />
            <a-button type="primary" @click="recalculate">重算当前供应商</a-button>
            <a-button @click="recalculateAll">重算全部</a-button>
          </a-space>
        </a-card>
        <a-table :data-source="assessments" row-key="id" size="small" :pagination="{ pageSize: 15 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'supplier'">{{ supplierName(record.supplier_id) }}</template>
            <template v-else-if="column.key === 'decision'"><a-tag :color="decisionColor(record.procurement_decision)">{{ record.procurement_decision }}</a-tag></template>
          </template>
          <a-table-column title="评分单" data-index="assessment_no" />
          <a-table-column title="供应商" key="supplier" />
          <a-table-column title="等级" data-index="grade" />
          <a-table-column title="综合分" data-index="overall_score" />
          <a-table-column title="IQC 通过率" data-index="pass_rate" />
          <a-table-column title="数量合格率" data-index="acceptance_rate" />
          <a-table-column title="整改得分" data-index="corrective_score" />
          <a-table-column title="OTIF 得分" data-index="delivery_score" />
          <a-table-column title="采购决策" key="decision" />
          <a-table-column title="评分时间" data-index="assessed_at" />
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="policy" tab="评分策略">
        <a-card title="供应商评分策略" :bordered="false" class="mb-4">
          <a-space wrap>
            <a-select v-model:value="policyForm.supplier_id" show-search placeholder="选择供应商" style="width: 260px" :options="suppliers.map((item) => ({ label: `${item.code} · ${item.name}`, value: item.id }))" />
            <span>滚动天数</span><a-input-number v-model:value="policyForm.rolling_days" :min="30" />
            <span>最少 IQC</span><a-input-number v-model:value="policyForm.minimum_inspections" :min="1" />
            <span>A 级</span><a-input-number v-model:value="policyForm.excellent_score" :min="0" :max="100" />
            <span>B 级</span><a-input-number v-model:value="policyForm.qualified_score" :min="0" :max="100" />
            <span>C 级</span><a-input-number v-model:value="policyForm.conditional_score" :min="0" :max="100" />
            <span>质量权重</span><a-input-number v-model:value="policyForm.quality_weight" :min="0" :max="100" />
            <span>交付权重</span><a-input-number v-model:value="policyForm.delivery_weight" :min="0" :max="100" />
            <a-checkbox v-model:checked="policyForm.auto_apply">自动联动采购</a-checkbox>
            <a-checkbox v-model:checked="policyForm.block_on_open_critical_scar">严重 SCAR 暂停采购</a-checkbox>
            <a-button type="primary" @click="savePolicy">保存</a-button>
          </a-space>
        </a-card>
        <a-table :data-source="policies" row-key="id" size="small">
          <a-table-column title="供应商" data-index="supplier_id" />
          <a-table-column title="滚动天数" data-index="rolling_days" />
          <a-table-column title="A/B/C 阈值" key="threshold">
            <!-- @vue-ignore antdv-next column slot typing omits the runtime record payload -->
            <template #default="{ record }">{{ record.excellent_score }} / {{ record.qualified_score }} / {{ record.conditional_score }}</template>
          </a-table-column>
          <a-table-column title="质量/交付权重" key="weight">
            <!-- @vue-ignore antdv-next column slot typing omits the runtime record payload -->
            <template #default="{ record }">{{ record.quality_weight }} / {{ record.delivery_weight }}</template>
          </a-table-column>
          <a-table-column title="自动应用" data-index="auto_apply" />
          <a-table-column title="状态" data-index="status" />
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="responseOpen" title="供应商整改回复" @ok="submitResponse">
      <a-form layout="vertical">
        <a-form-item label="临时遏制措施"><a-textarea v-model:value="responseForm.containment_action" :rows="2" /></a-form-item>
        <a-form-item label="根因分析"><a-textarea v-model:value="responseForm.root_cause" :rows="2" /></a-form-item>
        <a-form-item label="纠正措施"><a-textarea v-model:value="responseForm.corrective_action" :rows="2" /></a-form-item>
        <a-form-item label="预防再发措施"><a-textarea v-model:value="responseForm.preventive_action" :rows="2" /></a-form-item>
        <a-form-item label="证据说明"><a-textarea v-model:value="responseForm.response_evidence" :rows="2" /></a-form-item>
      </a-form>
    </a-modal>
  </Page>
</template>
