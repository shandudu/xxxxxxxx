import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesOperationMaterial',
    path: '/mes/operation-material',
    component: () => import('../views/index.vue'),
    meta: {
      icon: 'mdi:transit-connection-variant',
      title: $t('operationMaterial.menu'),
    },
  },
];

export default routes;
