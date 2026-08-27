<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { Card, Col, InputNumber, Row, Select, Space, Statistic, Table, Tag, message } from 'antdv-next';
import { calculateWorkOrderCostApi, getCostPeriodsApi, getMarginDashboardApi, postWorkOrderCostApi, type CostPeriod, type MarginDashboard, type MarginDimension, type WorkOrderCost } from '../api';

const loading = ref(false); const periods = ref<CostPeriod[]>([]); const periodId = ref<number>(); const workOrderId = ref<number>(); const dimension = ref<MarginDimension>('PRODUCT'); const margin = ref<MarginDashboard>(); const cost = ref<WorkOrderCost>();
const selectedPeriod = computed(() => periods.value.find((item) => item.id === periodId.value));
const fmt = (v: unknown) => Number(v ?? 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
async function load() { loading.value = true; try { periods.value = await getCostPeriodsApi(); periodId.value ||= periods.value[0]?.id; if (periodId.value) margin.value = await getMarginDashboardApi(dimension.value, periodId.value); } finally { loading.value = false; } }
async function refreshMargin() { if (periodId.value) margin.value = await getMarginDashboardApi(dimension.value, periodId.value); }
async function calculate(post = false) { if (!periodId.value || !workOrderId.value) return message.warning('请先选择成本期间并输入工单 ID'); cost.value = post ? await postWorkOrderCostApi(workOrderId.value, periodId.value) : await calculateWorkOrderCostApi(workOrderId.value, periodId.value); message.success(post ? '工单成本已结转' : '工单成本试算完成'); await refreshMargin(); }
const columns = [{ title:'维度', dataIndex:'name' }, { title:'发货数量', dataIndex:'shipped_quantity', customRender:({text}:any)=>fmt(text) }, { title:'收入', dataIndex:'revenue', customRender:({text}:any)=>fmt(text) }, { title:'销货成本', dataIndex:'cogs', customRender:({text}:any)=>fmt(text) }, { title:'毛利', dataIndex:'gross_profit', customRender:({text}:any)=>fmt(text) }, { title:'毛利率', dataIndex:'margin_rate', customRender:({text}:any)=>`${fmt(text)}%` }, { title:'成本覆盖率', dataIndex:'cost_coverage', customRender:({text}:any)=>`${fmt(text)}%` }];
onMounted(load);
</script>
<template>
  <Page title="生产成本核算与毛利分析">
    <Space wrap style="margin-bottom:16px"><Select v-model:value="periodId" style="width:180px" placeholder="成本期间" :options="periods.map(p=>({label:`${p.period_code} · ${p.status}`,value:p.id}))" @change="refreshMargin"/><Select v-model:value="dimension" style="width:130px" :options="[{label:'按产品',value:'PRODUCT'},{label:'按客户',value:'CUSTOMER'}]" @change="refreshMargin"/><InputNumber v-model:value="workOrderId" :min="1" placeholder="工单 ID"/><a-button type="primary" :loading="loading" @click="calculate(false)">成本试算</a-button><a-button :loading="loading" @click="calculate(true)">结转成本</a-button></Space>
    <Row :gutter="16"><Col :span="6"><Card><Statistic title="期间" :value="selectedPeriod?.period_code || '-'" /></Card></Col><Col :span="6"><Card><Statistic title="销售收入" :value="fmt(margin?.revenue)" suffix="CNY" /></Card></Col><Col :span="6"><Card><Statistic title="销货成本" :value="fmt(margin?.cogs)" suffix="CNY" /></Card></Col><Col :span="6"><Card><Statistic title="毛利率" :value="fmt(margin?.margin_rate)" suffix="%" /></Card></Col></Row>
    <Card v-if="cost" title="工单成本结转结果" style="margin-top:16px"><Space wrap><Tag color="blue">{{ cost.work_order_no_snapshot }}</Tag><span>产品：{{ cost.product_name_snapshot }}</span><span>材料 {{ fmt(cost.material_cost) }}</span><span>人工 {{ fmt(cost.labor_cost) }}</span><span>制造费用 {{ fmt(Number(cost.machine_cost)+Number(cost.overhead_cost)) }}</span><span>总成本 {{ fmt(cost.total_cost) }}</span><span>单位成本 {{ fmt(cost.unit_cost) }}</span><Tag :color="cost.status==='POSTED'?'green':'orange'">{{ cost.status }}</Tag></Space></Card>
    <Card title="产品 / 客户毛利明细" style="margin-top:16px"><Table row-key="key" :loading="loading" :columns="columns" :data-source="margin?.rows || []" :pagination="{pageSize:10}" /></Card>
  </Page>
</template>
