import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesWarehouse',
    path: '/mes/warehouse',
    component: () => import('../views/index.vue'),
    meta: {
      title: $t('warehouse.menu'),
      icon: 'mdi:warehouse',
    },
  },
];

export default routes;
