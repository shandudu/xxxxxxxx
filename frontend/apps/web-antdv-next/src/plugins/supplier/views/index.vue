<script lang="ts" setup>
import type {
  CooperationStatus,
  QualityStatus,
  SupplierCategoryTreeNode,
  SupplierContact,
  SupplierContactForm,
  SupplierForm,
  SupplierItem,
  SupplierMaterial,
  SupplierMaterialForm,
  SupplierMaterialStatus,
  SupplierStatus,
} from '../api';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { message } from 'antdv-next';

import {
  createSupplierApi,
  createSupplierCategoryApi,
  createSupplierContactApi,
  createSupplierMaterialApi,
  getSupplierApi,
  getSupplierCategoryTreeApi,
  getSupplierContactsApi,
  getSupplierListApi,
  getSupplierMaterialsApi,
  setSupplierContactPrimaryApi,
  updateSupplierApi,
  updateSupplierCategoryApi,
  updateSupplierCategoryStatusApi,
  updateSupplierContactApi,
  updateSupplierContactStatusApi,
  updateSupplierCooperationApi,
  updateSupplierMaterialApi,
  updateSupplierMaterialStatusApi,
  updateSupplierQualityApi,
  updateSupplierStatusApi,
} from '../api';
import { getMaterialOptionsApi } from '../../material/api';

interface TreeNode extends SupplierCategoryTreeNode {
  key: string;
  title: string;
  children: TreeNode[];
}

interface SupplierPage {
  items: SupplierItem[];
  page: number;
  size: number;
  total: number;
}

interface CategoryOption {
  children: CategoryOption[];
  disabled: boolean;
  label: string;
  value: number;
}

const emptyPage = (): SupplierPage => ({ items: [], page: 1, size: 20, total: 0 });
const emptySupplierForm = (): SupplierForm => ({
  supplier_code: '',
  supplier_name: '',
  category_id: 0,
  supplier_type: 'MATERIAL',
  company_type: 'COMPANY',
  status: 'ACTIVE',
  cooperation_status: 'NORMAL',
  quality_status: 'QUALIFIED',
  purchasing_enabled: true,
  quality_enabled: true,
  trace_enabled: true,
  preferred: false,
  currency: 'CNY',
});
const emptyContactForm = (): SupplierContactForm => ({
  contact_name: '',
  contact_type: 'PURCHASE',
  is_primary: false,
  status: 'ACTIVE',
});
const emptyMaterialForm = (): SupplierMaterialForm => ({
  material_id: 0,
  preferred: false,
  quality_inspection_required: false,
  status: 'ACTIVE',
});

const categoryTree = ref<TreeNode[]>([]);
const categoryKeyword = ref('');
const selectedCategoryId = ref<number>();
const supplierPage = ref<SupplierPage>(emptyPage());
const selectedSupplierId = ref<number>();
const selectedSupplier = ref<SupplierItem>();
const contacts = ref<SupplierContact[]>([]);
const supplierMaterials = ref<SupplierMaterial[]>([]);
const materialOptions = ref<Array<{ label: string; value: number }>>([]);
const loading = ref(false);
const detailLoading = ref(false);
const supplierDrawerOpen = ref(false);
const categoryModalOpen = ref(false);
const contactModalOpen = ref(false);
const materialModalOpen = ref(false);
const saving = ref(false);
const editingContactId = ref<number>();
const editingMaterialId = ref<number>();
const supplierForm = ref<SupplierForm>(emptySupplierForm());
const contactForm = ref<SupplierContactForm>(emptyContactForm());
const materialForm = ref<SupplierMaterialForm>(emptyMaterialForm());
const categoryForm = reactive({
  id: undefined as number | undefined,
  category_code: '',
  category_name: '',
  parent_id: undefined as number | undefined,
  sort_no: 0,
  remark: '',
});
const filters = reactive<{
  cooperation_status?: CooperationStatus;
  keyword: string;
  preferred?: boolean;
  quality_status?: QualityStatus;
  status?: SupplierStatus;
}>({ keyword: '' });

