<script lang="ts" setup>
import { onMounted, reactive, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message, Modal } from 'antdv-next';

import type {
  ExpiryAlert,
  FefoCandidate,
  LotQualityHold,
  LotRecall,
  ShelfLifeDashboard,
  ShelfLifePolicy,
} from '../api';
import {
  acknowledgeExpiryAlertApi,
  closeLotRecallApi,
  createExpiryReinspectionApi,
  createLotRecallApi,
  getExpiryAlertsApi,
  getFefoCandidatesApi,
  getLotHoldsApi,
  getLotRecallsApi,
  getShelfLifeDashboardApi,
  getShelfLifePoliciesApi,
  releaseLotHoldApi,
  scrapLotHoldApi,
  syncExpiryAlertsApi,
  updateLotRecallItemApi,
  upsertShelfLifePolicyApi,
} from '../api';

const loading = ref(false);
const dashboard = ref<ShelfLifeDashboard>();
const policies = ref<ShelfLifePolicy[]>([]);
const alerts = ref<ExpiryAlert[]>([]);
const holds = ref<LotQualityHold[]>([]);
const recalls = ref<LotRecall[]>([]);
const candidates = ref<FefoCandidate[]>([]);

const policyForm = reactive({
  material_id: undefined as number | undefined,
  warning_days: 30,
  critical_days: 7,
  min_remaining_days_at_issue: 0,
  fefo_enabled: true,
  auto_hold_expired: true,
  retest_required: true,
  status: 'ACTIVE',
});
const fefoForm = reactive({
  material_id: undefined as number | undefined,
  warehouse_id: undefined as number | undefined,
  quantity: 1,
});
const recallForm = reactive({
  root_lot_id: undefined as number | undefined,
  reason: '',
  severity: 'MAJOR',
});
const releaseOpen = ref(false);
const selectedHold = ref<LotQualityHold>();
const releaseForm = reactive({ new_expiry_date: '', decision_reason: '' });

async function load() {
  loading.value = true;
  try {
    [dashboard.value, policies.value, alerts.value, holds.value, recalls.value] = await Promise.all([
      getShelfLifeDashboardApi(),
      getShelfLifePoliciesApi(),
      getExpiryAlertsApi(),
      getLotHoldsApi(),
      getLotRecallsApi(),
    ]);
  } finally {
    loading.value = false;
  }
}

async function savePolicy() {
  if (!policyForm.material_id) return message.warning('请输入物料 ID');
  await upsertShelfLifePolicyApi(policyForm.material_id, policyForm);
  message.success('效期与 FEFO 策略已保存');
  await load();
}

async function syncAlerts() {
  const rows = await syncExpiryAlertsApi();
  message.success(`已刷新 ${rows.length} 个风险批次，过期批次已按策略冻结`);
  await load();
}

async function acknowledge(row: ExpiryAlert) {
  await acknowledgeExpiryAlertApi(row.id);
  message.success('预警已确认');
  await load();
}

async function reinspect(row: LotQualityHold) {
  await createExpiryReinspectionApi(row.id);
  message.success('复检单已创建，请在质量检验模块录入结果');
  await load();
}

function openRelease(row: LotQualityHold) {
  selectedHold.value = row;
  releaseForm.new_expiry_date = '';
  releaseForm.decision_reason = '';
  releaseOpen.value = true;
}

async function releaseHold() {
  if (!selectedHold.value || !releaseForm.new_expiry_date || !releaseForm.decision_reason) {
    return message.warning('请填写新效期和放行依据');
  }
  await releaseLotHoldApi(selectedHold.value.id, {
    new_expiry_date: new Date(releaseForm.new_expiry_date).toISOString(),
    decision_reason: releaseForm.decision_reason,
  });
  releaseOpen.value = false;
  message.success('批次已复检放行并更新效期');
  await load();
}

function scrap(row: LotQualityHold) {
  Modal.confirm({
    title: '确认报废该批次全部可用库存？',
    content: `隔离单 ${row.hold_no}，此操作会生成库存报废流水。`,
    okType: 'danger',
    async onOk() {
      await scrapLotHoldApi(row.id, { decision_reason: '效期复检不通过，批准报废' });
      message.success('批次库存已报废');
      await load();
    },
  });
}

async function previewFefo() {
  if (!fefoForm.material_id || !fefoForm.warehouse_id || fefoForm.quantity <= 0) {
    return message.warning('请输入物料、仓库和需求数量');
  }
  candidates.value = await getFefoCandidatesApi(fefoForm);
}

