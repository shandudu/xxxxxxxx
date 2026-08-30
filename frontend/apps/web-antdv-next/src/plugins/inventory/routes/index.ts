import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'MesInventory',
    path: '/mes/inventory',
    component: () => import('../views/index.vue'),
    meta: {
      title: $t('inventory.menu'),
      icon: 'mdi:clipboard-list-outline',
    },
  },
  {
    name: 'MesInventoryReplenishment',
    path: '/mes/inventory/replenishment',
    component: () => import('../views/replenishment.vue'),
    meta: { title: '安全库存 / 自动补货' },
  },
  {
    name: 'MesInventoryShelfLife',
    path: '/mes/inventory/shelf-life',
    component: () => import('../views/shelf-life.vue'),
    meta: { title: '批次效期 / FEFO / 召回' },
  },
];

export default routes;
