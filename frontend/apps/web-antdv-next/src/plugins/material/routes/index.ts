import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesMaterial',
    path: '/mes/material',
    component: () => import('../views/index.vue'),
    meta: {
      title: $t('material.menu'),
      icon: 'mdi:package-variant-closed',
    },
  },
];

export default routes;
