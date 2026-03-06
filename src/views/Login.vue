<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <h1 class="title">访问验证</h1>
      <p class="subtitle">请输入访问密码</p>
      <el-form @submit.prevent="handleLogin">
        <el-form-item>
          <el-input
            v-model="password"
            placeholder="请输入密码"
            show-password
            size="large"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item class="remember-item">
          <el-checkbox v-model="rememberPassword">记住登录状态</el-checkbox>
        </el-form-item>
        <el-button type="primary" size="large" class="login-btn" @click="handleLogin">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { getEffectivePassword } from '../utils/auth'
import { AUTH_KEY, REMEMBER_LOGIN_KEY } from '../utils/auth-keys'

export default {
  name: 'LoginPage',
  data() {
    return {
      password: '',
      rememberPassword: false,
      effectivePassword: ''
    }
  },
  async mounted() {
    const remember = localStorage.getItem(REMEMBER_LOGIN_KEY) === '1'
    if (remember) {
      this.rememberPassword = true
      sessionStorage.setItem(AUTH_KEY, '1')
      const redirectPath = this.$route.query.redirect || '/'
      this.$router.replace(redirectPath)
      return
    }

    this.effectivePassword = await getEffectivePassword()
  },
  methods: {
    handleLogin() {
      if (!this.effectivePassword) {
        this.$message.error('密码配置尚未加载完成，请稍后重试')
        return
      }

      if (this.password !== this.effectivePassword) {
        this.$message.error('密码错误')
        return
      }

      sessionStorage.setItem(AUTH_KEY, '1')
      if (this.rememberPassword) {
        localStorage.setItem(REMEMBER_LOGIN_KEY, '1')
      } else {
        localStorage.removeItem(REMEMBER_LOGIN_KEY)
      }
      localStorage.removeItem('local_v_remember_password')
      localStorage.removeItem('local_v_saved_password')
      const redirectPath = this.$route.query.redirect || '/'
      this.$router.replace(redirectPath)
    }
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f0ff 0%, #f8fbff 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  border-radius: 12px;
}

.title {
  margin: 0 0 8px;
  text-align: center;
  color: #1f2937;
}

.subtitle {
  margin: 0 0 20px;
  text-align: center;
  color: #6b7280;
}

.remember-item {
  margin-top: -6px;
}

.login-btn {
  width: 100%;
}
</style>
