<template>
  <div class="auth-wrapper">
    <el-card class="auth-card" shadow="always">
      <div class="title">
        <h2>医院管理系统</h2>
      </div>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="立即登录" name="login">
          <el-form :model="loginForm" label-width="80px" @keyup.enter="handleLogin">
            <el-form-item label="手机号">
              <el-input v-model="loginForm.phone" maxlength="11" placeholder="请输入手机号" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" class="full-width" :loading="loading" @click="handleLogin">登录</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="快速注册" name="register">
          <el-form :model="registerForm" label-width="80px" class="mt-3">
            <el-form-item label="手机号">
              <el-input v-model="registerForm.phone" maxlength="11" placeholder="登录手机号" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="registerForm.username" placeholder="昵称 / 工号" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="registerForm.password" type="password" show-password placeholder="请设置密码" />
            </el-form-item>
            <el-form-item label="确认密码">
              <el-input v-model="registerForm.confirmPassword" type="password" show-password placeholder="请再次输入密码" />
            </el-form-item>
            <el-form-item>
              <el-button type="success" class="full-width" :loading="loading" @click="handleRegister">注册并登录</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { login, register } from "../api/modules/auth";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const activeTab = ref("login");
const loading = ref(false);

const loginForm = reactive({
  phone: "",
  password: ""
});

const registerForm = reactive({
  phone: "",
  username: "",
  password: "",
  confirmPassword: ""
});

async function handleLogin() {
  if (!loginForm.phone || !loginForm.password) {
    ElMessage.warning("请输入手机号和密码");
    return;
  }
  loading.value = true;
  try {
    const { data } = await login({ ...loginForm });
    auth.setSession(data.access_token, loginForm.phone);
    ElMessage.success("登录成功");
    const redirect = (route.query.redirect as string) || "/";
    router.replace(redirect);
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail ?? "登录失败");
  } finally {
    loading.value = false;
  }
}

async function handleRegister() {
  if (!registerForm.phone || !registerForm.password || !registerForm.username) {
    ElMessage.warning("请完整填写注册信息");
    return;
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    ElMessage.warning("两次输入的密码不一致");
    return;
  }
  loading.value = true;
  try {
    await register({
      phone: registerForm.phone,
      username: registerForm.username,
      password: registerForm.password,
      role: "患者"
    });
    ElMessage.success("注册成功，已自动切换到登录页");
    activeTab.value = "login";
    loginForm.phone = registerForm.phone;
    loginForm.password = registerForm.password;
    await handleLogin();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail ?? "注册失败");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-wrapper {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: radial-gradient(circle at top, #c7d2fe, #f8fafc 55%);
  padding: 24px;
}

.auth-card {
  width: 420px;
}

.title {
  text-align: center;
  margin-bottom: 24px;
}

.title h2 {
  margin: 0;
}

.mt-3 {
  margin-top: 12px;
}

.full-width {
  width: 100%;
}
</style>
