import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesTrace',
    path: '/mes/trace',
    component: () => import('../views/index.vue'),
    meta: {
      title: $t('trace.menu'),
      icon: 'mdi:graph-outline',
    },
  },
];

export default routes;

