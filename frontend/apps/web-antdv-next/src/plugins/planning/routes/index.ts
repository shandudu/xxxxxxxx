import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesPlanning',
    path: '/mes/planning',
    component: () => import('../views/index.vue'),
    meta: {
      icon: 'mdi:clipboard-text-clock-outline',
      title: $t('planning.menu'),
    },
  },
];

export default routes;
