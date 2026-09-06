<script lang="ts" setup>
import type { HandlingUnit, PackagingDashboard, PackagingSpecification, PackagingTask } from '../api';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import { $t } from '#/locales';
import { getConfigurableTip } from '#/utils/dict';

import {
  createHandlingUnitApi,
  createPackagingSpecificationApi,
  createPackagingTaskApi,
  getPackagingDashboardApi,
  getPackagingSpecificationsApi,
  getPackagingTasksApi,
  inspectHandlingUnitApi,
  printPackagingLabelApi,
  recordPackagingWeightApi,
  releasePackagingTaskApi,
  releasePackagingToStockApi,
  scanPackagingItemApi,
  sealHandlingUnitApi,
  startPackagingTaskApi,
} from '../api';

const loading = ref(false);
const saving = ref(false);
const activeTab = ref('workbench');
const dashboard = ref<PackagingDashboard>();
const specifications = ref<PackagingSpecification[]>([]);
const tasks = ref<PackagingTask[]>([]);
const selectedTaskId = ref<number>();
const selectedHuId = ref<number>();
const specModalOpen = ref(false);
const taskModalOpen = ref(false);

const specForm = reactive({
  label_template_code: 'FG-CARTON-V1',
  material_id: undefined as number | undefined,
  require_quality_release: true,
  require_weight_check: false,
  spec_code: '',
  spec_name: '',
  target_gross_weight: undefined as number | undefined,
  units_per_carton: 1,
  version: 'V1',
  weight_tolerance: undefined as number | undefined,
});
const taskForm = reactive({
  planned_quantity: 1,
  production_report_id: undefined as number | undefined,
  specification_id: undefined as number | undefined,
});
const scanForm = reactive({ code: '', quantity: 1 });
const weightForm = reactive({ gross_weight: undefined as number | undefined, tare_weight: 0 });

const currentTask = computed(() => tasks.value.find((item) => item.id === selectedTaskId.value));
const currentHu = computed(() => currentTask.value?.handling_units.find((item) => item.id === selectedHuId.value));
const activeSpecs = computed(() => specifications.value.filter((item) => item.status === 'ACTIVE'));
const tip = (key: string) => getConfigurableTip(`packaging.${key}`, `packaging.tips.${key}`);
const idempotencyKey = (prefix: string) => `${prefix}:${Date.now()}:${crypto.randomUUID()}`;

async function load() {
  loading.value = true;
  try {
    [dashboard.value, specifications.value, tasks.value] = await Promise.all([
      getPackagingDashboardApi(),
      getPackagingSpecificationsApi(),
      getPackagingTasksApi(),
    ]);
    if (selectedTaskId.value && !tasks.value.some((item) => item.id === selectedTaskId.value)) selectedTaskId.value = undefined;
    if (selectedHuId.value && !currentTask.value?.handling_units.some((item) => item.id === selectedHuId.value)) selectedHuId.value = undefined;
  } finally {
    loading.value = false;
  }
}

function selectTask(task: PackagingTask) {
  selectedTaskId.value = task.id;
  selectedHuId.value = task.handling_units.find((item) => item.status === 'OPEN')?.id ?? task.handling_units[0]?.id;
  activeTab.value = 'workbench';
}

async function createSpec() {
  if (!specForm.spec_code || !specForm.spec_name || !specForm.material_id || !specForm.units_per_carton) return message.warning($t('packaging.tips.required'));
  saving.value = true;
  try {
    await createPackagingSpecificationApi(specForm);
    message.success(tip('specCreated'));
    specModalOpen.value = false;
    await load();
  } finally { saving.value = false; }
}

async function createTask() {
  if (!taskForm.production_report_id || !taskForm.specification_id || !taskForm.planned_quantity) return message.warning($t('packaging.tips.required'));
  saving.value = true;
  try {
    const task = await createPackagingTaskApi({ ...taskForm, idempotency_key: idempotencyKey('TASK') });
    message.success(tip('taskCreated'));
    taskModalOpen.value = false;
    selectedTaskId.value = task.id;
    await load();
  } finally { saving.value = false; }
}

async function releaseTask(task: PackagingTask) {
  await releasePackagingTaskApi(task.id); message.success(tip('taskReleased')); await load();
}

