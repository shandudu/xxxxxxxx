import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesPackaging',
    path: '/mes/packaging',
    component: () => import('../views/index.vue'),
    meta: { icon: 'mdi:package-variant-closed-check', title: $t('packaging.menu') },
  },
];

export default routes;
