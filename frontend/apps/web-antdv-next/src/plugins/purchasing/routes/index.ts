import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'ErpPurchasing',
    path: '/erp/purchasing',
    component: () => import('../views/index.vue'),
    meta: { title: $t('purchasing.menu'), icon: 'mdi:cart-outline' },
  },
  {
    name: 'ErpPurchasingDelivery',
    path: '/erp/purchasing/delivery',
    component: () => import('../views/delivery.vue'),
    meta: { title: '供应商交期 / 采购 OTIF' },
  },
];

export default routes;
