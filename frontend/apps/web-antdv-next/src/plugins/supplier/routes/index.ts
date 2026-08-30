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
  {
    name: 'ErpSupplierLifecycle',
    path: '/erp/supplier/lifecycle',
    component: () => import('../views/lifecycle.vue'),
    meta: {
      title: '供应商准入与 AVL',
      icon: 'mdi:clipboard-check-outline',
    },
  },
];

export default routes;
