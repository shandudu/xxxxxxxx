import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesPerformance',
    path: '/mes/performance',
    component: () => import('../views/index.vue'),
    meta: {
      icon: 'mdi:chart-box-outline',
      title: $t('performance.menu'),
    },
  },
];

export default routes;
