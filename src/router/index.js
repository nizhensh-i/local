import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/VideoList.vue'),
      meta: {
        title: '视频列表'
      }
    },
    {
      path: '/video/:filename',
      name: 'videoDetail',
      component: () => import('../views/VideoDetail.vue'),
      props: true,
      meta: {
        title: '视频播放'
      }
    }
  ]
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title || '本地视频播放器'
  next()
})

export default router
