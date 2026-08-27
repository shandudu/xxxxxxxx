import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesScheduling',
    path: '/mes/scheduling',
    component: () => import('../views/index.vue'),
    meta: {
      icon: 'mdi:chart-timeline-variant-shimmer',
      title: $t('scheduling.menu'),
    },
  },
];

export default routes;
