import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesShopfloor',
    path: '/mes/shopfloor',
    component: () => import('../views/index.vue'),
    meta: { icon: 'mdi:monitor-dashboard', title: $t('shopfloor.menu') },
  },
];

export default routes;
