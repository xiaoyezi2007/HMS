<template>
  <div class="staff-profile">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>个人主页</span>
          <small>查看账号信息并修改密码</small>
        </div>
      </template>

      <el-descriptions :column="1">
        <el-descriptions-item label="用户名">{{ user?.username }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ user?.phone }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ user?.role }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ user?.status }}</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <el-form :model="pwdForm" label-width="120px">
        <el-form-item label="当前密码">
          <el-input v-model="pwdForm.current_password" type="password" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="pwdForm.confirm_password" type="password" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="changing" @click="submitChange">修改密码</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { fetchCurrentUser, changePassword } from "../../api/modules/auth";

const user = ref<any | null>(null);
const changing = ref(false);

const pwdForm = reactive({ current_password: "", new_password: "", confirm_password: "" });

async function loadUser() {
  try {
    const { data } = await fetchCurrentUser();
    user.value = data;
  } catch (err) {
    console.error("fetchCurrentUser error", err);
  }
}

async function submitChange() {
  if (!pwdForm.current_password || !pwdForm.new_password) {
    ElMessage.warning("请填写完整密码信息");
    return;
  }
  if (pwdForm.new_password !== pwdForm.confirm_password) {
    ElMessage.warning("两次输入的新密码不一致");
    return;
  }
  changing.value = true;
  try {
    await changePassword(pwdForm.current_password, pwdForm.new_password);
    ElMessage.success("密码已修改，请重新登录");
    // 清除本地 token 并跳转登录（前端 http 拦截会处理 401）
    window.localStorage.removeItem("hms-token");
    window.localStorage.removeItem("hms-role");
    window.localStorage.removeItem("hms-phone");
    window.location.href = "/login";
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "修改失败");
  } finally {
    changing.value = false;
  }
}

onMounted(() => {
  loadUser();
});
</script>

<style scoped>
.card-header { display:flex; flex-direction:column }
.card-header small { color: #94a3b8 }
</style>