const supplierTypes = [
  'MATERIAL',
  'EQUIPMENT',
  'SPARE_PART',
  'SERVICE',
  'LOGISTICS',
  'OTHER',
].map((value) => ({ label: value, value }));
const companyTypes = ['COMPANY', 'INDIVIDUAL', 'ORGANIZATION'].map((value) => ({ label: value, value }));
const statusOptions = ['ACTIVE', 'DISABLED'].map((value) => ({ label: value, value }));
const cooperationOptions = ['NORMAL', 'SUSPENDED', 'BLACKLISTED'].map((value) => ({ label: value, value }));
const qualityOptions = ['QUALIFIED', 'CONDITIONAL', 'UNQUALIFIED', 'PENDING'].map((value) => ({ label: value, value }));
const contactTypes = ['BUSINESS', 'PURCHASE', 'QUALITY', 'TECHNICAL', 'FINANCE', 'AFTER_SALES', 'OTHER'].map(
  (value) => ({ label: value, value }),
);

const tableColumns = [
  { title: '编码', dataIndex: 'supplier_code', key: 'supplier_code', width: 125 },
  { title: '供应商', dataIndex: 'supplier_name', key: 'supplier_name', width: 160, ellipsis: true },
  { title: '分类', dataIndex: 'category_name', key: 'category_name', width: 100, ellipsis: true },
  { title: '合作', dataIndex: 'cooperation_status', key: 'cooperation_status', width: 90 },
  { title: '质量', dataIndex: 'quality_status', key: 'quality_status', width: 90 },
];
const contactColumns = [
  { title: '联系人', dataIndex: 'contact_name', key: 'contact_name' },
  { title: '类型', dataIndex: 'contact_type', key: 'contact_type', width: 85 },
  { title: '电话', dataIndex: 'mobile', key: 'mobile', width: 110 },
  { title: '主联系人', dataIndex: 'is_primary', key: 'is_primary', width: 78 },
  { title: '操作', key: 'action', width: 130 },
];
const materialColumns = [
  { title: '物料', key: 'material', width: 180 },
  { title: '供应商物料编码', dataIndex: 'supplier_material_code', key: 'supplier_material_code', width: 150 },
  { title: 'MOQ', dataIndex: 'minimum_order_quantity', key: 'minimum_order_quantity', width: 80 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 85 },
  { title: '操作', key: 'action', width: 105 },
];

const filteredCategoryTree = computed(() => {
  const keyword = categoryKeyword.value.trim().toLowerCase();
  if (!keyword) return categoryTree.value;
  const filterTree = (nodes: TreeNode[]): TreeNode[] =>
    nodes.reduce<TreeNode[]>((result, node) => {
      const children = filterTree(node.children);
      if (node.title.toLowerCase().includes(keyword) || children.length > 0) {
        result.push({ ...node, children });
      }
      return result;
    }, []);
  return filterTree(categoryTree.value);
});

const categoryOptions = computed<CategoryOption[]>(() => {
  const mapTree = (nodes: TreeNode[]): CategoryOption[] =>
    nodes.map((node) => ({
      value: node.id,
      label: `${node.name} (${node.code})`,
      disabled: node.status === 'DISABLED',
      children: mapTree(node.children),
    }));
  return mapTree(categoryTree.value);
});

function buildTree(nodes: SupplierCategoryTreeNode[]): TreeNode[] {
  return nodes.map((node) => ({
    ...node,
    key: String(node.id),
    title: `${node.name} (${node.code})`,
    children: buildTree(node.children || []),
  }));
}

function findCategory(id: number, nodes = categoryTree.value): TreeNode | undefined {
  for (const node of nodes) {
    if (node.id === id) return node;
    const found = findCategory(id, node.children);
    if (found) return found;
  }
  return undefined;
}

function statusColor(status: string) {
  if (['ACTIVE', 'NORMAL', 'QUALIFIED'].includes(status)) return 'green';
  if (['SUSPENDED', 'CONDITIONAL', 'PENDING'].includes(status)) return 'orange';
  return 'red';
}

async function loadCategories() {
  categoryTree.value = buildTree(await getSupplierCategoryTreeApi());
}

async function loadMaterials() {
  const materials = await getMaterialOptionsApi({ purchasable: true });
  materialOptions.value = materials.map((item) => ({
    label: `${item.code} - ${item.name}${item.specification ? ` (${item.specification})` : ''}`,
    value: item.id,
  }));
}

