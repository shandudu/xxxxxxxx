<script lang="ts" setup>
import type { BomItemRecord } from '../../bom/api';
import type { RoutingItem } from '../../routing/api';
import type { OperationMaterialPlan, PlanValidation } from '../api';

import { computed, onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import { getBomApi, getBomListApi } from '../../bom/api';
import { getRoutingApi, getRoutingsApi } from '../../routing/api';
import {
  activatePlanApi,
  addRequirementApi,
  createPlanApi,
  deactivatePlanApi,
  getPlanApi,
  getPlansApi,
  validatePlanApi,
} from '../api';

const loading = ref(false);
const saving = ref(false);
const plans = ref<OperationMaterialPlan[]>([]);
const selected = ref<OperationMaterialPlan>();
const boms = ref<BomItemRecord[]>([]);
const routings = ref<RoutingItem[]>([]);
const selectedBom = ref<BomItemRecord>();
const selectedRouting = ref<RoutingItem>();
const validation = ref<PlanValidation>();
const createVisible = ref(false);
const requirementVisible = ref(false);
const createForm = ref<Record<string, any>>({});
const requirementForm = ref<Record<string, any>>({ quantity: 1 });

const compatibleRoutings = computed(() => {
  const bom = boms.value.find((item) => item.id === createForm.value.bom_id);
  return bom
    ? routings.value.filter((item) => item.product_material_id === bom.product_material_id)
    : routings.value;
});

const requirementRows = computed(() =>
  (selected.value?.requirements ?? []).map((item) => ({
    ...item,
    bom_item_label: bomItemLabel(item.bom_item_id),
    operation_label: operationLabel(item.routing_operation_id),
  })),
);

function bomItemLabel(id: number) {
  const row = selectedBom.value?.items?.find((item) => item.id === id);
  return row ? `${row.line_no} · ${row.component.code} · ${row.component.name}` : `#${id}`;
}

function operationLabel(id: number) {
  const row = selectedRouting.value?.operations?.find((item) => item.id === id);
  return row ? `${row.sequence_no} · ${row.operation_display_name}` : `#${id}`;
}

async function load() {
  loading.value = true;
  try {
    plans.value = await getPlansApi();
    if (selected.value) {
      const current = plans.value.find((item) => item.id === selected.value?.id);
      if (current) await selectPlan(current);
    }
  } finally {
    loading.value = false;
  }
}

async function loadOptions() {
  async function fetchAll<T>(
    fetchPage: (
      page: number,
    ) => Promise<{ items: T[]; total_pages: number }>,
  ) {
    const firstPage = await fetchPage(1);
    if (firstPage.total_pages <= 1) {
      return firstPage.items;
    }

    const remainingPages = await Promise.all(
      Array.from({ length: firstPage.total_pages - 1 }, (_, index) =>
        fetchPage(index + 2),
      ),
    );
    return [firstPage, ...remainingPages].flatMap((page) => page.items);
  }

  const [bomItems, routingItems] = await Promise.all([
    fetchAll((page) => getBomListApi({ page, size: 200 })),
    fetchAll((page) => getRoutingsApi({ page, size: 200 })),
  ]);
  boms.value = bomItems;
  routings.value = routingItems;
}

async function selectPlan(row: OperationMaterialPlan) {
  const [detail, bom, routing] = await Promise.all([
    getPlanApi(row.id),
    getBomApi(row.bom_id),
    getRoutingApi(row.routing_id),
  ]);
  selected.value = detail;
  selectedBom.value = bom;
  selectedRouting.value = routing;
  validation.value = undefined;
}

function openCreate() {
  createForm.value = { plan_code: '', bom_id: undefined, routing_id: undefined, remark: '' };
  createVisible.value = true;
}

function bomChanged() {
  createForm.value.routing_id = compatibleRoutings.value[0]?.id;
}

async function createPlan() {
  saving.value = true;
  try {
    selected.value = await createPlanApi(createForm.value);
    createVisible.value = false;
    message.success('计划已创建');
    await load();
  } finally {
    saving.value = false;
  }
}

function openRequirement() {
  requirementForm.value = {
    bom_item_id: selectedBom.value?.items?.[0]?.id,
    routing_operation_id: selectedRouting.value?.operations?.[0]?.id,
    quantity: 1,
    remark: '',
  };
  requirementVisible.value = true;
}

async function addRequirement() {
  if (!selected.value) return;
  saving.value = true;
  try {
    await addRequirementApi(selected.value.id, requirementForm.value);
    requirementVisible.value = false;
    message.success('投料分配已保存');
    await selectPlan(selected.value);
  } finally {
    saving.value = false;
  }
}

async function validatePlan() {
  if (!selected.value) return;
  validation.value = await validatePlanApi(selected.value.id);
  message[validation.value.valid ? 'success' : 'warning'](
    validation.value.valid ? '计划校验通过' : '计划存在未分配的必选物料',
  );
}

async function changeStatus(target: 'ACTIVE' | 'INACTIVE') {
  if (!selected.value) return;
  selected.value = target === 'ACTIVE'
    ? await activatePlanApi(selected.value.id)
    : await deactivatePlanApi(selected.value.id);
  message.success(target === 'ACTIVE' ? '计划已生效' : '计划已停用');
  await load();
}

onMounted(async () => {
  await Promise.all([loadOptions(), load()]);
});
</script>

<template>
  <Page title="工序物料计划">
    <div class="flex h-full min-h-0 gap-4">
      <a-card class="min-w-0 flex-1" :bordered="false">
        <div class="mb-3 flex gap-2">
          <a-button type="primary" @click="openCreate">新建计划</a-button>
          <a-button @click="load">刷新</a-button>
        </div>
        <a-table
          :data-source="plans"
          :loading="loading"
          :pagination="{ pageSize: 20 }"
          row-key="id"
          @row="(row: OperationMaterialPlan) => ({ onClick: () => selectPlan(row) })"
        >
          <a-table-column title="计划编码" data-index="plan_code" />
          <a-table-column title="BOM ID" data-index="bom_id" />
          <a-table-column title="工艺路线 ID" data-index="routing_id" />
          <a-table-column title="状态" data-index="status" />
        </a-table>
      </a-card>

      <a-card class="w-[620px] shrink-0" :bordered="false" :title="selected?.plan_code ?? '计划详情'">
        <a-empty v-if="!selected" description="请选择一个计划" />
        <template v-else>
          <a-descriptions :column="1" size="small">
            <a-descriptions-item label="BOM">
              {{ selectedBom?.bom_code }} / {{ selectedBom?.bom_version }}
            </a-descriptions-item>
            <a-descriptions-item label="工艺路线">
              {{ selectedRouting?.routing_code }} / {{ selectedRouting?.routing_version }}
            </a-descriptions-item>
            <a-descriptions-item label="状态"><a-tag>{{ selected.status }}</a-tag></a-descriptions-item>
          </a-descriptions>
          <div class="my-3 flex gap-2">
            <a-button v-if="selected.status === 'DRAFT'" type="primary" @click="openRequirement">添加投料分配</a-button>
            <a-button @click="validatePlan">校验</a-button>
            <a-button v-if="selected.status !== 'ACTIVE'" @click="changeStatus('ACTIVE')">生效</a-button>
            <a-button v-else @click="changeStatus('INACTIVE')">停用</a-button>
          </div>
          <a-alert
            v-if="validation"
            class="mb-3"
            :message="validation.valid ? '校验通过' : '校验未通过'"
            :description="[...validation.errors, ...validation.warnings].join('；') || '所有必选物料均已分配'"
            :type="validation.valid ? 'success' : 'warning'"
            show-icon
          />
          <a-table :data-source="requirementRows" row-key="id" size="small" :pagination="false">
            <a-table-column title="BOM 物料" data-index="bom_item_label" />
            <a-table-column title="投料工序" data-index="operation_label" />
            <a-table-column title="数量" data-index="quantity" />
          </a-table>
        </template>
      </a-card>
    </div>

    <a-modal v-model:open="createVisible" title="新建工序物料计划" :confirm-loading="saving" @ok="createPlan">
      <a-form layout="vertical" :model="createForm">
        <a-form-item label="计划编码" required><a-input v-model:value="createForm.plan_code" /></a-form-item>
        <a-form-item label="BOM" required>
          <a-select
            v-model:value="createForm.bom_id"
            show-search
            :options="boms.map((item) => ({ label: `${item.bom_code} / ${item.bom_version} · ${item.product.name}`, value: item.id }))"
            @change="bomChanged"
          />
        </a-form-item>
        <a-form-item label="工艺路线" required>
          <a-select
            v-model:value="createForm.routing_id"
            :options="compatibleRoutings.map((item) => ({ label: `${item.routing_code} / ${item.routing_version}`, value: item.id }))"
          />
        </a-form-item>
        <a-form-item label="备注"><a-textarea v-model:value="createForm.remark" /></a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="requirementVisible" title="添加投料分配" :confirm-loading="saving" @ok="addRequirement">
      <a-form layout="vertical" :model="requirementForm">
        <a-form-item label="BOM 物料" required>
          <a-select
            v-model:value="requirementForm.bom_item_id"
            :options="selectedBom?.items?.map((item) => ({ label: `${item.line_no} · ${item.component.code} · ${item.component.name}`, value: item.id }))"
          />
        </a-form-item>
        <a-form-item label="投料工序" required>
          <a-select
            v-model:value="requirementForm.routing_operation_id"
            :options="selectedRouting?.operations?.map((item) => ({ label: `${item.sequence_no} · ${item.operation_display_name}`, value: item.id }))"
          />
        </a-form-item>
        <a-form-item label="分配数量" required><a-input-number v-model:value="requirementForm.quantity" class="w-full" :min="0.000001" /></a-form-item>
        <a-form-item label="备注"><a-textarea v-model:value="requirementForm.remark" /></a-form-item>
      </a-form>
    </a-modal>
  </Page>
</template>
