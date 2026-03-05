import { createRouter, createWebHistory } from 'vue-router'

const AUTH_KEY = 'local_v_logged_in'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/Login.vue'),
      meta: {
        title: '登录',
        public: true
      }
    },
    {
      path: '/',
      name: 'home',
      component: () => import('../views/VideoList.vue'),
      meta: {
        title: '视频列表',
        keepAlive: true
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

router.beforeEach((to) => {
  document.title = to.meta.title || '本地视频播放器'

  if (to.meta.public) {
    return true
  }

  const isAuthed = sessionStorage.getItem(AUTH_KEY) === '1'
  if (!isAuthed) {
    return {
      name: 'login',
      query: { redirect: to.fullPath }
    }
  }

  return true
})

export default router
