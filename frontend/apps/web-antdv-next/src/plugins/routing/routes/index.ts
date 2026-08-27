import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesOperation',
    path: '/mes/operation',
    component: () => import('../views/operation.vue'),
    meta: { title: $t('routing.operationMenu'), icon: 'mdi:format-list-numbered' },
  },
  {
    name: 'MesWorkCenter',
    path: '/mes/work-center',
    component: () => import('../views/work-center.vue'),
    meta: { title: $t('routing.workCenterMenu'), icon: 'mdi:factory' },
  },
  {
    name: 'MesRouting',
    path: '/mes/routing',
    component: () => import('../views/routing.vue'),
    meta: { title: $t('routing.menu'), icon: 'mdi:source-branch' },
  },
];

export default routes;
