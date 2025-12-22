<template>
  <div class="patient-profile">
    <el-card shadow="hover" v-loading="loadingProfile">
      <template #header>
        <div class="card-header">
          <span>个人信息档案</span>
          <small>首次挂号前请先完善实名信息</small>
        </div>
      </template>
      <el-form :model="profileForm" label-width="80px">
        <el-form-item label="姓名">
          <el-input v-model="profileForm.name" placeholder="与证件一致" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="profileForm.gender">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="出生日期">
          <el-date-picker
            v-model="profileForm.birth_date"
            type="date"
            placeholder="请选择"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="身份证">
          <el-input v-model="profileForm.id_number" maxlength="18" placeholder="18 位身份证号" />
        </el-form-item>
        <el-form-item label="联系地址">
          <el-input v-model="profileForm.address" type="textarea" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitLoading" @click="submitProfile">提交档案</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>修改密码</span>
          <small>更新账户登录密码</small>
        </div>
      </template>
      <el-form :model="pwdForm" label-width="100px">
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
          <el-button type="primary" :loading="pwdLoading" @click="submitPwd">修改密码</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { createPatientProfile, fetchPatientProfile } from "../../api/modules/patient";
import { changePassword } from "../../api/modules/auth";

const profileForm = reactive({
  name: "",
  gender: "男",
  birth_date: "",
  id_number: "",
  address: ""
});

const loadingProfile = ref(false);
const submitLoading = ref(false);
const hasProfile = ref(false);
const pwdLoading = ref(false);
const pwdForm = reactive({ current_password: "", new_password: "", confirm_password: "" });

async function loadProfile() {
  loadingProfile.value = true;
  try {
    const { data } = await fetchPatientProfile();
    if (data) {
      hasProfile.value = true;
      profileForm.name = data.name ?? "";
      profileForm.gender = data.gender ?? "男";
      profileForm.birth_date = data.birth_date ?? "";
      profileForm.id_number = data.id_number ?? "";
      profileForm.address = data.address ?? "";
    }
  } catch (error: any) {
    if (error.response?.status === 404) {
      hasProfile.value = false;
    } else {
      ElMessage.error(error.response?.data?.detail ?? "档案加载失败");
    }
  } finally {
    loadingProfile.value = false;
  }
}

async function submitProfile() {
  if (!profileForm.name || !profileForm.birth_date || !profileForm.id_number) {
    ElMessage.warning("请完整填写档案信息");
    return;
  }
  const updating = hasProfile.value;
  submitLoading.value = true;
  try {
    await createPatientProfile({ ...profileForm });
    ElMessage.success(updating ? "档案更新成功" : "档案提交成功");
    hasProfile.value = true;
    await loadProfile();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail ?? "提交失败");
  } finally {
    submitLoading.value = false;
  }
}

onMounted(() => {
  loadProfile();
});

async function submitPwd() {
  if (!pwdForm.current_password || !pwdForm.new_password) {
    ElMessage.warning("请填写完整密码信息");
    return;
  }
  if (pwdForm.new_password !== pwdForm.confirm_password) {
    ElMessage.warning("两次输入的新密码不一致");
    return;
  }
  pwdLoading.value = true;
  try {
    await changePassword(pwdForm.current_password, pwdForm.new_password);
    ElMessage.success("密码已修改，请重新登录");
    window.localStorage.removeItem("hms-token");
    window.localStorage.removeItem("hms-role");
    window.localStorage.removeItem("hms-phone");
    window.location.href = "/login";
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "修改失败");
  } finally {
    pwdLoading.value = false;
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.card-header small {
  color: #94a3b8;
}
</style>
