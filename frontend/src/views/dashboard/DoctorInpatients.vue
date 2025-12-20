<template>
  <div class="doctor-inpatients">
    <el-card class="header-card">
      <div class="card-header">
        <div>
          <div class="title">住院管理</div>
          <div class="sub">查看由你负责的在院患者，便于随访与出院决策</div>
        </div>
        <div class="actions">
          <el-button type="primary" plain :loading="loading" @click="loadInpatients">刷新列表</el-button>
        </div>
      </div>
      <div class="stats">
        <div class="stat">
          <span class="stat-label">在院人数</span>
          <span class="stat-value">{{ inpatients.length }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">平均住院时长</span>
          <span class="stat-value">{{ avgStay }}</span>
        </div>
      </div>
    </el-card>

    <el-card class="table-card">
      <el-table :data="inpatients" stripe v-loading="loading">
        <el-table-column label="患者姓名" min-width="160">
          <template #default="scope">
            <div class="patient-name">{{ scope.row.patient_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="ward_id" label="病房号" width="120" />
        <el-table-column label="住院单" width="130">
          <template #default="scope">
            <div class="hosp-ticket">
              <el-button size="small" type="primary" link @click="openHospDetail(scope.row)">查看</el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="ward_type" label="病房类型" width="140" />
        <el-table-column label="入院时间" min-width="200">
          <template #default="scope">
            {{ formatDate(scope.row.in_date) }}
          </template>
        </el-table-column>
        <el-table-column label="已住院" width="140">
          <template #default="scope">
            {{ formatStay(scope.row.stay_hours) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" link @click="openTaskDialog(scope.row)">添加护理任务</el-button>
            <el-button size="small" type="primary" link @click="goToConsultation(scope.row)">查看接诊记录</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !inpatients.length" description="暂无在院患者" />
    </el-card>

    <el-dialog v-model="detailVisible" title="住院单" width="460px" destroy-on-close>
      <div v-if="detailItem">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="患者">{{ detailItem.patient_name }} (ID: {{ detailItem.patient_id }})</el-descriptions-item>
          <el-descriptions-item label="病房号">{{ detailItem.ward_id }}</el-descriptions-item>
          <el-descriptions-item label="病房类型">{{ detailItem.ward_type }}</el-descriptions-item>
          <el-descriptions-item label="入院时间">{{ formatDate(detailItem.in_date) }}</el-descriptions-item>
          <el-descriptions-item label="已住院">{{ formatStay(detailItem.stay_hours) }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="goToConsultation(detailItem!)">查看接诊记录</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="taskVisible" title="添加护理任务" width="500px" destroy-on-close>
      <el-form :model="taskForm" label-width="120px">
        <el-form-item label="项目名称">
          <el-select v-model="taskForm.type" placeholder="选择护理任务" teleported>
            <el-option v-for="item in taskOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="预计完成时间">
          <el-date-picker
            v-model="taskForm.time"
            type="datetime"
            placeholder="选择完成时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            format="YYYY-MM-DD HH:mm"
            teleported
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskVisible = false" :disabled="taskSubmitting">取消</el-button>
        <el-button type="primary" :loading="taskSubmitting" @click="submitTask">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import { createNurseTask, fetchDoctorInpatients, type DoctorInpatientItem, type NurseTaskCreatePayload } from "../../api/modules/doctor";

const router = useRouter();
const inpatients = ref<DoctorInpatientItem[]>([]);
const loading = ref(false);
const detailVisible = ref(false);
const detailItem = ref<DoctorInpatientItem | null>(null);
const taskVisible = ref(false);
const taskSubmitting = ref(false);
const taskForm = ref<NurseTaskCreatePayload>({ type: "输液", time: formatDateTimeLocal() });
const taskOptions = [
  { label: "输液", value: "输液" },
  { label: "吃药", value: "吃药" },
  { label: "针灸", value: "针灸" },
  { label: "手术", value: "手术" },
];
const activeHospId = ref<number | null>(null);

const avgStay = computed(() => {
  if (!inpatients.value.length) return "0 小时";
  const hours = inpatients.value.reduce((sum, item) => sum + item.stay_hours, 0) / inpatients.value.length;
  return `${hours.toFixed(1)} 小时`;
});

function formatDate(val: string) {
  return new Date(val).toLocaleString();
}

function formatStay(hours: number) {
  if (hours < 24) {
    return `${hours.toFixed(1)} 小时`;
  }
  const days = Math.floor(hours / 24);
  const rem = hours % 24;
  return rem > 0 ? `${days} 天 ${rem.toFixed(1)} 小时` : `${days} 天`;
}

async function loadInpatients() {
  loading.value = true;
  try {
    const { data } = await fetchDoctorInpatients();
    inpatients.value = data;
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "加载在院患者失败");
  } finally {
    loading.value = false;
  }
}

function goToConsultation(row: DoctorInpatientItem) {
  router.push({ path: `/workspace/consultation/${row.reg_id}`, query: { patient_id: String(row.patient_id) } });
}

function openHospDetail(row: DoctorInpatientItem) {
  detailItem.value = row;
  detailVisible.value = true;
}

function formatDateTimeLocal(date = new Date()) {
  const pad = (val: number) => val.toString().padStart(2, "0");
  const y = date.getFullYear();
  const m = pad(date.getMonth() + 1);
  const d = pad(date.getDate());
  const h = pad(date.getHours());
  const mi = pad(date.getMinutes());
  const s = pad(date.getSeconds());
  return `${y}-${m}-${d}T${h}:${mi}:${s}`;
}

function openTaskDialog(row: DoctorInpatientItem) {
  activeHospId.value = row.hosp_id;
  taskForm.value = { type: taskForm.value.type || "输液", time: formatDateTimeLocal() };
  taskVisible.value = true;
}

async function submitTask() {
  if (!activeHospId.value) return;
  taskSubmitting.value = true;
  try {
    await createNurseTask(activeHospId.value, taskForm.value);
    ElMessage.success("护理任务已创建");
    taskVisible.value = false;
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "创建护理任务失败");
  } finally {
    taskSubmitting.value = false;
  }
}

onMounted(() => {
  void loadInpatients();
});
</script>

<style scoped>
.doctor-inpatients {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-card {
  border: none;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.title {
  font-size: 20px;
  font-weight: 700;
}

.sub {
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.actions {
  display: flex;
  gap: 8px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.stat {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
}

.stat-label {
  display: block;
  color: #475569;
  font-size: 13px;
  margin-bottom: 6px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.table-card {
  border: none;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04);
}

.patient-name {
  font-weight: 600;
}

.patient-meta {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.hosp-ticket {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
