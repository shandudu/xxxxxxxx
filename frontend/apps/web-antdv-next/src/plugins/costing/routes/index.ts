import type { RouteRecordRaw } from 'vue-router';
import { $t } from '#/locales';

export default [{
  name: 'ErpCosting',
  path: '/erp/costing',
  component: () => import('../views/index.vue'),
  meta: { icon: 'mdi:finance', title: $t('costing.menu') },
}] satisfies RouteRecordRaw[];
