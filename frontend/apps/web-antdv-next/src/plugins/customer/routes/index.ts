import type { RouteRecordRaw } from 'vue-router';
import { $t } from '#/locales';
const routes: RouteRecordRaw[] = [{ name: 'ErpCustomer', path: '/erp/customer', component: () => import('../views/index.vue'), meta: { title: $t('customer.menu'), icon: 'mdi:account-group' } }];
export default routes;
