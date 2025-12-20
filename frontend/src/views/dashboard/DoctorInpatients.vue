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
            <el-button size="small" type="primary" link @click="openHistoryDialog(scope.row)">查看接诊记录</el-button>
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
        <el-button type="primary" @click="detailItem && openHistoryDialog(detailItem)">查看接诊记录</el-button>
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

    <el-dialog
      v-model="historyDialogVisible"
      :title="historyContext ? `接诊记录 · ${historyContext.patient_name}` : '接诊记录'"
      width="780px"
      destroy-on-close
    >
      <div v-if="historyContext" class="history-header">
        <div>
          <div class="history-name">{{ historyContext.patient_name }}</div>
          <div class="history-meta">患者 ID：{{ historyContext.patient_id }}</div>
        </div>
        <el-radio-group v-model="historyRange" size="small" class="history-range">
          <el-radio-button label="current">本次挂号</el-radio-button>
          <el-radio-button label="7d">近 7 天</el-radio-button>
          <el-radio-button label="30d">近 1 个月</el-radio-button>
        </el-radio-group>
      </div>
      <el-alert
        v-if="historyError"
        class="history-alert"
        type="error"
        show-icon
        closable
        :title="historyError"
        @close="historyError = ''"
      />
      <el-skeleton v-if="historyLoading" :rows="5" animated />
      <el-empty v-else-if="!historyItems.length" description="暂无符合条件的挂号" />
      <el-collapse v-else v-model="historyActivePanels" class="history-collapse" accordion>
        <el-collapse-item v-for="item in historyItems" :key="item.reg_id" :name="String(item.reg_id)">
          <template #title>
            <div class="history-title">
              <span>#{{ item.reg_id }}</span>
              <span class="history-date">{{ formatDate(item.reg_date) }}</span>
              <el-tag size="small" type="info">{{ normalizeRegStatus(item.status) }}</el-tag>
              <el-tag v-if="item.is_current" size="small" type="success">本次</el-tag>
              <el-tag size="small" type="warning">{{ item.reg_type }}</el-tag>
            </div>
          </template>
          <div class="history-body">
            <p><strong>主诉：</strong>{{ item.record?.complaint || "尚未填写" }}</p>
            <p><strong>诊断：</strong>{{ item.record?.diagnosis || "尚未填写" }}</p>
            <p><strong>建议：</strong>{{ item.record?.suggestion || "—" }}</p>
            <div class="history-body-meta">
              <span>就诊日期：{{ item.visit_date ? formatDate(item.visit_date) : "-" }}</span>
              <span>费用：{{ formatCurrency(item.fee) }}</span>
            </div>
            <div class="history-actions">
              <el-button size="small" @click="viewRegistrationDetail(item.reg_id)">查看详情</el-button>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-dialog>

    <el-drawer
      v-model="registrationDetailVisible"
      title="挂号详情"
      size="640px"
      destroy-on-close
      append-to-body
    >
      <el-skeleton v-if="registrationDetailLoading" :rows="6" animated />
      <div v-else-if="registrationDetail" class="detail-scroll">
        <section class="detail-section">
          <h4>挂号信息</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="挂号号">{{ registrationDetail.registration.reg_id }}</el-descriptions-item>
            <el-descriptions-item label="号别">{{ registrationDetail.registration.reg_type }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ normalizeRegStatus(registrationDetail.registration.status) }}</el-descriptions-item>
            <el-descriptions-item label="费用">{{ formatCurrency(registrationDetail.registration.fee) }}</el-descriptions-item>
            <el-descriptions-item label="挂号时间">{{ formatDate(registrationDetail.registration.reg_date) }}</el-descriptions-item>
            <el-descriptions-item label="就诊日期">{{ registrationDetail.registration.visit_date ? formatDate(registrationDetail.registration.visit_date) : "-" }}</el-descriptions-item>
          </el-descriptions>
        </section>

        <section class="detail-section">
          <h4>病历摘要</h4>
          <div v-if="registrationDetail.record">
            <p><strong>主诉：</strong>{{ registrationDetail.record.complaint }}</p>
            <p><strong>诊断：</strong>{{ registrationDetail.record.diagnosis }}</p>
            <p><strong>建议：</strong>{{ registrationDetail.record.suggestion || "—" }}</p>
          </div>
          <el-empty v-else description="尚未书写病历" />
        </section>

        <section class="detail-section">
          <h4>处方</h4>
          <div v-if="registrationDetail.prescriptions.length">
            <el-collapse accordion>
              <el-collapse-item
                v-for="pres in registrationDetail.prescriptions"
                :key="pres.pres_id"
                :title="`处方 ${pres.pres_id} · ${formatCurrency(pres.total_amount)}`"
                :name="String(pres.pres_id)"
              >
                <el-table :data="pres.details" size="small" border>
                  <el-table-column prop="medicine_name" label="药品" />
                  <el-table-column prop="quantity" label="数量" width="80" />
                  <el-table-column prop="usage" label="用法" />
                </el-table>
              </el-collapse-item>
            </el-collapse>
          </div>
          <el-empty v-else description="暂无处方" />
        </section>

        <section class="detail-section">
          <h4>检查</h4>
          <div v-if="registrationDetail.exams.length">
            <el-table :data="registrationDetail.exams" size="small" border>
              <el-table-column prop="type" label="检查类型" />
              <el-table-column prop="result" label="结果" />
              <el-table-column label="时间">
                <template #default="{ row }">{{ row.date ? formatDate(row.date) : "-" }}</template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="暂无检查记录" />
        </section>
      </div>
      <div v-else class="detail-empty">
        <el-empty description="未加载到挂号详情" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  createNurseTask,
  fetchDoctorInpatients,
  fetchPatientRegistrationHistory,
  fetchDoctorRegistrationDetail,
  type DoctorInpatientItem,
  type NurseTaskCreatePayload,
  type DoctorPatientRegistrationHistoryItem,
  type DoctorRegistrationDetail,
  type HistoryRange
} from "../../api/modules/doctor";

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

