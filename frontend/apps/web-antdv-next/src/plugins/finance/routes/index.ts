import type { RouteRecordRaw } from 'vue-router';
import { $t } from '#/locales';

export default [{ name:'ErpFinance', path:'/erp/finance', component:()=>import('../views/index.vue'), meta:{ icon:'mdi:finance', title:$t('finance.menu') } }] satisfies RouteRecordRaw[];
