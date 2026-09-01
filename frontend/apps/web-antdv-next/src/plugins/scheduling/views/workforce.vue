<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import { getOperationsApi, type OperationItem } from '../../routing/api';
import {
  checkWorkforceAccessApi,
  getJobTypesApi,
  getPositionRulesApi,
  getShiftsApi,
  getSkillLevelsApi,
  getUserOptionsApi,
  getWorkerAuthorizationsApi,
  getWorkerCertificatesApi,
  getWorkerRostersApi,
  getWorkerSkillsApi,
  getWorkCenterOptionsApi,
  getWorkforceDashboardApi,
  saveJobTypeApi,
  savePositionRuleApi,
  saveSkillLevelApi,
  saveWorkerAuthorizationApi,
  saveWorkerCertificateApi,
  saveWorkerRosterApi,
  saveWorkerSkillApi,
  type AccessCheckResult,
  type JobType,
  type PositionRule,
  type Shift,
  type SkillLevel,
  type UserOption,
  type WorkerAuthorization,
  type WorkerCertificate,
  type WorkerRoster,
  type WorkerSkill,
  type WorkforceDashboard,
  type WorkCenterOption,
} from '../api';

type FormKind = 'authorization' | 'certificate' | 'job' | 'level' | 'roster' | 'rule' | 'skill';
const loading = ref(false);
const saving = ref(false);
const modalOpen = ref(false);
const kind = ref<FormKind>('job');
const dashboard = ref<WorkforceDashboard>();
const jobs = ref<JobType[]>([]);
const levels = ref<SkillLevel[]>([]);
const skills = ref<WorkerSkill[]>([]);
const certificates = ref<WorkerCertificate[]>([]);
const rules = ref<PositionRule[]>([]);
const authorizations = ref<WorkerAuthorization[]>([]);
const rosters = ref<WorkerRoster[]>([]);
const shifts = ref<Shift[]>([]);
const users = ref<UserOption[]>([]);
const centers = ref<WorkCenterOption[]>([]);
const operations = ref<OperationItem[]>([]);
const accessResult = ref<AccessCheckResult>();
const checkForm = reactive<Record<string, any>>({ user_id: undefined, operation_id: undefined, work_center_id: undefined });
const form = reactive<Record<string, any>>({});
const today = new Date().toISOString().slice(0, 10);

const titles: Record<FormKind, string> = { job: '工种', level: '技能等级', skill: '人员技能', certificate: '人员证书', authorization: '岗位授权', roster: '排班', rule: '准入规则' };
const statusOptions = computed(() => ['job','level','rule'].includes(kind.value)
  ? [{label:'启用',value:'ACTIVE'},{label:'停用',value:'DISABLED'}]
  : [{label:'启用',value:'ACTIVE'},{label:'暂停',value:'SUSPENDED'},{label:'撤销',value:'REVOKED'}]);
const cards = computed(() => dashboard.value ? [
  ['有效工种', dashboard.value.active_job_types], ['技能等级', dashboard.value.active_skill_levels],
  ['具备技能人员', dashboard.value.qualified_workers], ['30 天临期证书', dashboard.value.certificates_expiring_30_days],
  ['过期证书', dashboard.value.expired_certificates], ['有效岗位授权', dashboard.value.active_authorizations],
  ['今日确认排班', dashboard.value.confirmed_today_rosters], ['启用准入规则', dashboard.value.active_rules],
] : []);
const userName = (id:number) => { const row = users.value.find((item) => item.id === id); return row ? `${row.nickname}（${row.username}）` : `#${id}`; };
const jobName = (id:number) => jobs.value.find((item) => item.id === id)?.job_name || `#${id}`;
const levelName = (id:number) => levels.value.find((item) => item.id === id)?.level_name || `#${id}`;
const centerName = (id?:number) => centers.value.find((item) => item.id === id)?.name || (id ? `#${id}` : '全部工作中心');
const operationName = (id?:number) => operations.value.find((item) => item.id === id)?.operation_name || (id ? `#${id}` : '全部工序');
const shiftName = (id:number) => shifts.value.find((item) => item.id === id)?.shift_name || `#${id}`;

async function load() {
  loading.value = true;
  try {
    const [d,j,l,s,c,r,a,ro,sh,u,w,o] = await Promise.all([
      getWorkforceDashboardApi(), getJobTypesApi(), getSkillLevelsApi(), getWorkerSkillsApi(),
      getWorkerCertificatesApi(), getPositionRulesApi(), getWorkerAuthorizationsApi(), getWorkerRostersApi(),
      getShiftsApi(), getUserOptionsApi(), getWorkCenterOptionsApi(), getOperationsApi({ page:1, size:500, status:'ACTIVE' }),
    ]);
    dashboard.value=d; jobs.value=j; levels.value=l; skills.value=s; certificates.value=c; rules.value=r;
    authorizations.value=a; rosters.value=ro; shifts.value=sh; users.value=u.items; centers.value=w; operations.value=o.items;
  } finally { loading.value = false; }
}

