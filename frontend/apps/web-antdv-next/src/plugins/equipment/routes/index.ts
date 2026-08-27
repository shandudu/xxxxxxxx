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
];

export default routes;