type HistoryContext = { patient_id: number; patient_name: string; current_reg_id: number };

const historyDialogVisible = ref(false);
const historyRange = ref<HistoryRange>("current");
const historyItems = ref<DoctorPatientRegistrationHistoryItem[]>([]);
const historyContext = ref<HistoryContext | null>(null);
const historyLoading = ref(false);
const historyError = ref("");
const historyActivePanels = ref<string[]>([]);

const registrationDetailVisible = ref(false);
const registrationDetailLoading = ref(false);
const registrationDetail = ref<DoctorRegistrationDetail | null>(null);

const avgStay = computed(() => {
  if (!inpatients.value.length) return "0 小时";
  const hours = inpatients.value.reduce((sum, item) => sum + item.stay_hours, 0) / inpatients.value.length;
  return `${hours.toFixed(1)} 小时`;
});

watch(historyItems, (items) => {
  historyActivePanels.value = items.length ? [String(items[0].reg_id)] : [];
});

watch(historyRange, () => {
  if (historyDialogVisible.value) {
    void loadHistory();
  }
});

watch(historyDialogVisible, (visible) => {
  if (!visible) {
    historyItems.value = [];
    historyError.value = "";
    historyContext.value = null;
  }
});

function formatDate(val?: string | null) {
  if (!val) {
    return "-";
  }
  return new Date(val).toLocaleString();
}

function formatCurrency(value?: number | null) {
  const amount = Number(value ?? 0);
  return `￥${amount.toFixed(2)}`;
}

function normalizeRegStatus(value?: string | null) {
  if (!value) return "未知";
  const map: Record<string, string> = {
    WAITING: "排队中",
    IN_PROGRESS: "就诊中",
    FINISHED: "已完成",
    CANCELLED: "已取消",
    EXPIRED: "已过期",
    排队中: "排队中",
    就诊中: "就诊中",
    已完成: "已完成",
    已取消: "已取消",
    已过期: "已过期"
  };
  return map[value] || value;
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

function openHistoryDialog(row: DoctorInpatientItem) {
  historyContext.value = {
    patient_id: row.patient_id,
    patient_name: row.patient_name,
    current_reg_id: row.reg_id
  };
  historyRange.value = "current";
  historyDialogVisible.value = true;
  void loadHistory();
}

async function loadHistory() {
  if (!historyContext.value) {
    return;
  }
  historyLoading.value = true;
  historyError.value = "";
  const params: { range: HistoryRange; current_reg_id?: number } = { range: historyRange.value };
  if (historyContext.value.current_reg_id) {
    params.current_reg_id = historyContext.value.current_reg_id;
  }
  try {
    const { data } = await fetchPatientRegistrationHistory(historyContext.value.patient_id, params);
    historyItems.value = data;
  } catch (err: any) {
    historyItems.value = [];
    historyError.value = err?.response?.data?.detail ?? "接诊记录加载失败";
    ElMessage.error(historyError.value);
  } finally {
    historyLoading.value = false;
  }
}

async function viewRegistrationDetail(regId: number) {
  registrationDetailVisible.value = true;
  registrationDetailLoading.value = true;
  try {
    const { data } = await fetchDoctorRegistrationDetail(regId);
    registrationDetail.value = {
      ...data,
      prescriptions: data.prescriptions ?? [],
      exams: data.exams ?? []
    };
  } catch (err: any) {
    registrationDetailVisible.value = false;
    const message = err?.response?.data?.detail ?? "加载挂号详情失败";
    ElMessage.error(message);
  } finally {
    registrationDetailLoading.value = false;
  }
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

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 12px;
}

.history-name {
  font-size: 18px;
  font-weight: 600;
}

.history-meta {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.history-range {
  flex-shrink: 0;
}

.history-alert {
  margin-bottom: 12px;
}

.history-collapse {
  max-height: 420px;
  overflow: auto;
}

.history-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-date {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.history-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
}

.history-body-meta {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.history-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.detail-scroll {
  max-height: 75vh;
  overflow: auto;
  padding-right: 6px;
}

.detail-section {
  margin-bottom: 18px;
}

.detail-section h4 {
  margin-bottom: 8px;
  font-weight: 600;
}

.detail-empty {
  padding: 24px 0;
}
</style>