async function loadSuppliers(page = 1, size = supplierPage.value.size) {
  loading.value = true;
  try {
    const data = await getSupplierListApi({
      page,
      size,
      category_id: selectedCategoryId.value,
      keyword: filters.keyword.trim() || undefined,
      status: filters.status,
      cooperation_status: filters.cooperation_status,
      quality_status: filters.quality_status,
      preferred: filters.preferred,
    });
    supplierPage.value = data;
    const current = data.items.find((item) => item.id === selectedSupplierId.value);
    if (current) await selectSupplier(current.id);
    else if (data.items[0]) await selectSupplier(data.items[0].id);
    else {
      selectedSupplierId.value = undefined;
      selectedSupplier.value = undefined;
      contacts.value = [];
      supplierMaterials.value = [];
    }
  } finally {
    loading.value = false;
  }
}

async function selectSupplier(id: number) {
  selectedSupplierId.value = id;
  detailLoading.value = true;
  try {
    const [supplier, contactList, relationList] = await Promise.all([
      getSupplierApi(id),
      getSupplierContactsApi(id),
      getSupplierMaterialsApi(id),
    ]);
    selectedSupplier.value = supplier;
    contacts.value = contactList;
    supplierMaterials.value = relationList;
  } finally {
    detailLoading.value = false;
  }
}

function selectCategory(keys: Array<number | string>) {
  selectedCategoryId.value = keys[0] ? Number(keys[0]) : undefined;
  loadSuppliers(1);
}

function resetFilters() {
  filters.keyword = '';
  filters.status = undefined;
  filters.cooperation_status = undefined;
  filters.quality_status = undefined;
  filters.preferred = undefined;
  loadSuppliers(1);
}

function openCreateSupplier() {
  supplierForm.value = emptySupplierForm();
  if (selectedCategoryId.value) supplierForm.value.category_id = selectedCategoryId.value;
  supplierDrawerOpen.value = true;
}

function openEditSupplier() {
  if (!selectedSupplier.value) return;
  supplierForm.value = { ...selectedSupplier.value };
  supplierDrawerOpen.value = true;
}

async function saveSupplier() {
  if (!supplierForm.value.supplier_code.trim() || !supplierForm.value.supplier_name.trim() || !supplierForm.value.category_id) {
    message.warning('请填写供应商编码、名称和分类');
    return;
  }
  saving.value = true;
  try {
    const saved = supplierForm.value.id
      ? await updateSupplierApi(supplierForm.value.id, supplierForm.value)
      : await createSupplierApi(supplierForm.value);
    supplierDrawerOpen.value = false;
    selectedSupplierId.value = saved.id;
    await loadSuppliers(supplierPage.value.page);
    message.success('供应商已保存');
  } finally {
    saving.value = false;
  }
}

async function toggleSupplierStatus() {
  if (!selectedSupplier.value) return;
  const status: SupplierStatus = selectedSupplier.value.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  selectedSupplier.value = await updateSupplierStatusApi(selectedSupplier.value.id, status);
  await loadSuppliers(supplierPage.value.page);
}

async function changeCooperation(value: CooperationStatus) {
  if (!selectedSupplier.value) return;
  selectedSupplier.value = await updateSupplierCooperationApi(selectedSupplier.value.id, value);
  await loadSuppliers(supplierPage.value.page);
}

async function changeQuality(value: QualityStatus) {
  if (!selectedSupplier.value) return;
  selectedSupplier.value = await updateSupplierQualityApi(selectedSupplier.value.id, value);
  await loadSuppliers(supplierPage.value.page);
}

function openCreateCategory() {
  Object.assign(categoryForm, {
    id: undefined,
    category_code: '',
    category_name: '',
    parent_id: selectedCategoryId.value,
    sort_no: 0,
    remark: '',
  });
  categoryModalOpen.value = true;
}

function openEditCategory() {
  if (!selectedCategoryId.value) return;
  const category = findCategory(selectedCategoryId.value);
  if (!category) return;
  Object.assign(categoryForm, {
    id: category.id,
    category_code: category.code,
    category_name: category.name,
    parent_id: category.parent_id,
    sort_no: category.sort_no,
    remark: '',
  });
  categoryModalOpen.value = true;
}

async function toggleCategoryStatus() {
  if (!selectedCategoryId.value) return;
  const category = findCategory(selectedCategoryId.value);
  if (!category) return;
  const status: SupplierStatus = category.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  await updateSupplierCategoryStatusApi(category.id, status);
  await loadCategories();
  message.success('分类状态已更新');
}

