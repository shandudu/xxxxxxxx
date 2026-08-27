import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesMaintenance',
    path: '/mes/maintenance',
    component: () => import('../views/index.vue'),
    meta: {
      icon: 'mdi:tools',
      title: $t('maintenance.menu'),
    },
  },
];

export default routes;
