<script lang="ts" setup>
import type { Team, TerminalContext, UserOption, Workstation } from '../api';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { message } from 'antdv-next';

import {
  addTeamMemberApi,
  checkInApi,
  checkOutApi,
  completeDispatchApi,
  createTeamApi,
  createWorkstationApi,
  getEquipmentOptionsApi,
  getTeamsApi,
  getTerminalContextApi,
  getUserOptionsApi,
  getWorkCenterOptionsApi,
  getWorkstationOptionsApi,
  getWorkstationsApi,
  startDispatchApi,
  updateTeamApi,
  updateWorkstationApi,
} from '../api';

const activeTab = ref('terminal');
const loading = ref(false);
const saving = ref(false);
const teams = ref<Team[]>([]);
const workstations = ref<Workstation[]>([]);
const users = ref<UserOption[]>([]);
const centers = ref<{ code: string; id: number; name: string }[]>([]);
const equipment = ref<{ code: string; id: number; name: string }[]>([]);
const stationOptions = ref<{ code: string; id: number; name: string; work_center_id: number }[]>([]);
const selectedStationId = ref<number>();
const terminal = ref<TerminalContext>();
const modalVisible = ref(false);
const modalKind = ref<'member' | 'station' | 'team'>('team');
const editingId = ref<number>();
const form = ref<Record<string, any>>({});
const completeVisible = ref(false);
const completingDispatchId = ref<number>();
const completeForm = ref({ good_quantity: 0, remark: '', scrap_quantity: 0 });

const modalTitle = computed(() => ({ member: '添加班组成员', station: editingId.value ? '编辑工位' : '新增工位', team: editingId.value ? '编辑班组' : '新增班组' })[modalKind.value]);
const centerOptions = computed(() => centers.value.map((x) => ({ label: `${x.code} · ${x.name}`, value: x.id })));
const userOptions = computed(() => users.value.map((x) => ({ label: `${x.username} · ${x.nickname}`, value: x.id })));
const equipmentOptions = computed(() => equipment.value.map((x) => ({ label: `${x.code} · ${x.name}`, value: x.id })));
const teamOptions = computed(() => teams.value.filter((x) => x.status === 'ACTIVE').map((x) => ({ label: `${x.team_code} · ${x.team_name}`, value: x.id })));

async function loadAll() {
  loading.value = true;
  try {
    const [teamRows, stationRows, userRows, centerRows, equipmentRows, optionRows] = await Promise.all([
      getTeamsApi(), getWorkstationsApi(), getUserOptionsApi(), getWorkCenterOptionsApi(), getEquipmentOptionsApi(), getWorkstationOptionsApi(),
    ]);
    teams.value = teamRows;
    workstations.value = stationRows;
    users.value = userRows;
    centers.value = centerRows;
    equipment.value = equipmentRows;
    stationOptions.value = optionRows;
    if (!selectedStationId.value && optionRows.length) selectedStationId.value = optionRows[0]?.id;
    if (selectedStationId.value) terminal.value = await getTerminalContextApi(selectedStationId.value);
  } finally {
    loading.value = false;
  }
}

async function loadTerminal() {
  if (selectedStationId.value) terminal.value = await getTerminalContextApi(selectedStationId.value);
}

function openTeam(row?: Team) {
  modalKind.value = 'team'; editingId.value = row?.id;
  form.value = row ? { ...row } : { status: 'ACTIVE' };
  modalVisible.value = true;
}

function openStation(row?: Workstation) {
  modalKind.value = 'station'; editingId.value = row?.id;
  form.value = row ? { ...row } : { status: 'ACTIVE', terminal_enabled: true };
  modalVisible.value = true;
}

function openMember(team: Team) {
  modalKind.value = 'member'; editingId.value = team.id;
  form.value = { member_role: 'OPERATOR' };
  modalVisible.value = true;
}