async function saveCategory() {
  if (!categoryForm.category_code.trim() || !categoryForm.category_name.trim()) {
    message.warning('请填写分类编码和名称');
    return;
  }
  const data = {
    category_code: categoryForm.category_code,
    category_name: categoryForm.category_name,
    parent_id: categoryForm.parent_id,
    sort_no: categoryForm.sort_no,
    remark: categoryForm.remark || undefined,
  };
  if (categoryForm.id) await updateSupplierCategoryApi(categoryForm.id, data);
  else await createSupplierCategoryApi(data);
  categoryModalOpen.value = false;
  await loadCategories();
  message.success('供应商分类已保存');
}

function openCreateContact() {
  if (!selectedSupplier.value) return;
  editingContactId.value = undefined;
  contactForm.value = emptyContactForm();
  contactModalOpen.value = true;
}

function openEditContact(contact: SupplierContact) {
  editingContactId.value = contact.id;
  contactForm.value = { ...contact };
  contactModalOpen.value = true;
}

async function saveContact() {
  if (!selectedSupplier.value || !contactForm.value.contact_name.trim()) {
    message.warning('请填写联系人姓名');
    return;
  }
  if (editingContactId.value) await updateSupplierContactApi(editingContactId.value, contactForm.value);
  else await createSupplierContactApi(selectedSupplier.value.id, contactForm.value);
  contactModalOpen.value = false;
  contacts.value = await getSupplierContactsApi(selectedSupplier.value.id);
  message.success('联系人已保存');
}

async function setPrimary(contact: SupplierContact) {
  if (!selectedSupplier.value) return;
  await setSupplierContactPrimaryApi(contact.id);
  contacts.value = await getSupplierContactsApi(selectedSupplier.value.id);
}

async function toggleContactStatus(contact: SupplierContact) {
  if (!selectedSupplier.value) return;
  const status: SupplierStatus = contact.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  await updateSupplierContactStatusApi(contact.id, status);
  contacts.value = await getSupplierContactsApi(selectedSupplier.value.id);
}

function openCreateSupplierMaterial() {
  if (!selectedSupplier.value) return;
  editingMaterialId.value = undefined;
  materialForm.value = emptyMaterialForm();
  materialModalOpen.value = true;
}

function openEditSupplierMaterial(relation: SupplierMaterial) {
  editingMaterialId.value = relation.id;
  materialForm.value = { ...relation };
  materialModalOpen.value = true;
}

async function saveSupplierMaterial() {
  if (!selectedSupplier.value || !materialForm.value.material_id) {
    message.warning('请选择物料');
    return;
  }
  if (editingMaterialId.value) await updateSupplierMaterialApi(editingMaterialId.value, materialForm.value);
  else await createSupplierMaterialApi(selectedSupplier.value.id, materialForm.value);
  materialModalOpen.value = false;
  supplierMaterials.value = await getSupplierMaterialsApi(selectedSupplier.value.id);
  message.success('供货物料已保存');
}

async function toggleSupplierMaterialStatus(relation: SupplierMaterial) {
  if (!selectedSupplier.value) return;
  const status: SupplierMaterialStatus = relation.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  await updateSupplierMaterialStatusApi(relation.id, status);
  supplierMaterials.value = await getSupplierMaterialsApi(selectedSupplier.value.id);
}

