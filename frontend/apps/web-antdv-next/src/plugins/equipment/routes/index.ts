import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesEquipment',
    path: '/mes/equipment',
    component: () => import('../views/index.vue'),
    meta: {
      title: $t('equipment.menu'),
      icon: 'mdi:robot-industrial',
    },
  },
  {
    name: 'MesMoldLifecycle',
    path: '/mes/equipment/molds',
    component: () => import('../views/molds.vue'),
    meta: { title: '模具全生命周期', icon: 'mdi:tools' },
  },
];

export default routes;