async function submitModal() {
  saving.value = true;
  try {
    if (modalKind.value === 'member' && editingId.value) await addTeamMemberApi(editingId.value, form.value);
    if (modalKind.value === 'team') editingId.value ? await updateTeamApi(editingId.value, form.value) : await createTeamApi(form.value);
    if (modalKind.value === 'station') editingId.value ? await updateWorkstationApi(editingId.value, form.value) : await createWorkstationApi(form.value);
    message.success('保存成功'); modalVisible.value = false; await loadAll();
  } finally { saving.value = false; }
}

async function checkIn() {
  if (!selectedStationId.value) return;
  await checkInApi(selectedStationId.value, { team_id: form.value.terminal_team_id });
  message.success('工位签到成功'); await loadTerminal();
}

async function checkOut() {
  if (!terminal.value?.session) return;
  await checkOutApi(terminal.value.session.id); message.success('已签退'); await loadTerminal();
}

async function startDispatch(id: number) {
  if (!selectedStationId.value) return;
  await startDispatchApi(selectedStationId.value, id); message.success('派工已开工'); await loadTerminal();
}

function openComplete(id: number, quantity: number | string) {
  completingDispatchId.value = id;
  completeForm.value = { good_quantity: Number(quantity), remark: '', scrap_quantity: 0 };
  completeVisible.value = true;
}

async function completeDispatch() {
  if (!selectedStationId.value || !completingDispatchId.value) return;
  saving.value = true;
  try {
    await completeDispatchApi(selectedStationId.value, completingDispatchId.value, completeForm.value);
    message.success('派工已完工'); completeVisible.value = false; await loadTerminal();
  } finally { saving.value = false; }
}

onMounted(loadAll);
</script>

