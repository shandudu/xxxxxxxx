<script lang="ts" setup>
import { onMounted, reactive, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import type { MaterialOption } from '../../material/api';
import type { SupplierOption } from '../../purchasing/api';
import type {
  QualificationApplication,
  SupplierAudit,
  SupplierAvlEntry,
  SupplierLifecycleDashboard,
  SupplierPeriodicReview,
  SupplierPpap,
  SupplierSampleApproval,
} from '../api';
import { getMaterialOptionsApi } from '../../material/api';
import { getPurchasingSupplierOptionsApi } from '../../purchasing/api';
import {
  approveQualificationApplicationApi,
  completeQualificationAuditApi,
  completeSupplierPeriodicReviewApi,
  createQualificationApplicationApi,
  createQualificationAuditApi,
  createSampleApprovalApi,
  createSupplierPeriodicReviewApi,
  createSupplierPpapApi,
  decideSampleApprovalApi,
  decideSupplierPpapApi,
  generateDueSupplierReviewsApi,
  getQualificationApplicationsApi,
  getQualificationAuditsApi,
  getSampleApprovalsApi,
  getSupplierAvlApi,
  getSupplierLifecycleDashboardApi,
  getSupplierPeriodicReviewsApi,
  getSupplierPpapsApi,
  rejectQualificationApplicationApi,
  submitQualificationApplicationApi,
  submitSupplierPpapApi,
} from '../api';

const loading = ref(false);
const dashboard = ref<SupplierLifecycleDashboard>();
const applications = ref<QualificationApplication[]>([]);
const audits = ref<SupplierAudit[]>([]);
const samples = ref<SupplierSampleApproval[]>([]);
const ppaps = ref<SupplierPpap[]>([]);
const avl = ref<SupplierAvlEntry[]>([]);
const reviews = ref<SupplierPeriodicReview[]>([]);
const suppliers = ref<SupplierOption[]>([]);
const materials = ref<MaterialOption[]>([]);

const applicationForm = reactive({ supplier_id: undefined as number | undefined, requested_scope: '', certificate_reference: '' });
const auditForm = reactive({ application_id: undefined as number | undefined, audit_type: 'INITIAL', score: 90, findings: '审厂要求符合' });
const sampleForm = reactive({ application_id: undefined as number | undefined, material_id: undefined as number | undefined, submitted_quantity: 1 });
const ppapForm = reactive({ application_id: undefined as number | undefined, material_id: undefined as number | undefined, sample_approval_id: undefined as number | undefined, level: 3, version: '1.0', document_reference: '' });

const applicationOptions = () => applications.value
  .filter((row) => ['SUBMITTED', 'UNDER_REVIEW'].includes(row.status))
  .map((row) => ({ label: `${row.application_no} · ${supplierName(row.supplier_id)}`, value: row.id }));
const supplierOptions = () => suppliers.value.map((row) => ({ label: `${row.code} · ${row.name}`, value: row.id }));
const materialOptions = () => materials.value.map((row) => ({ label: `${row.code} · ${row.name}`, value: row.id }));
const approvedSampleOptions = () => samples.value
  .filter((row) => row.status === 'APPROVED' && (!ppapForm.material_id || row.material_id === ppapForm.material_id))
  .map((row) => ({ label: `${row.sample_no} · 物料 ${row.material_id}`, value: row.id }));

function supplierName(id: number) {
  const row = suppliers.value.find((item) => item.id === id);
  return row ? `${row.code} · ${row.name}` : `供应商 ${id}`;
}

function materialName(id: number) {
  const row = materials.value.find((item) => item.id === id);
  return row ? `${row.code} · ${row.name}` : `物料 ${id}`;
}

function statusColor(status: string) {
  if (['APPROVED', 'COMPLETED', 'PASS', 'CONTINUE'].includes(status)) return 'green';
  if (['CONDITIONAL', 'PENDING', 'PLANNED', 'SUBMITTED', 'UNDER_REVIEW'].includes(status)) return 'orange';
  if (['REJECTED', 'FAIL', 'REMOVED', 'SUSPENDED'].includes(status)) return 'red';
  return 'default';
}

async function load() {
  loading.value = true;
  try {
    [dashboard.value, applications.value, audits.value, samples.value, ppaps.value, avl.value, reviews.value, suppliers.value, materials.value] = await Promise.all([
      getSupplierLifecycleDashboardApi(),
      getQualificationApplicationsApi(),
      getQualificationAuditsApi(),
      getSampleApprovalsApi(),
      getSupplierPpapsApi(),
      getSupplierAvlApi(),
      getSupplierPeriodicReviewsApi(),
      getPurchasingSupplierOptionsApi(),
      getMaterialOptionsApi(),
    ]);
  } finally {
    loading.value = false;
  }
}

async function createApplication() {
  if (!applicationForm.supplier_id || !applicationForm.requested_scope || !applicationForm.certificate_reference) {
    return message.warning('请选择供应商并填写准入范围和资质文件引用');
  }
  await createQualificationApplicationApi({
    supplier_id: applicationForm.supplier_id,
    requested_scope: applicationForm.requested_scope,
    certificate_manifest: { reference: applicationForm.certificate_reference },
  });
  message.success('准入申请已创建，供应商采购资格暂时冻结');
  Object.assign(applicationForm, { supplier_id: undefined, requested_scope: '', certificate_reference: '' });
  await load();
}

async function submitApplication(row: QualificationApplication) {
  await submitQualificationApplicationApi(row.id);
  message.success('准入申请已提交');
  await load();
}

async function approveApplication(row: QualificationApplication) {
  await approveQualificationApplicationApi(row.id, { decision_notes: '审厂、样品和 PPAP 均符合准入要求', valid_days: 365, qualification_level: 'STANDARD' });
  message.success('准入已批准，物料级 AVL 已生成');
  await load();
}

async function rejectApplication(row: QualificationApplication) {
  await rejectQualificationApplicationApi(row.id, { decision_notes: '当前准入证据不满足要求' });
  message.success('准入申请已拒绝');
  await load();
}

async function createAudit() {
  if (!auditForm.application_id) return message.warning('请选择准入申请');
  await createQualificationAuditApi(auditForm.application_id, {
    audit_type: auditForm.audit_type,
    planned_at: new Date().toISOString(),
  });
  message.success('审厂任务已创建');
  await load();
}

async function completeAudit(row: SupplierAudit, passed = true) {
  await completeQualificationAuditApi(row.id, {
    score: passed ? auditForm.score : 50,
    result: passed ? 'PASS' : 'FAIL',
    findings: auditForm.findings,
    evidence_manifest: { source: 'SQE audit workbench' },
  });
  message.success('审厂结论已记录');
  await load();
}

async function createSample() {
  if (!sampleForm.application_id || !sampleForm.material_id) return message.warning('请选择准入申请和物料');
  await createSampleApprovalApi(sampleForm.application_id, {
    material_id: sampleForm.material_id,
    submitted_quantity: sampleForm.submitted_quantity,
    evidence_manifest: { source: 'sample submission' },
  });
  message.success('送样轮次已创建');
  await load();
}

async function decideSample(row: SupplierSampleApproval, approved: boolean) {
  await decideSampleApprovalApi(row.id, { approved, decision_notes: approved ? '样品验证符合要求' : '样品验证不合格' });
  message.success('样品结论已记录');
  await load();
}

async function createPpap() {
  if (!ppapForm.application_id || !ppapForm.material_id || !ppapForm.sample_approval_id || !ppapForm.document_reference) {
    return message.warning('请完整选择申请、物料、已批准样品并填写 PPAP 文件引用');
  }
  await createSupplierPpapApi(ppapForm.application_id, {
    material_id: ppapForm.material_id,
    sample_approval_id: ppapForm.sample_approval_id,
    level: ppapForm.level,
    version: ppapForm.version,
    document_manifest: { reference: ppapForm.document_reference, apqp: true },
  });
  message.success('PPAP 文件包已创建');
  await load();
}

async function submitPpap(row: SupplierPpap) {
  await submitSupplierPpapApi(row.id);
  message.success('PPAP 已提交审批');
  await load();
}

async function decidePpap(row: SupplierPpap, approved: boolean) {
  await decideSupplierPpapApi(row.id, { approved, decision_notes: approved ? 'PPAP 文件与样品证据符合要求' : 'PPAP 文件需补充', valid_days: 365 });
  message.success('PPAP 审批结论已记录');
  await load();
}

async function createReview(row: SupplierAvlEntry) {
  await createSupplierPeriodicReviewApi(row.id);
  message.success('定期复审任务已创建');
  await load();
}

async function generateDueReviews() {
  const rows = await generateDueSupplierReviewsApi();
  message.success(`已生成 ${rows.length} 个到期复审任务`);
  await load();
}

async function completeReview(row: SupplierPeriodicReview, decision: string) {
  await completeSupplierPeriodicReviewApi(row.id, { decision, notes: `复审决定：${decision}`, next_review_days: 365 });
  message.success('复审结论已联动 AVL 和采购资格');
  await load();
}

onMounted(load);
</script>

<template>
  <Page title="供应商准入、PPAP/APQP 与 AVL" auto-content-height>
    <div v-if="dashboard" class="mb-4 grid grid-cols-6 gap-3">
      <a-card size="small" title="待评审准入">{{ dashboard.pending_applications }}</a-card>
      <a-card size="small" title="待审厂">{{ dashboard.audits_pending }}</a-card>
      <a-card size="small" title="待样品承认">{{ dashboard.samples_pending }}</a-card>
      <a-card size="small" title="待 PPAP">{{ dashboard.ppaps_pending }}</a-card>
      <a-card size="small" title="有效 AVL">{{ dashboard.active_avl_entries }}</a-card>
      <a-card size="small" title="到期复审">{{ dashboard.reviews_due }}</a-card>
    </div>

    <a-tabs>
      <a-tab-pane key="qualification" tab="准入申请">
        <a-card title="发起供应商准入" size="small" class="mb-4">
          <a-space wrap>
            <a-select v-model:value="applicationForm.supplier_id" show-search placeholder="供应商" style="width: 260px" :options="supplierOptions()" />
            <a-input v-model:value="applicationForm.requested_scope" placeholder="准入供应范围" style="width: 260px" />
            <a-input v-model:value="applicationForm.certificate_reference" placeholder="营业执照/体系证书引用" style="width: 280px" />
            <a-button type="primary" @click="createApplication">创建申请</a-button>
          </a-space>
        </a-card>
        <a-table :data-source="applications" :loading="loading" row-key="id" size="small" :pagination="{ pageSize: 12 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'supplier'">{{ supplierName(record.supplier_id) }}</template>
            <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button v-if="record.status === 'DRAFT'" type="link" @click="submitApplication(record)">提交</a-button>
                <a-button v-if="['SUBMITTED', 'UNDER_REVIEW'].includes(record.status)" type="link" @click="approveApplication(record)">批准准入</a-button>
                <a-button v-if="['SUBMITTED', 'UNDER_REVIEW'].includes(record.status)" danger type="link" @click="rejectApplication(record)">拒绝</a-button>
              </a-space>
            </template>
          </template>
          <a-table-column title="申请单" data-index="application_no" />
          <a-table-column title="供应商" key="supplier" />
          <a-table-column title="准入范围" data-index="requested_scope" />
          <a-table-column title="状态" key="status" />
          <a-table-column title="有效期" data-index="valid_until" />
          <a-table-column title="操作" key="action" />
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="audit" tab="审厂">
        <a-space wrap class="mb-4">
          <a-select v-model:value="auditForm.application_id" placeholder="准入申请" style="width: 300px" :options="applicationOptions()" />
          <a-select v-model:value="auditForm.audit_type" :options="['INITIAL', 'PERIODIC', 'SPECIAL'].map((value) => ({ label: value, value }))" />
          <span>默认得分</span><a-input-number v-model:value="auditForm.score" :min="0" :max="100" />
          <a-input v-model:value="auditForm.findings" placeholder="审厂发现" style="width: 260px" />
          <a-button type="primary" @click="createAudit">创建审厂</a-button>
        </a-space>
        <a-table :data-source="audits" row-key="id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.result || record.status)">{{ record.result || record.status }}</a-tag></template>
            <template v-else-if="column.key === 'action' && record.status === 'PLANNED'"><a-space><a-button type="link" @click="completeAudit(record, true)">通过</a-button><a-button danger type="link" @click="completeAudit(record, false)">不通过</a-button></a-space></template>
          </template>
          <a-table-column title="审厂单" data-index="audit_no" /><a-table-column title="类型" data-index="audit_type" />
          <a-table-column title="计划时间" data-index="planned_at" /><a-table-column title="得分" data-index="score" />
          <a-table-column title="结论" key="status" /><a-table-column title="发现" data-index="findings" /><a-table-column title="操作" key="action" />
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="sample" tab="样品承认">
        <a-space wrap class="mb-4">
          <a-select v-model:value="sampleForm.application_id" placeholder="准入申请" style="width: 300px" :options="applicationOptions()" />
          <a-select v-model:value="sampleForm.material_id" show-search placeholder="物料" style="width: 300px" :options="materialOptions()" />
          <span>送样数量</span><a-input-number v-model:value="sampleForm.submitted_quantity" :min="0.000001" />
          <a-button type="primary" @click="createSample">创建送样</a-button>
        </a-space>
        <a-table :data-source="samples" row-key="id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'material'">{{ materialName(record.material_id) }}</template>
            <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
            <template v-else-if="column.key === 'action' && ['PENDING', 'TESTING'].includes(record.status)"><a-space><a-button type="link" @click="decideSample(record, true)">承认</a-button><a-button danger type="link" @click="decideSample(record, false)">拒绝</a-button></a-space></template>
          </template>
          <a-table-column title="送样单" data-index="sample_no" /><a-table-column title="物料" key="material" />
          <a-table-column title="轮次" data-index="round_no" /><a-table-column title="数量" data-index="submitted_quantity" />
          <a-table-column title="状态" key="status" /><a-table-column title="操作" key="action" />
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="ppap" tab="PPAP/APQP">
        <a-space wrap class="mb-4">
          <a-select v-model:value="ppapForm.application_id" placeholder="准入申请" style="width: 280px" :options="applicationOptions()" />
          <a-select v-model:value="ppapForm.material_id" show-search placeholder="物料" style="width: 260px" :options="materialOptions()" />
          <a-select v-model:value="ppapForm.sample_approval_id" placeholder="已批准样品" style="width: 260px" :options="approvedSampleOptions()" />
          <span>Level</span><a-input-number v-model:value="ppapForm.level" :min="1" :max="5" />
          <a-input v-model:value="ppapForm.version" placeholder="版本" style="width: 80px" />
          <a-input v-model:value="ppapForm.document_reference" placeholder="PPAP/APQP 文件包引用" style="width: 240px" />
          <a-button type="primary" @click="createPpap">创建 PPAP</a-button>
        </a-space>
        <a-table :data-source="ppaps" row-key="id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'material'">{{ materialName(record.material_id) }}</template>
            <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
            <template v-else-if="column.key === 'action'"><a-space><a-button v-if="record.status === 'DRAFT'" type="link" @click="submitPpap(record)">提交</a-button><a-button v-if="record.status === 'SUBMITTED'" type="link" @click="decidePpap(record, true)">批准</a-button><a-button v-if="record.status === 'SUBMITTED'" danger type="link" @click="decidePpap(record, false)">拒绝</a-button></a-space></template>
          </template>
          <a-table-column title="PPAP 单" data-index="ppap_no" /><a-table-column title="物料" key="material" />
          <a-table-column title="Level" data-index="level" /><a-table-column title="版本" data-index="version" />
          <a-table-column title="状态" key="status" /><a-table-column title="有效期" data-index="expires_at" /><a-table-column title="操作" key="action" />
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="avl" tab="AVL 与定期复审">
        <a-button class="mb-4" type="primary" @click="generateDueReviews">生成到期复审任务</a-button>
        <a-table :data-source="avl" row-key="id" size="small" class="mb-6">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'supplier'">{{ supplierName(record.supplier_id) }}</template>
            <template v-else-if="column.key === 'material'">{{ materialName(record.material_id) }}</template>
            <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
            <template v-else-if="column.key === 'action'"><a-button type="link" @click="createReview(record)">发起复审</a-button></template>
          </template>
          <a-table-column title="供应商" key="supplier" /><a-table-column title="物料" key="material" />
          <a-table-column title="AVL 状态" key="status" /><a-table-column title="PPAP ID" data-index="ppap_id" />
          <a-table-column title="有效期" data-index="valid_until" /><a-table-column title="下次复审" data-index="next_review_at" /><a-table-column title="操作" key="action" />
        </a-table>
        <a-table :data-source="reviews" row-key="id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.decision || record.status)">{{ record.decision || record.status }}</a-tag></template>
            <template v-else-if="column.key === 'action' && record.status === 'PLANNED'"><a-space><a-button type="link" @click="completeReview(record, 'CONTINUE')">延续</a-button><a-button type="link" @click="completeReview(record, 'CONDITIONAL')">有条件</a-button><a-button danger type="link" @click="completeReview(record, 'SUSPEND')">暂停</a-button><a-button danger type="link" @click="completeReview(record, 'REMOVE')">淘汰</a-button></a-space></template>
          </template>
          <a-table-column title="复审单" data-index="review_no" /><a-table-column title="AVL ID" data-index="avl_id" />
          <a-table-column title="SQM 分数" data-index="score_snapshot" /><a-table-column title="计划时间" data-index="planned_at" />
          <a-table-column title="结论" key="status" /><a-table-column title="操作" key="action" />
        </a-table>
      </a-tab-pane>
    </a-tabs>
  </Page>
</template>
