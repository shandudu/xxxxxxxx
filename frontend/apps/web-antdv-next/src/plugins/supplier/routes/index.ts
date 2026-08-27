import type { RouteRecordRaw } from 'vue-router';

import { $t } from '#/locales';

const routes: RouteRecordRaw[] = [
  {
    name: 'ErpSupplier',
    path: '/erp/supplier',
    component: () => import('../views/index.vue'),
    meta: {
      title: $t('supplier.menu'),
      icon: 'mdi:truck-delivery-outline',
    },
  },
];

export default routes;
