<template>
  <div class="doctor-board">
    <el-alert type="success" show-icon :closable="false">
      <template #title>待诊列表</template>
      你守护生命的样子，就是人间最美的风景。祝您工作顺利！
    </el-alert>

    <el-card class="mt-3">
      <el-table :data="schedule" stripe size="large">
        <el-table-column label="患者" min-width="150" align="center">
          <template #default="scope">
            <el-button type="text" @click.stop="openPatientDialog(scope.row.patient_id)">
              {{ patientNames[scope.row.patient_id] ? `患者：${patientNames[scope.row.patient_id]}` : "患者信息加载中" }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="reg_type" label="号别" min-width="150" align="center" />
        <el-table-column prop="fee" label="费用" min-width="150" align="center">
          <template #default="scope">
            ￥{{ scope.row.fee.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="就诊时间" min-width="150" align="center">
          <template #default="scope">
            <span>{{ formatDateText(scope.row.visit_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="150" align="center">
          <template #default="scope">
            <el-button v-if="scope.row.status === '排队中'" size="small" type="info" @click="onStart(scope.row)">开始办理</el-button>
            <el-button v-else-if="scope.row.status === '就诊中'" size="small" type="warning" @click="onStart(scope.row)">开始就诊</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="patientDialogVisible" title="病人信息" width="420px">
      <div v-if="patientLoading" style="text-align:center; padding:20px">
        <el-spin />
      </div>
      <div v-else>
        <el-descriptions :column="1">
          <el-descriptions-item label="姓名">{{ patientDetail?.name }}</el-descriptions-item>
          <el-descriptions-item label="性别">{{ patientDetail?.gender }}</el-descriptions-item>
          <el-descriptions-item label="出生日期">{{ patientDetail?.birth_date }}</el-descriptions-item>
          <el-descriptions-item label="身份证号">{{ patientDetail?.id_number }}</el-descriptions-item>
          <el-descriptions-item label="电话">{{ patientDetail?.phone }}</el-descriptions-item>
          <el-descriptions-item label="地址">{{ patientDetail?.address }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="patientDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 书写病历对话框已移至接诊页（ConsultationView），列表页不再提供 -->
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { fetchDoctorSchedule, type RegistrationItem } from "../../api/modules/doctor";
import { fetchPatientById, type PatientProfileResponse } from "../../api/modules/patient";
import { useRouter } from "vue-router";

const schedule = ref<RegistrationItem[]>([]);
const router = useRouter();

const patientDialogVisible = ref(false);
const patientLoading = ref(false);
const patientDetail = ref<PatientProfileResponse | null>(null);
const patientNames = ref<Record<number, string>>({});

function formatDateTimeText(value?: unknown) {
  if (value === undefined || value === null) return "-";
  return String(value).replace("T", " ");
}

function formatDateText(value?: unknown) {
  if (value === undefined || value === null) return "-";
  return String(value).split("T")[0];
}

async function loadSchedule() {
  const { data } = await fetchDoctorSchedule();
  schedule.value = data;
  await loadPatientNames(data);
}

// 书写病历入口已移至接诊页（ConsultationView）

// 点击「开具处方」按钮的处理逻辑：若已存在病历则直接跳转；否则先打开病历写入对话框并在提交后跳转
// 开具处方入口已移至接诊页（ConsultationView）

// 患者详情弹窗逻辑已移除，列表页保持精简

// 开始办理
async function onStart(row: RegistrationItem) {
  // 导航到接诊页，由接诊页负责调用 startHandling 并展示后续操作按钮
  router.push({ path: `/workspace/consultation/${row.reg_id}`, query: { patient_id: String(row.patient_id) } });
}

// 完成办理现在在接诊页统一执行，列表页不提供该操作
// 列表页不提供完成办理操作

onMounted(() => {
  loadSchedule();
});

async function openPatientDialog(patientId: number) {
  patientDialogVisible.value = true;
  patientLoading.value = true;
  patientDetail.value = null;
  try {
    const { data } = await fetchPatientById(patientId);
    patientDetail.value = data;
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "获取病人信息失败");
    patientDialogVisible.value = false;
  } finally {
    patientLoading.value = false;
  }
}

async function loadPatientNames(items: RegistrationItem[]) {
  const ids = Array.from(new Set(items.map((i) => i.patient_id).filter(Boolean)));
  const tasks = ids.map(async (id) => {
    if (patientNames.value[id]) return;
    try {
      const { data } = await fetchPatientById(id);
      patientNames.value = { ...patientNames.value, [id]: data.name };
    } catch (err) {
      // 忽略单个患者加载失败，保持表格可用
    }
  });
  await Promise.allSettled(tasks);
}
</script>

<style scoped>
.doctor-board {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mt-3 {
  margin-top: 16px;
}
</style>