async function startTask(task: PackagingTask) {
  await startPackagingTaskApi(task.id); await load();
}

async function createHu() {
  if (!currentTask.value) return message.warning($t('packaging.placeholder.selectTask'));
  const hu = await createHandlingUnitApi(currentTask.value.id, { hu_type: 'CARTON' });
  selectedHuId.value = hu.id;
  message.success(tip('huCreated'));
  await load();
}

async function scan() {
  if (!currentHu.value || !scanForm.code) return message.warning($t('packaging.tips.required'));
  await scanPackagingItemApi(currentHu.value.id, {
    code: scanForm.code.trim(),
    idempotency_key: idempotencyKey('SCAN'),
    quantity: scanForm.quantity,
  });
  scanForm.code = '';
  message.success(tip('scanAccepted'));
  await load();
}

async function weigh() {
  if (!currentHu.value || !weightForm.gross_weight) return message.warning($t('packaging.tips.required'));
  await recordPackagingWeightApi(currentHu.value.id, {
    ...weightForm,
    idempotency_key: idempotencyKey('WEIGHT'),
  });
  message.success(tip('weightRecorded'));
  await load();
}

async function seal() {
  if (!currentHu.value) return;
  await sealHandlingUnitApi(currentHu.value.id, {});
  message.success(tip('huSealed'));
  await load();
}

async function inspect(result: 'FAIL' | 'PASS') {
  if (!currentHu.value) return;
  await inspectHandlingUnitApi(currentHu.value.id, {
    appearance_passed: result === 'PASS',
    idempotency_key: idempotencyKey('INSPECTION'),
    label_passed: result === 'PASS',
    quantity_passed: result === 'PASS',
    result,
  });
  message.success(tip('inspectionCompleted'));
  await load();
}

async function printLabel(hu: HandlingUnit) {
  await printPackagingLabelApi(hu.id, { copies: 1, idempotency_key: idempotencyKey('LABEL') });
  message.success(tip('labelRecorded'));
}

async function releaseToStock() {
  if (!currentTask.value) return;
  await releasePackagingToStockApi(currentTask.value.id);
  message.success(tip('releasedToStock'));
  await load();
}

onMounted(load);
</script>

