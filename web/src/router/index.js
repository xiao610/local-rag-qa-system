import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    children: [
      { path: '', redirect: '/kb' },
      { path: 'kb', component: () => import('@/views/KbManage.vue') },
      { path: 'chat', component: () => import('@/views/Chat.vue') },
      { path: 'documents', component: () => import('@/views/DocumentManage.vue') },
      { path: 'sessions', component: () => import('@/views/SessionManage.vue') }
    ]
  },
  // 知识库详情页（作为Layout子路由，保持顶部导航栏）
  {
    path: '/kb/:name',
    component: Layout,
    children: [
      {
        path: '',
        component: () => import('@/views/KbDetail.vue'),
        name: 'KbDetail'  // 添加这一行
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router