function openForm(next:FormKind) {
  kind.value=next;
  Object.keys(form).forEach((key) => delete form[key]);
  Object.assign(form, next === 'job' ? { job_code:'', job_name:'', status:'ACTIVE' }
    : next === 'level' ? { level_code:'', level_name:'', rank_order:1, status:'ACTIVE' }
    : next === 'skill' ? { assessed_on:today, status:'ACTIVE' }
    : next === 'certificate' ? { issued_on:today, valid_from:today, expires_on:today, status:'ACTIVE' }
    : next === 'authorization' ? { effective_from:today, status:'ACTIVE' }
    : next === 'roster' ? { work_date:today, status:'CONFIRMED' }
    : { rule_code:'', rule_name:'', require_authorization:true, require_roster:true, status:'ACTIVE' });
  modalOpen.value=true;
}

async function save() {
  saving.value=true;
  try {
    const action = kind.value === 'job' ? saveJobTypeApi : kind.value === 'level' ? saveSkillLevelApi
      : kind.value === 'skill' ? saveWorkerSkillApi : kind.value === 'certificate' ? saveWorkerCertificateApi
      : kind.value === 'authorization' ? saveWorkerAuthorizationApi : kind.value === 'roster' ? saveWorkerRosterApi : savePositionRuleApi;
    await action({ ...form });
    message.success(`${titles[kind.value]}已保存`); modalOpen.value=false; await load();
  } finally { saving.value=false; }
}

async function checkAccess() {
  accessResult.value = await checkWorkforceAccessApi({ ...checkForm });
  message[accessResult.value.allowed ? 'success' : 'error'](accessResult.value.allowed ? '准入校验通过' : '准入校验不通过');
}

onMounted(load);
</script>

