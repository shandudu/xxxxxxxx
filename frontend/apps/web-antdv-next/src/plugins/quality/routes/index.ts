import type { RouteRecordRaw } from 'vue-router';
import { $t } from '#/locales';
const routes: RouteRecordRaw[]=[
  {name:'MesQuality',path:'/mes/quality',component:()=>import('../views/index.vue'),meta:{title:$t('quality.menu'),icon:'mdi:shield-check-outline'}},
  {name:'MesSupplierQuality',path:'/mes/quality/sqm',component:()=>import('../views/sqm.vue'),meta:{title:'供应商质量管理'}},
];
export default routes;
