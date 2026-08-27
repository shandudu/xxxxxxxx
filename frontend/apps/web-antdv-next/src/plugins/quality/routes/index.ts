import type { RouteRecordRaw } from 'vue-router';
import { $t } from '#/locales';
const routes: RouteRecordRaw[]=[{name:'MesQuality',path:'/mes/quality',component:()=>import('../views/index.vue'),meta:{title:$t('quality.menu'),icon:'mdi:shield-check-outline'}}];
export default routes;