<template>
  <Page :title="$t('packaging.title')" :description="$t('packaging.subtitle')" auto-content-height>
    <div class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <a-card size="small"><a-statistic :title="$t('packaging.dashboard.draft')" :value="dashboard?.draft_tasks || 0" /></a-card>
      <a-card size="small"><a-statistic :title="$t('packaging.dashboard.active')" :value="dashboard?.active_tasks || 0" /></a-card>
      <a-card size="small"><a-statistic :title="$t('packaging.dashboard.packed')" :value="dashboard?.packed_tasks || 0" /></a-card>
      <a-card size="small"><a-statistic :title="$t('packaging.dashboard.released')" :value="dashboard?.released_tasks || 0" /></a-card>
      <a-card size="small"><a-statistic :title="$t('packaging.dashboard.openHu')" :value="dashboard?.open_handling_units || 0" /></a-card>
      <a-card size="small"><a-statistic :title="$t('packaging.dashboard.heldHu')" :value="dashboard?.held_handling_units || 0" /></a-card>
    </div>

    <a-tabs v-model:active-key="activeTab">
      <template #rightExtra><a-button :loading="loading" @click="load">{{ $t('packaging.action.refresh') }}</a-button></template>
      <a-tab-pane key="workbench" :tab="$t('packaging.tab.workbench')">
        <a-empty v-if="!currentTask" :description="$t('packaging.placeholder.selectTask')" />
        <template v-else>
          <a-card class="mb-3" size="small">
            <div class="flex flex-wrap items-center gap-3">
              <strong>{{ currentTask.task_no }}</strong><a-tag>{{ currentTask.status }}</a-tag>
              <span>{{ $t('packaging.field.packedQuantity') }}: {{ currentTask.packed_quantity }} / {{ currentTask.planned_quantity }}</span>
              <span>{{ $t('packaging.field.lotId') }}: {{ currentTask.lot_id || '-' }}</span>
              <a-button type="primary" :disabled="!['RELEASED', 'IN_PROGRESS'].includes(currentTask.status)" @click="createHu">{{ $t('packaging.action.createHu') }}</a-button>
              <a-button type="primary" ghost :disabled="currentTask.status !== 'PACKED'" @click="releaseToStock">{{ $t('packaging.action.stock') }}</a-button>
            </div>
          </a-card>
          <div class="grid gap-3 xl:grid-cols-[320px_1fr]">
            <a-card :title="$t('packaging.field.huCode')" size="small">
              <a-list :data-source="currentTask.handling_units" bordered>
                <template #renderItem="{ item }">
                  <a-list-item class="cursor-pointer" :class="{ 'bg-primary/10': selectedHuId === item.id }" @click="selectedHuId = item.id">
                    <a-list-item-meta :title="item.hu_code" :description="`${item.quantity} / ${item.capacity}`" />
                    <a-tag>{{ item.status }}</a-tag>
                  </a-list-item>
                </template>
              </a-list>
            </a-card>
            <a-card v-if="currentHu" :title="currentHu.hu_code" size="small">
              <div class="mb-4 flex flex-wrap gap-2">
                <a-input v-model:value="scanForm.code" class="min-w-64 flex-1" autofocus :placeholder="$t('packaging.placeholder.scan')" :disabled="currentHu.status !== 'OPEN'" @press-enter="scan" />
                <a-input-number v-model:value="scanForm.quantity" :min="0.000001" :disabled="currentHu.status !== 'OPEN'" />
                <a-button type="primary" :disabled="currentHu.status !== 'OPEN'" @click="scan">{{ $t('packaging.action.scan') }}</a-button>
              </div>
              <div class="mb-4 flex flex-wrap items-center gap-2">
                <span>{{ $t('packaging.field.grossWeight') }}</span><a-input-number v-model:value="weightForm.gross_weight" :min="0.000001" />
                <span>{{ $t('packaging.field.tareWeight') }}</span><a-input-number v-model:value="weightForm.tare_weight" :min="0" />
                <a-button :disabled="currentHu.status !== 'OPEN'" @click="weigh">{{ $t('packaging.action.weight') }}</a-button>
                <a-button type="primary" :disabled="currentHu.status !== 'OPEN'" @click="seal">{{ $t('packaging.action.seal') }}</a-button>
                <a-button type="primary" :disabled="!['SEALED', 'QUALITY_HOLD'].includes(currentHu.status)" @click="inspect('PASS')">{{ $t('packaging.action.inspectPass') }}</a-button>
                <a-button danger :disabled="!['SEALED', 'QUALITY_HOLD'].includes(currentHu.status)" @click="inspect('FAIL')">{{ $t('packaging.action.inspectFail') }}</a-button>
                <a-button :disabled="currentHu.status === 'OPEN'" @click="printLabel(currentHu)">{{ $t('packaging.action.print') }}</a-button>
              </div>
              <a-descriptions class="mb-3" bordered size="small" :column="3">
                <a-descriptions-item :label="$t('packaging.field.status')">{{ currentHu.status }}</a-descriptions-item>
                <a-descriptions-item :label="$t('packaging.field.quantity')">{{ currentHu.quantity }} / {{ currentHu.capacity }}</a-descriptions-item>
                <a-descriptions-item :label="$t('packaging.field.weightResult')">{{ currentHu.weight_result || '-' }}</a-descriptions-item>
              </a-descriptions>
              <a-table :data-source="currentHu.contents" row-key="id" size="small" :pagination="false">
                <a-table-column :title="$t('packaging.field.scanCode')" data-index="scanned_code" />
                <a-table-column :title="$t('packaging.field.status')" data-index="scan_type" />
                <a-table-column :title="$t('packaging.field.quantity')" data-index="quantity" />
                <a-table-column :title="$t('packaging.field.lotId')" data-index="lot_id" />
              </a-table>
            </a-card>
          </div>
        </template>
      </a-tab-pane>

      <a-tab-pane key="task" :tab="$t('packaging.tab.task')">
        <a-card :loading="loading"><template #extra><a-button type="primary" @click="taskModalOpen = true">{{ $t('packaging.action.createTask') }}</a-button></template>
          <a-table :data-source="tasks" row-key="id">
            <template #bodyCell="{ column, record }"><template v-if="column.key === 'status'"><a-tag>{{ record.status }}</a-tag></template><template v-else-if="column.key === 'quantity'">{{ record.packed_quantity }} / {{ record.planned_quantity }}</template><template v-else-if="column.key === 'action'"><a-space><a-button v-if="record.status === 'DRAFT'" type="link" @click="releaseTask(record)">{{ $t('packaging.action.release') }}</a-button><a-button v-if="record.status === 'RELEASED'" type="link" @click="startTask(record)">{{ $t('packaging.action.start') }}</a-button><a-button type="link" @click="selectTask(record)">{{ $t('packaging.action.select') }}</a-button></a-space></template></template>
            <a-table-column :title="$t('packaging.field.taskNo')" data-index="task_no" /><a-table-column :title="$t('packaging.field.reportId')" data-index="production_report_id" /><a-table-column :title="$t('packaging.field.materialId')" data-index="material_id" /><a-table-column :title="$t('packaging.field.packedQuantity')" key="quantity" /><a-table-column :title="$t('packaging.field.status')" key="status" /><a-table-column :title="$t('packaging.action.select')" key="action" />
          </a-table>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="spec" :tab="$t('packaging.tab.spec')">
        <a-card :loading="loading"><template #extra><a-button type="primary" @click="specModalOpen = true">{{ $t('packaging.action.createSpec') }}</a-button></template>
          <a-table :data-source="specifications" row-key="id"><a-table-column :title="$t('packaging.field.specCode')" data-index="spec_code" /><a-table-column :title="$t('packaging.field.specName')" data-index="spec_name" /><a-table-column :title="$t('packaging.field.materialId')" data-index="material_id" /><a-table-column :title="$t('packaging.field.unitsPerCarton')" data-index="units_per_carton" /><a-table-column :title="$t('packaging.field.version')" data-index="version" /><a-table-column :title="$t('packaging.field.status')" data-index="status" /></a-table>
        </a-card>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="specModalOpen" :title="$t('packaging.action.createSpec')" :confirm-loading="saving" @ok="createSpec"><a-form layout="vertical"><a-form-item :label="$t('packaging.field.specCode')" required><a-input v-model:value="specForm.spec_code" /></a-form-item><a-form-item :label="$t('packaging.field.specName')" required><a-input v-model:value="specForm.spec_name" /></a-form-item><a-form-item :label="$t('packaging.field.materialId')" required><a-input-number v-model:value="specForm.material_id" :min="1" class="w-full" /></a-form-item><a-form-item :label="$t('packaging.field.unitsPerCarton')" required><a-input-number v-model:value="specForm.units_per_carton" :min="0.000001" class="w-full" /></a-form-item><a-form-item :label="$t('packaging.field.version')"><a-input v-model:value="specForm.version" /></a-form-item><a-form-item :label="$t('packaging.field.labelTemplate')"><a-input v-model:value="specForm.label_template_code" /></a-form-item><a-form-item :label="$t('packaging.field.weightRequired')"><a-switch v-model:checked="specForm.require_weight_check" /></a-form-item><template v-if="specForm.require_weight_check"><a-form-item :label="$t('packaging.field.targetWeight')" required><a-input-number v-model:value="specForm.target_gross_weight" :min="0.000001" class="w-full" /></a-form-item><a-form-item :label="$t('packaging.field.tolerance')" required><a-input-number v-model:value="specForm.weight_tolerance" :min="0" class="w-full" /></a-form-item></template></a-form></a-modal>
    <a-modal v-model:open="taskModalOpen" :title="$t('packaging.action.createTask')" :confirm-loading="saving" @ok="createTask"><a-form layout="vertical"><a-form-item :label="$t('packaging.field.reportId')" required><a-input-number v-model:value="taskForm.production_report_id" :min="1" class="w-full" /></a-form-item><a-form-item :label="$t('packaging.field.specification')" required><a-select v-model:value="taskForm.specification_id" :options="activeSpecs.map(item => ({ label: `${item.spec_code} · ${item.spec_name} · ${item.units_per_carton}`, value: item.id }))" /></a-form-item><a-form-item :label="$t('packaging.field.plannedQuantity')" required><a-input-number v-model:value="taskForm.planned_quantity" :min="0.000001" class="w-full" /></a-form-item></a-form></a-modal>
  </Page>
</template>
