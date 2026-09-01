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
  {
    name: 'MesWorkforceQualification',
    path: '/mes/workforce-qualification',
    component: () => import('../views/workforce.vue'),
    meta: {
      icon: 'mdi:account-hard-hat',
      title: $t('scheduling.workforceMenu'),
    },
  },
];

export default routes;
