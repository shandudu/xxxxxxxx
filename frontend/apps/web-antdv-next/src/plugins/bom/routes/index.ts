import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesBom',
    path: '/mes/bom',
    component: () => import('../views/index.vue'),
    meta: {
      title: $t('bom.menu'),
      icon: 'mdi:file-tree',
    },
  },
];

export default routes;
