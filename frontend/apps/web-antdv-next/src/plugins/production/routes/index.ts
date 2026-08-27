import type { RouteRecordRaw } from 'vue-router';
import { $t } from '#/locales';
const routes: RouteRecordRaw[] = [{ name: 'MesProduction', path: '/mes/production', component: () => import('../views/index.vue'), meta: { title: $t('production.menu'), icon: 'mdi:factory' } }];
export default routes;