<template>
  <Page title="车间派工与工位终端" auto-content-height>
    <a-tabs v-model:active-key="activeTab">
      <a-tab-pane key="terminal" tab="工位终端">
        <a-card class="mb-3" :loading="loading">
          <div class="flex flex-wrap items-center gap-3">
            <a-select v-model:value="selectedStationId" class="w-72" placeholder="选择工位" :options="stationOptions.map(x => ({ label: `${x.code} · ${x.name}`, value: x.id }))" @change="loadTerminal" />
            <a-select v-if="!terminal?.session" v-model:value="form.terminal_team_id" class="w-56" allow-clear placeholder="选择班组（可选）" :options="teamOptions" />
            <a-button v-if="!terminal?.session" type="primary" :disabled="!selectedStationId" @click="checkIn">签到工位</a-button>
            <a-button v-else danger @click="checkOut">签退</a-button>
            <a-tag :color="terminal?.session ? 'green' : 'default'">{{ terminal?.session ? '已签到' : '未签到' }}</a-tag>
          </div>
        </a-card>
        <a-card title="当前派工" :loading="loading">
          <a-table :data-source="terminal?.dispatches || []" row-key="id" :pagination="false">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'"><a-tag>{{ record.status }}</a-tag></template>
              <template v-else-if="column.key === 'action'"><a-space><a-button v-if="record.status === 'DISPATCHED' || record.status === 'ACCEPTED'" type="link" :disabled="!terminal?.session" @click="startDispatch(record.id)">开工</a-button><a-button v-if="record.status === 'STARTED'" type="link" @click="openComplete(record.id, record.dispatch_quantity)">完工</a-button></a-space></template>
            </template>
            <a-table-column title="派工单" data-index="dispatch_no" />
            <a-table-column title="工单" data-index="work_order_no" />
            <a-table-column title="工序" data-index="operation_name" />
            <a-table-column title="数量" data-index="dispatch_quantity" />
            <a-table-column title="状态" data-index="status" key="status" />
            <a-table-column title="操作" key="action" width="180" />
          </a-table>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="teams" tab="班组管理">
        <a-card :loading="loading"><template #extra><a-button type="primary" @click="openTeam()">新增班组</a-button></template>
          <a-table :data-source="teams" row-key="id"><template #bodyCell="{ column, record }"><template v-if="column.key === 'members'">{{ record.members.map((x: any) => x.nickname || x.username).join('、') || '-' }}</template><template v-else-if="column.key === 'action'"><a-space><a-button type="link" @click="openTeam(record)">编辑</a-button><a-button type="link" @click="openMember(record)">加成员</a-button></a-space></template></template><a-table-column title="编码" data-index="team_code"/><a-table-column title="名称" data-index="team_name"/><a-table-column title="工作中心" data-index="work_center_name"/><a-table-column title="负责人" data-index="leader_username"/><a-table-column title="成员" key="members"/><a-table-column title="状态" data-index="status"/><a-table-column title="操作" key="action"/></a-table>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="stations" tab="工位管理">
        <a-card :loading="loading"><template #extra><a-button type="primary" @click="openStation()">新增工位</a-button></template>
          <a-table :data-source="workstations" row-key="id"><template #bodyCell="{ column, record }"><template v-if="column.key === 'terminal'"><a-tag :color="record.terminal_enabled ? 'green' : 'default'">{{ record.terminal_enabled ? '启用' : '关闭' }}</a-tag></template><template v-else-if="column.key === 'action'"><a-button type="link" @click="openStation(record)">编辑</a-button></template></template><a-table-column title="编码" data-index="workstation_code"/><a-table-column title="名称" data-index="workstation_name"/><a-table-column title="工作中心" data-index="work_center_name"/><a-table-column title="设备" data-index="equipment_name"/><a-table-column title="终端" key="terminal"/><a-table-column title="状态" data-index="status"/><a-table-column title="操作" key="action"/></a-table>
        </a-card>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="modalVisible" :title="modalTitle" :confirm-loading="saving" @ok="submitModal">
      <a-form layout="vertical">
        <template v-if="modalKind === 'team'"><a-form-item label="班组编码" required><a-input v-model:value="form.team_code"/></a-form-item><a-form-item label="班组名称" required><a-input v-model:value="form.team_name"/></a-form-item><a-form-item label="工作中心"><a-select v-model:value="form.work_center_id" allow-clear :options="centerOptions"/></a-form-item><a-form-item label="负责人"><a-select v-model:value="form.leader_user_id" allow-clear show-search :options="userOptions"/></a-form-item></template>
        <template v-if="modalKind === 'station'"><a-form-item label="工位编码" required><a-input v-model:value="form.workstation_code"/></a-form-item><a-form-item label="工位名称" required><a-input v-model:value="form.workstation_name"/></a-form-item><a-form-item label="工作中心" required><a-select v-model:value="form.work_center_id" :options="centerOptions"/></a-form-item><a-form-item label="设备"><a-select v-model:value="form.equipment_id" allow-clear :options="equipmentOptions"/></a-form-item><a-form-item label="启用终端"><a-switch v-model:checked="form.terminal_enabled"/></a-form-item></template>
        <template v-if="modalKind === 'member'"><a-form-item label="用户" required><a-select v-model:value="form.user_id" show-search :options="userOptions"/></a-form-item><a-form-item label="角色"><a-select v-model:value="form.member_role" :options="[{label:'班组长',value:'LEADER'},{label:'操作员',value:'OPERATOR'},{label:'质量',value:'QUALITY'},{label:'物料',value:'MATERIAL'},{label:'其他',value:'OTHER'}]"/></a-form-item></template>
      </a-form>
    </a-modal>

    <a-modal v-model:open="completeVisible" title="派工完工" :confirm-loading="saving" @ok="completeDispatch"><a-form layout="vertical"><a-form-item label="良品数量"><a-input-number v-model:value="completeForm.good_quantity" :min="0" class="w-full"/></a-form-item><a-form-item label="报废数量"><a-input-number v-model:value="completeForm.scrap_quantity" :min="0" class="w-full"/></a-form-item><a-form-item label="备注"><a-textarea v-model:value="completeForm.remark"/></a-form-item></a-form></a-modal>
  </Page>
</template>