async function createRecall() {
  if (!recallForm.root_lot_id || !recallForm.reason) return message.warning('请输入根批次和召回原因');
  await createLotRecallApi(recallForm);
  recallForm.reason = '';
  message.success('召回单已创建，相关库存已隔离，受影响发货已展开');
  await load();
}

async function resolveItem(recall: LotRecall, itemId: number) {
  await updateLotRecallItemApi(recall.id, itemId, {
    status: 'CLOSED',
    action_notes: '召回处置已完成',
  });
  message.success('影响项已关闭');
  await load();
}

async function closeRecall(row: LotRecall) {
  await closeLotRecallApi(row.id);
  message.success('召回闭环已完成');
  await load();
}

function levelColor(level: string) {
  return level === 'EXPIRED' ? 'red' : level === 'CRITICAL' ? 'orange' : 'gold';
}

onMounted(load);
</script>

<template>
  <Page title="批次效期、FEFO 与质量隔离" auto-content-height>
    <div v-if="dashboard" class="mb-4 grid grid-cols-6 gap-3">
      <a-card size="small" title="策略物料">{{ dashboard.policy_count }}</a-card>
      <a-card size="small" title="临期预警">{{ dashboard.warning_count }}</a-card>
      <a-card size="small" title="严重临期">{{ dashboard.critical_count }}</a-card>
      <a-card size="small" title="已过期">{{ dashboard.expired_count }}</a-card>
      <a-card size="small" title="质量隔离">{{ dashboard.open_hold_count }}</a-card>
      <a-card size="small" title="召回处理中">{{ dashboard.active_recall_count }}</a-card>
    </div>

    <a-tabs>
      <a-tab-pane key="alerts" tab="临期预警 / 质量隔离">
        <a-card :bordered="false" class="mb-4">
          <template #extra><a-button type="primary" @click="syncAlerts">扫描效期并自动冻结</a-button></template>
          <a-table :data-source="alerts" :loading="loading" row-key="id" size="small">
            <a-table-column title="批次 ID" data-index="lot_id" />
            <a-table-column title="剩余天数" data-index="days_remaining" />
            <a-table-column title="可用数量" data-index="available_quantity" />
            <a-table-column title="状态" data-index="status" />
            <a-table-column title="风险" key="level">
              <!-- @vue-ignore antdv-next column slot typing omits the runtime record payload -->
              <template #default="{ record }"><a-tag :color="levelColor(record.level)">{{ record.level }}</a-tag></template>
            </a-table-column>
            <a-table-column title="操作" key="action">
              <!-- @vue-ignore antdv-next column slot typing omits the runtime record payload -->
              <template #default="{ record }">
                <a-button v-if="record.status === 'OPEN'" type="link" @click="acknowledge(record)">确认</a-button>
              </template>
            </a-table-column>
          </a-table>
        </a-card>
        <a-card title="隔离处置" :bordered="false">
          <a-table :data-source="holds" row-key="id" size="small" :pagination="{ pageSize: 10 }">
            <a-table-column title="隔离单" data-index="hold_no" />
            <a-table-column title="批次 ID" data-index="lot_id" />
            <a-table-column title="原因" data-index="reason" />
            <a-table-column title="状态" data-index="status" />
            <a-table-column title="复检单 ID" data-index="inspection_id" />
            <a-table-column title="操作" key="action">
              <!-- @vue-ignore antdv-next column slot typing omits the runtime record payload -->
              <template #default="{ record }">
                <a-space>
                  <a-button v-if="record.status === 'OPEN'" type="link" @click="reinspect(record)">发起复检</a-button>
                  <a-button v-if="record.status === 'AWAITING_RETEST'" type="link" @click="openRelease(record)">复检放行</a-button>
                  <a-button v-if="['OPEN', 'AWAITING_RETEST'].includes(record.status)" danger type="link" @click="scrap(record)">报废</a-button>
                </a-space>
              </template>
            </a-table-column>
          </a-table>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="fefo" tab="FEFO 分配预览">
        <a-card :bordered="false">
          <a-space class="mb-4" wrap>
            <a-input-number v-model:value="fefoForm.material_id" placeholder="物料 ID" :min="1" />
            <a-input-number v-model:value="fefoForm.warehouse_id" placeholder="仓库 ID" :min="1" />
            <a-input-number v-model:value="fefoForm.quantity" placeholder="需求数量" :min="0.000001" />
            <a-button type="primary" @click="previewFefo">按效期计算</a-button>
          </a-space>
          <a-table :data-source="candidates" row-key="balance_id" size="small">
            <a-table-column title="批次" data-index="lot_no" />
            <a-table-column title="库位 ID" data-index="location_id" />
            <a-table-column title="有效期" data-index="expiry_date" />
            <a-table-column title="剩余天数" data-index="days_remaining" />
            <a-table-column title="可用数量" data-index="available_quantity" />
            <a-table-column title="本次分配" data-index="allocated_quantity" />
          </a-table>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="policies" tab="效期策略">
        <a-card title="新增或更新物料策略" :bordered="false" class="mb-4">
          <a-space wrap>
            <a-input-number v-model:value="policyForm.material_id" placeholder="物料 ID" :min="1" />
            <span>预警天数</span><a-input-number v-model:value="policyForm.warning_days" :min="1" />
            <span>严重天数</span><a-input-number v-model:value="policyForm.critical_days" :min="0" />
            <span>出库最低剩余天数</span><a-input-number v-model:value="policyForm.min_remaining_days_at_issue" :min="0" />
            <a-checkbox v-model:checked="policyForm.fefo_enabled">启用 FEFO</a-checkbox>
            <a-checkbox v-model:checked="policyForm.auto_hold_expired">过期自动冻结</a-checkbox>
            <a-checkbox v-model:checked="policyForm.retest_required">放行必须复检</a-checkbox>
            <a-button type="primary" @click="savePolicy">保存策略</a-button>
          </a-space>
        </a-card>
        <a-table :data-source="policies" row-key="id" size="small">
          <a-table-column title="物料 ID" data-index="material_id" />
          <a-table-column title="预警天数" data-index="warning_days" />
          <a-table-column title="严重天数" data-index="critical_days" />
          <a-table-column title="出库最低剩余天数" data-index="min_remaining_days_at_issue" />
          <a-table-column title="FEFO" data-index="fefo_enabled" />
          <a-table-column title="过期冻结" data-index="auto_hold_expired" />
          <a-table-column title="状态" data-index="status" />
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="recalls" tab="批次召回">
        <a-card title="发起批次召回" :bordered="false" class="mb-4">
          <a-space wrap>
            <a-input-number v-model:value="recallForm.root_lot_id" placeholder="根批次 ID" :min="1" />
            <a-select v-model:value="recallForm.severity" style="width: 120px">
              <a-select-option value="MINOR">一般</a-select-option>
              <a-select-option value="MAJOR">重大</a-select-option>
              <a-select-option value="CRITICAL">紧急</a-select-option>
            </a-select>
            <a-input v-model:value="recallForm.reason" placeholder="召回原因" style="width: 360px" />
            <a-button danger type="primary" @click="createRecall">发起召回</a-button>
          </a-space>
        </a-card>
        <a-collapse>
          <a-collapse-panel v-for="recall in recalls" :key="recall.id" :header="`${recall.recall_no} · 根批次 ${recall.root_lot_id} · ${recall.status}`">
            <p>{{ recall.reason }}</p>
            <a-table :data-source="recall.items" row-key="id" size="small" :pagination="false">
              <a-table-column title="影响类型" data-index="item_type" />
              <a-table-column title="批次 ID" data-index="lot_id" />
              <a-table-column title="发货单 ID" data-index="shipment_id" />
              <a-table-column title="客户 ID" data-index="customer_id" />
              <a-table-column title="数量" data-index="quantity" />
              <a-table-column title="处置状态" data-index="status" />
              <a-table-column title="操作" key="action">
                <!-- @vue-ignore antdv-next column slot typing omits the runtime record payload -->
                <template #default="{ record }">
                  <a-button v-if="record.status !== 'CLOSED'" type="link" @click="resolveItem(recall, record.id)">标记已处置</a-button>
                </template>
              </a-table-column>
            </a-table>
            <a-button v-if="recall.status === 'ACTIVE'" class="mt-3" type="primary" @click="closeRecall(recall)">关闭召回</a-button>
          </a-collapse-panel>
        </a-collapse>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="releaseOpen" title="复检放行" @ok="releaseHold">
      <a-form layout="vertical">
        <a-form-item label="新有效期"><a-input v-model:value="releaseForm.new_expiry_date" type="datetime-local" /></a-form-item>
        <a-form-item label="放行依据"><a-textarea v-model:value="releaseForm.decision_reason" :rows="3" /></a-form-item>
      </a-form>
    </a-modal>
  </Page>
</template>
