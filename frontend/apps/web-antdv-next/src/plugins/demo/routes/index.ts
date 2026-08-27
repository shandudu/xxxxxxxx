import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesDemoCenter',
    path: '/mes/demo-center',
    component: () => import('../views/index.vue'),
    meta: {
      icon: 'mdi:flask-outline',
      title: $t('demo.menu'),
    },
  },
];

export default routes;