<template>
  <Page title="人员资质与排班准入" description="工种、技能、证书、岗位授权和班次排班统一控制生产操作资格">
    <a-spin :spinning="loading">
      <a-row :gutter="12" class="mb-4">
        <a-col v-for="item in cards" :key="String(item[0])" :span="6" class="mb-3"><a-card size="small"><a-statistic :title="item[0]" :value="item[1]" /></a-card></a-col>
      </a-row>
      <a-card :bordered="false">
        <template #extra><a-button @click="load">刷新</a-button></template>
        <a-tabs>
          <a-tab-pane key="skills" tab="技能矩阵">
            <a-space class="mb-3"><a-button @click="openForm('job')">维护工种</a-button><a-button @click="openForm('level')">维护等级</a-button><a-button type="primary" @click="openForm('skill')">登记人员技能</a-button></a-space>
            <a-table :data-source="skills" row-key="id" size="small" :pagination="false">
              <a-table-column title="人员" key="user"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ userName(record.user_id) }}</template></a-table-column>
              <a-table-column title="工种" key="job"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ jobName(record.job_type_id) }}</template></a-table-column>
              <a-table-column title="技能等级" key="level"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ levelName(record.skill_level_id) }}</template></a-table-column>
              <a-table-column title="评定日期" data-index="assessed_on" /><a-table-column title="到期日期" data-index="expires_on" /><a-table-column title="状态" data-index="status" />
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="certificates" tab="证书与临期预警">
            <a-button type="primary" class="mb-3" @click="openForm('certificate')">登记/更新证书</a-button>
            <a-table :data-source="certificates" row-key="id" size="small" :pagination="false">
              <a-table-column title="人员" key="user"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ userName(record.user_id) }}</template></a-table-column><a-table-column title="证书" data-index="certificate_name" /><a-table-column title="证书类型" data-index="certificate_type" /><a-table-column title="证书号" data-index="certificate_no" /><a-table-column title="到期日期" data-index="expires_on" />
              <a-table-column title="有效状态" key="valid"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}"><a-tag :color="record.validity_state === 'VALID' ? 'green' : record.validity_state === 'EXPIRING' ? 'orange' : 'red'">{{ record.validity_state }}</a-tag></template></a-table-column>
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="authorization" tab="岗位授权">
            <a-button type="primary" class="mb-3" @click="openForm('authorization')">授予/更新岗位授权</a-button>
            <a-table :data-source="authorizations" row-key="id" size="small" :pagination="false"><a-table-column title="人员" key="user"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ userName(record.user_id) }}</template></a-table-column><a-table-column title="工种" key="job"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ jobName(record.job_type_id) }}</template></a-table-column><a-table-column title="工作中心" key="center"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ centerName(record.work_center_id) }}</template></a-table-column><a-table-column title="工序" key="operation"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ operationName(record.operation_id) }}</template></a-table-column><a-table-column title="生效" data-index="effective_from" /><a-table-column title="失效" data-index="effective_to" /><a-table-column title="状态" data-index="status" /></a-table>
          </a-tab-pane>
          <a-tab-pane key="rosters" tab="人员排班">
            <a-button type="primary" class="mb-3" @click="openForm('roster')">安排班次</a-button>
            <a-table :data-source="rosters" row-key="id" size="small" :pagination="false"><a-table-column title="日期" data-index="work_date" /><a-table-column title="班次" key="shift"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ shiftName(record.shift_id) }}</template></a-table-column><a-table-column title="人员" key="user"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ userName(record.user_id) }}</template></a-table-column><a-table-column title="工种" key="job"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ jobName(record.job_type_id) }}</template></a-table-column><a-table-column title="工作中心" key="center"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ centerName(record.work_center_id) }}</template></a-table-column><a-table-column title="状态" data-index="status" /></a-table>
          </a-tab-pane>
          <a-tab-pane key="rules" tab="准入规则">
            <a-button type="primary" class="mb-3" @click="openForm('rule')">配置准入规则</a-button>
            <a-table :data-source="rules" row-key="id" size="small" :pagination="false"><a-table-column title="规则" data-index="rule_name" /><a-table-column title="工种" key="job"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ jobName(record.job_type_id) }}</template></a-table-column><a-table-column title="最低等级" key="level"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ levelName(record.minimum_skill_level_id) }}</template></a-table-column><a-table-column title="范围" key="scope"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ centerName(record.work_center_id) }} / {{ operationName(record.operation_id) }}</template></a-table-column><a-table-column title="必需证书" data-index="required_certificate_type" /><a-table-column title="授权/排班" key="checks"><!-- @vue-ignore antdv-next column slot typing omits the runtime record payload --><template #default="{record}">{{ record.require_authorization ? '需授权' : '免授权' }} / {{ record.require_roster ? '需排班' : '免排班' }}</template></a-table-column><a-table-column title="状态" data-index="status" /></a-table>
          </a-tab-pane>
          <a-tab-pane key="check" tab="准入预检">
            <a-form layout="inline"><a-form-item label="人员"><a-select v-model:value="checkForm.user_id" class="w-56" :options="users.map(i=>({label:userName(i.id),value:i.id}))" /></a-form-item><a-form-item label="工序"><a-select v-model:value="checkForm.operation_id" show-search class="w-56" :options="operations.map(i=>({label:i.operation_name,value:i.id}))" /></a-form-item><a-form-item label="工作中心"><a-select v-model:value="checkForm.work_center_id" show-search class="w-56" :options="centers.map(i=>({label:i.name,value:i.id}))" /></a-form-item><a-button type="primary" @click="checkAccess">执行预检</a-button></a-form>
            <a-alert v-if="accessResult" class="mt-4" :type="accessResult.allowed ? 'success' : 'error'" :message="accessResult.allowed ? '允许操作' : '禁止操作'" :description="accessResult.enforcement_enabled ? (accessResult.reasons.join('；') || `匹配规则 #${accessResult.matched_rule_id}`) : '当前范围未配置启用规则，按兼容策略放行'" show-icon />
          </a-tab-pane>
        </a-tabs>
      </a-card>
    </a-spin>

    <a-modal v-model:open="modalOpen" :title="`维护${titles[kind]}`" :confirm-loading="saving" width="720px" @ok="save">
      <a-form layout="vertical">
        <template v-if="kind==='job'"><a-form-item label="工种编码" required><a-input v-model:value="form.job_code" /></a-form-item><a-form-item label="工种名称" required><a-input v-model:value="form.job_name" /></a-form-item></template>
        <template v-else-if="kind==='level'"><a-form-item label="等级编码" required><a-input v-model:value="form.level_code" /></a-form-item><a-form-item label="等级名称" required><a-input v-model:value="form.level_name" /></a-form-item><a-form-item label="等级顺序" required><a-input-number v-model:value="form.rank_order" class="w-full" :min="1" /></a-form-item></template>
        <template v-else>
          <a-form-item v-if="kind!=='rule'" label="人员" required><a-select v-model:value="form.user_id" show-search :options="users.map(i=>({label:userName(i.id),value:i.id}))" /></a-form-item>
          <a-form-item v-if="kind!=='certificate'" label="工种" required><a-select v-model:value="form.job_type_id" :options="jobs.map(i=>({label:i.job_name,value:i.id}))" /></a-form-item>
          <template v-if="kind==='skill'"><a-form-item label="技能等级" required><a-select v-model:value="form.skill_level_id" :options="levels.map(i=>({label:i.level_name,value:i.id}))" /></a-form-item><a-form-item label="评定日期" required><a-date-picker v-model:value="form.assessed_on" value-format="YYYY-MM-DD" class="w-full" /></a-form-item><a-form-item label="到期日期"><a-date-picker v-model:value="form.expires_on" value-format="YYYY-MM-DD" class="w-full" /></a-form-item><a-form-item label="评定人"><a-input v-model:value="form.assessor" /></a-form-item></template>
          <template v-if="kind==='certificate'"><a-form-item label="证书类型" required><a-input v-model:value="form.certificate_type" placeholder="如 FORKLIFT" /></a-form-item><a-form-item label="证书名称" required><a-input v-model:value="form.certificate_name" /></a-form-item><a-form-item label="证书号" required><a-input v-model:value="form.certificate_no" /></a-form-item><a-row :gutter="12"><a-col :span="8"><a-form-item label="发证日期"><a-date-picker v-model:value="form.issued_on" value-format="YYYY-MM-DD" /></a-form-item></a-col><a-col :span="8"><a-form-item label="生效日期"><a-date-picker v-model:value="form.valid_from" value-format="YYYY-MM-DD" /></a-form-item></a-col><a-col :span="8"><a-form-item label="到期日期"><a-date-picker v-model:value="form.expires_on" value-format="YYYY-MM-DD" /></a-form-item></a-col></a-row><a-form-item label="发证机构"><a-input v-model:value="form.issuer" /></a-form-item><a-form-item label="证据链接"><a-input v-model:value="form.evidence_url" /></a-form-item></template>
          <template v-if="kind==='authorization'"><a-form-item label="工作中心" required><a-select v-model:value="form.work_center_id" :options="centers.map(i=>({label:i.name,value:i.id}))" /></a-form-item><a-form-item label="限定工序"><a-select v-model:value="form.operation_id" allow-clear :options="operations.map(i=>({label:i.operation_name,value:i.id}))" /></a-form-item><a-row :gutter="12"><a-col :span="12"><a-form-item label="生效日期"><a-date-picker v-model:value="form.effective_from" value-format="YYYY-MM-DD" class="w-full" /></a-form-item></a-col><a-col :span="12"><a-form-item label="失效日期"><a-date-picker v-model:value="form.effective_to" value-format="YYYY-MM-DD" class="w-full" /></a-form-item></a-col></a-row></template>
          <template v-if="kind==='roster'"><a-form-item label="日期"><a-date-picker v-model:value="form.work_date" value-format="YYYY-MM-DD" class="w-full" /></a-form-item><a-form-item label="班次"><a-select v-model:value="form.shift_id" :options="shifts.filter(i=>i.status==='ACTIVE').map(i=>({label:`${i.shift_name} ${i.start_time}-${i.end_time}`,value:i.id}))" /></a-form-item><a-form-item label="工作中心"><a-select v-model:value="form.work_center_id" :options="centers.map(i=>({label:i.name,value:i.id}))" /></a-form-item><a-form-item label="排班状态"><a-select v-model:value="form.status" :options="[{label:'已确认',value:'CONFIRMED'},{label:'计划',value:'PLANNED'},{label:'取消',value:'CANCELLED'}]" /></a-form-item></template>
          <template v-if="kind==='rule'"><a-form-item label="规则编码"><a-input v-model:value="form.rule_code" /></a-form-item><a-form-item label="规则名称"><a-input v-model:value="form.rule_name" /></a-form-item><a-form-item label="最低技能等级"><a-select v-model:value="form.minimum_skill_level_id" :options="levels.map(i=>({label:i.level_name,value:i.id}))" /></a-form-item><a-form-item label="工作中心范围"><a-select v-model:value="form.work_center_id" allow-clear :options="centers.map(i=>({label:i.name,value:i.id}))" /></a-form-item><a-form-item label="工序范围"><a-select v-model:value="form.operation_id" allow-clear :options="operations.map(i=>({label:i.operation_name,value:i.id}))" /></a-form-item><a-form-item label="必需证书类型"><a-input v-model:value="form.required_certificate_type" /></a-form-item><a-space><a-checkbox v-model:checked="form.require_authorization">必须岗位授权</a-checkbox><a-checkbox v-model:checked="form.require_roster">必须当前排班</a-checkbox></a-space></template>
        </template>
        <a-form-item v-if="kind!=='roster'" label="状态"><a-select v-model:value="form.status" :options="statusOptions" /></a-form-item>
      </a-form>
    </a-modal>
  </Page>
</template>
