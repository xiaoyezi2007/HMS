<template>
  <div class="patient-panel">
    <el-row :gutter="16">
      <el-col :md="12" :sm="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>完善个人档案</span>
              <small>首次挂号前需提交实名信息</small>
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
              <el-date-picker v-model="profileForm.birth_date" type="date" placeholder="请选择" />
            </el-form-item>
            <el-form-item label="身份证">
              <el-input v-model="profileForm.id_number" maxlength="18" placeholder="18 位身份证号" />
            </el-form-item>
            <el-form-item label="联系地址">
              <el-input v-model="profileForm.address" type="textarea" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="profileLoading" @click="submitProfile">提交档案</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :md="12" :sm="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>智能挂号</span>
              <small>按科室 / 医生 / 号别进行预约</small>
            </div>
          </template>
          <el-form label-width="80px">
            <el-form-item label="科室">
              <el-select v-model="regForm.dept_id" placeholder="请选择科室" @change="onDeptChange">
                <el-option v-for="dept in departments" :key="dept.dept_id" :label="dept.dept_name" :value="dept.dept_id" />
              </el-select>
            </el-form-item>
            <el-form-item label="医生">
              <el-select v-model="regForm.doctor_id" placeholder="请选择医生" :disabled="!regForm.dept_id || doctorLoading">
                <el-option v-for="doc in doctors" :key="doc.doctor_id" :label="`${doc.name} / ${doc.title}`" :value="doc.doctor_id" />
              </el-select>
            </el-form-item>
            <el-form-item label="号别">
              <el-radio-group v-model="regForm.reg_type">
                <el-radio-button label="普通号" />
                <el-radio-button label="专家号" />
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button type="success" :loading="regLoading" @click="submitRegistration">提交挂号</el-button>
            </el-form-item>
          </el-form>
          <el-divider content-position="left">科室一览</el-divider>
          <el-table :data="departments" size="small" height="240px">
            <el-table-column prop="dept_name" label="科室" />
            <el-table-column prop="telephone" label="咨询电话" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  createPatientProfile,
  fetchDepartments,
  fetchDoctors,
  createRegistration,
  type Department,
  type DoctorItem
} from "../../api/modules/patient";

const profileForm = reactive({
  name: "",
  gender: "男",
  birth_date: "",
  id_number: "",
  address: ""
});
const profileLoading = ref(false);

const departments = ref<Department[]>([]);
const doctors = ref<DoctorItem[]>([]);
const doctorLoading = ref(false);

const regForm = reactive({
  dept_id: undefined as number | undefined,
  doctor_id: undefined as number | undefined,
  reg_type: "普通号"
});
const regLoading = ref(false);

async function loadDepartments() {
  const { data } = await fetchDepartments();
  departments.value = data;
}

async function onDeptChange(deptId: number) {
  if (!deptId) {
    doctors.value = [];
    return;
  }
  doctorLoading.value = true;
  try {
    const { data } = await fetchDoctors(deptId);
    doctors.value = data;
  } finally {
    doctorLoading.value = false;
  }
}

async function submitProfile() {
  if (!profileForm.name || !profileForm.birth_date || !profileForm.id_number) {
    ElMessage.warning("请完整填写档案信息");
    return;
  }
  profileLoading.value = true;
  try {
    await createPatientProfile({ ...profileForm });
    ElMessage.success("档案提交成功");
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail ?? "提交失败");
  } finally {
    profileLoading.value = false;
  }
}

async function submitRegistration() {
  if (!regForm.doctor_id) {
    ElMessage.warning("请选择医生");
    return;
  }
  regLoading.value = true;
  try {
    await createRegistration({ doctor_id: regForm.doctor_id, reg_type: regForm.reg_type });
    ElMessage.success("挂号成功，等待医生处理");
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail ?? "挂号失败");
  } finally {
    regLoading.value = false;
  }
}

onMounted(() => {
  loadDepartments();
});
</script>

<style scoped>
.patient-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.card-header small {
  color: #94a3b8;
}
</style>