onMounted(async () => {
  await Promise.all([loadCategories(), loadMaterials()]);
  await loadSuppliers();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 gap-3">
      <a-card class="w-60 shrink-0" :body-style="{ padding: '12px' }">
        <template #title>供应商分类</template>
        <template #extra>
            <a-space :size="2">
            <a-button size="small" type="link" @click="openCreateCategory">新增</a-button>
            <a-button :disabled="!selectedCategoryId" size="small" type="link" @click="openEditCategory">编辑</a-button>
            <a-button :disabled="!selectedCategoryId" size="small" type="link" @click="toggleCategoryStatus">状态</a-button>
          </a-space>
        </template>
        <a-input v-model:value="categoryKeyword" allow-clear class="mb-3" placeholder="搜索分类" />
        <a-button class="mb-2" size="small" type="link" @click="selectedCategoryId = undefined; loadSuppliers(1)">
          全部供应商
        </a-button>
        <a-tree
          :default-expand-all="true"
          :selected-keys="selectedCategoryId ? [String(selectedCategoryId)] : []"
          :tree-data="filteredCategoryTree"
          block-node
          @select="selectCategory"
        />
      </a-card>

      <a-card class="min-w-0 flex-1" :body-style="{ padding: '12px' }">
        <template #title>供应商列表 <span class="ml-2 text-sm text-muted-foreground">{{ supplierPage.total }}</span></template>
        <template #extra><a-button type="primary" @click="openCreateSupplier">新增供应商</a-button></template>
        <div class="mb-3 flex flex-wrap gap-2">
          <a-input-search v-model:value="filters.keyword" allow-clear class="w-48" placeholder="编码 / 名称 / 统一信用代码" @search="loadSuppliers(1)" />
          <a-select v-model:value="filters.status" allow-clear class="w-28" :options="statusOptions" placeholder="状态" @change="loadSuppliers(1)" />
          <a-select v-model:value="filters.cooperation_status" allow-clear class="w-32" :options="cooperationOptions" placeholder="合作状态" @change="loadSuppliers(1)" />
          <a-select v-model:value="filters.quality_status" allow-clear class="w-32" :options="qualityOptions" placeholder="质量状态" @change="loadSuppliers(1)" />
          <a-select v-model:value="filters.preferred" allow-clear class="w-28" placeholder="首选" @change="loadSuppliers(1)">
            <a-select-option :value="true">首选</a-select-option>
            <a-select-option :value="false">非首选</a-select-option>
          </a-select>
          <a-button @click="resetFilters">重置</a-button>
        </div>
        <a-table :columns="tableColumns" :data-source="supplierPage.items" :loading="loading" :pagination="false" :row-key="(item: SupplierItem) => item.id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'supplier_code'">
              <a-button class="h-auto p-0" type="link" @click="selectSupplier(record.id)">{{ record.supplier_code }}</a-button>
            </template>
            <template v-else-if="column.key === 'cooperation_status' || column.key === 'quality_status'">
              <a-tag :color="statusColor(record[column.key])">{{ record[column.key] }}</a-tag>
            </template>
          </template>
        </a-table>
        <div class="mt-3 flex justify-end">
          <a-pagination :current="supplierPage.page" :page-size="supplierPage.size" :show-size-changer="true" :total="supplierPage.total" @change="loadSuppliers" />
        </div>
      </a-card>

      <a-card class="w-[430px] shrink-0" :body-style="{ padding: '12px' }" :loading="detailLoading">
        <template #title>供应商详情</template>
        <a-empty v-if="!selectedSupplier" description="请选择供应商" />
        <template v-else>
          <div class="mb-3 flex items-center justify-between">
            <div><span class="font-medium">{{ selectedSupplier.supplier_name }}</span><span class="ml-2 text-sm text-muted-foreground">{{ selectedSupplier.supplier_code }}</span></div>
            <a-space :size="2"><a-button size="small" @click="openEditSupplier">编辑</a-button><a-button size="small" @click="toggleSupplierStatus">{{ selectedSupplier.status === 'ACTIVE' ? '停用' : '启用' }}</a-button></a-space>
          </div>
          <a-descriptions :column="2" size="small">
            <a-descriptions-item label="分类">{{ selectedSupplier.category_name || '-' }}</a-descriptions-item>
            <a-descriptions-item label="类型">{{ selectedSupplier.supplier_type }}</a-descriptions-item>
            <a-descriptions-item label="运行"><a-tag :color="statusColor(selectedSupplier.status)">{{ selectedSupplier.status }}</a-tag></a-descriptions-item>
            <a-descriptions-item label="首选">{{ selectedSupplier.preferred ? '是' : '否' }}</a-descriptions-item>
            <a-descriptions-item label="信用代码" :span="2">{{ selectedSupplier.unified_social_credit_code || '-' }}</a-descriptions-item>
            <a-descriptions-item label="付款条件">{{ selectedSupplier.payment_terms || '-' }}</a-descriptions-item>
            <a-descriptions-item label="默认交期">{{ selectedSupplier.default_lead_time_days ?? '-' }} 天</a-descriptions-item>
          </a-descriptions>
          <div class="mt-3 grid grid-cols-2 gap-2">
            <a-select :value="selectedSupplier.cooperation_status" :options="cooperationOptions" @change="changeCooperation"><template #prefix>合作</template></a-select>
            <a-select :value="selectedSupplier.quality_status" :options="qualityOptions" @change="changeQuality"><template #prefix>质量</template></a-select>
          </div>
          <a-tabs class="mt-3">
            <a-tab-pane key="contacts" tab="联系人">
              <div class="mb-2 flex justify-end"><a-button size="small" type="primary" @click="openCreateContact">新增联系人</a-button></div>
              <a-table :columns="contactColumns" :data-source="contacts" :pagination="false" :row-key="(item: SupplierContact) => item.id" size="small">
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'is_primary'"><a-tag v-if="record.is_primary" color="blue">主</a-tag><span v-else>-</span></template>
                  <template v-else-if="column.key === 'action'"><a-space :size="2"><a-button size="small" type="link" @click="openEditContact(record)">编辑</a-button><a-button v-if="!record.is_primary" size="small" type="link" @click="setPrimary(record)">设主</a-button><a-button size="small" type="link" @click="toggleContactStatus(record)">{{ record.status === 'ACTIVE' ? '停用' : '启用' }}</a-button></a-space></template>
                </template>
              </a-table>
            </a-tab-pane>
            <a-tab-pane key="materials" tab="供货物料">
              <div class="mb-2 flex justify-end"><a-button size="small" type="primary" @click="openCreateSupplierMaterial">新增供货物料</a-button></div>
              <a-table :columns="materialColumns" :data-source="supplierMaterials" :pagination="false" :row-key="(item: SupplierMaterial) => item.id" size="small">
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'material'"><div>{{ record.material_code || '-' }}</div><div class="text-xs text-muted-foreground">{{ record.material_name || '-' }}</div></template>
                  <template v-else-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag></template>
                  <template v-else-if="column.key === 'action'"><a-space :size="2"><a-button size="small" type="link" @click="openEditSupplierMaterial(record)">编辑</a-button><a-button size="small" type="link" @click="toggleSupplierMaterialStatus(record)">{{ record.status === 'ACTIVE' ? '停用' : '启用' }}</a-button></a-space></template>
                </template>
              </a-table>
            </a-tab-pane>
          </a-tabs>
        </template>
      </a-card>
    </div>

    <a-drawer v-model:open="supplierDrawerOpen" :confirm-loading="saving" :title="supplierForm.id ? '编辑供应商' : '新增供应商'" width="720" @close="supplierDrawerOpen = false">
      <a-form layout="vertical">
        <a-row :gutter="16"><a-col :span="12"><a-form-item label="供应商编码" required><a-input v-model:value="supplierForm.supplier_code" /></a-form-item></a-col><a-col :span="12"><a-form-item label="供应商名称" required><a-input v-model:value="supplierForm.supplier_name" /></a-form-item></a-col></a-row>
        <a-row :gutter="16"><a-col :span="12"><a-form-item label="简称"><a-input v-model:value="supplierForm.short_name" /></a-form-item></a-col><a-col :span="12"><a-form-item label="供应商分类" required><a-tree-select v-model:value="supplierForm.category_id" :tree-data="categoryOptions" class="w-full" tree-default-expand-all /></a-form-item></a-col></a-row>
        <a-row :gutter="16"><a-col :span="12"><a-form-item label="供应类型"><a-select v-model:value="supplierForm.supplier_type" :options="supplierTypes" /></a-form-item></a-col><a-col :span="12"><a-form-item label="企业类型"><a-select v-model:value="supplierForm.company_type" :options="companyTypes" /></a-form-item></a-col></a-row>
        <a-row :gutter="16"><a-col :span="12"><a-form-item label="统一社会信用代码"><a-input v-model:value="supplierForm.unified_social_credit_code" /></a-form-item></a-col><a-col :span="12"><a-form-item label="税号"><a-input v-model:value="supplierForm.tax_number" /></a-form-item></a-col></a-row>
        <a-row :gutter="16"><a-col :span="12"><a-form-item label="币种"><a-input v-model:value="supplierForm.currency" /></a-form-item></a-col><a-col :span="12"><a-form-item label="默认交期（天）"><a-input-number v-model:value="supplierForm.default_lead_time_days" class="w-full" :min="0" /></a-form-item></a-col></a-row>
        <a-form-item label="付款条件"><a-input v-model:value="supplierForm.payment_terms" /></a-form-item>
        <a-form-item label="经营地址"><a-input v-model:value="supplierForm.business_address" /></a-form-item>
        <a-form-item label="业务开关"><a-space><a-switch v-model:checked="supplierForm.purchasing_enabled" checked-children="采购" un-checked-children="采购" /><a-switch v-model:checked="supplierForm.quality_enabled" checked-children="质量" un-checked-children="质量" /><a-switch v-model:checked="supplierForm.trace_enabled" checked-children="追溯" un-checked-children="追溯" /><a-switch v-model:checked="supplierForm.preferred" checked-children="首选" un-checked-children="首选" /></a-space></a-form-item>
        <a-form-item label="备注"><a-textarea v-model:value="supplierForm.remark" :rows="3" /></a-form-item>
        <a-button block type="primary" @click="saveSupplier">保存</a-button>
      </a-form>
    </a-drawer>

    <a-modal v-model:open="categoryModalOpen" :title="categoryForm.id ? '编辑供应商分类' : '新增供应商分类'" @ok="saveCategory">
      <a-form layout="vertical"><a-row :gutter="12"><a-col :span="12"><a-form-item label="分类编码" required><a-input v-model:value="categoryForm.category_code" /></a-form-item></a-col><a-col :span="12"><a-form-item label="分类名称" required><a-input v-model:value="categoryForm.category_name" /></a-form-item></a-col></a-row><a-form-item label="上级分类"><a-tree-select v-model:value="categoryForm.parent_id" allow-clear :tree-data="categoryOptions" class="w-full" tree-default-expand-all /></a-form-item><a-form-item label="排序"><a-input-number v-model:value="categoryForm.sort_no" class="w-full" :min="0" /></a-form-item><a-form-item label="备注"><a-textarea v-model:value="categoryForm.remark" /></a-form-item></a-form>
    </a-modal>

    <a-modal v-model:open="contactModalOpen" :title="editingContactId ? '编辑联系人' : '新增联系人'" @ok="saveContact">
      <a-form layout="vertical"><a-row :gutter="12"><a-col :span="12"><a-form-item label="姓名" required><a-input v-model:value="contactForm.contact_name" /></a-form-item></a-col><a-col :span="12"><a-form-item label="类型"><a-select v-model:value="contactForm.contact_type" :options="contactTypes" /></a-form-item></a-col></a-row><a-row :gutter="12"><a-col :span="12"><a-form-item label="手机"><a-input v-model:value="contactForm.mobile" /></a-form-item></a-col><a-col :span="12"><a-form-item label="邮箱"><a-input v-model:value="contactForm.email" /></a-form-item></a-col></a-row><a-form-item label="部门 / 职位"><a-input v-model:value="contactForm.department" placeholder="部门" /><a-input v-model:value="contactForm.position" class="mt-2" placeholder="职位" /></a-form-item><a-form-item label="主联系人"><a-switch v-model:checked="contactForm.is_primary" /></a-form-item><a-form-item label="备注"><a-textarea v-model:value="contactForm.remark" /></a-form-item></a-form>
    </a-modal>

    <a-modal v-model:open="materialModalOpen" :title="editingMaterialId ? '编辑供货物料' : '新增供货物料'" @ok="saveSupplierMaterial">
      <a-form layout="vertical"><a-form-item label="物料" required><a-select v-model:value="materialForm.material_id" :disabled="Boolean(editingMaterialId)" :options="materialOptions" show-search /></a-form-item><a-row :gutter="12"><a-col :span="12"><a-form-item label="供应商物料编码"><a-input v-model:value="materialForm.supplier_material_code" /></a-form-item></a-col><a-col :span="12"><a-form-item label="供应商物料名称"><a-input v-model:value="materialForm.supplier_material_name" /></a-form-item></a-col></a-row><a-row :gutter="12"><a-col :span="12"><a-form-item label="MOQ"><a-input-number v-model:value="materialForm.minimum_order_quantity" class="w-full" :min="0" /></a-form-item></a-col><a-col :span="12"><a-form-item label="交期（天）"><a-input-number v-model:value="materialForm.lead_time_days" class="w-full" :min="0" /></a-form-item></a-col></a-row><a-form-item label="业务开关"><a-space><a-switch v-model:checked="materialForm.preferred" checked-children="首选" un-checked-children="首选" /><a-switch v-model:checked="materialForm.quality_inspection_required" checked-children="需检" un-checked-children="免检" /></a-space></a-form-item><a-form-item label="备注"><a-textarea v-model:value="materialForm.remark" /></a-form-item></a-form>
    </a-modal>
  </Page>
</template>
