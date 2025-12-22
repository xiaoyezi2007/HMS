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
        <el-table-column label="历史病历" width="130">
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
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !inpatients.length" description="暂无在院患者" />
    </el-card>

    <el-dialog v-model="detailVisible" title="住院表" width="460px" destroy-on-close>
      <div v-if="detailItem">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="患者">{{ detailItem.patient_name }}</el-descriptions-item>
          <el-descriptions-item label="病房号">{{ detailItem.ward_id }}</el-descriptions-item>
          <el-descriptions-item label="病房类型">{{ detailItem.ward_type }}</el-descriptions-item>
          <el-descriptions-item label="入院时间">{{ formatDate(detailItem.in_date) }}</el-descriptions-item>
          <el-descriptions-item label="已住院">{{ formatStay(detailItem.stay_hours) }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="detailItem && openHistoryDialog(detailItem)">查看历史病历</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="taskVisible" title="添加护理任务" width="840px" destroy-on-close class="task-plan-dialog">
      <el-alert
        class="plan-hint"
        type="info"
        show-icon
        title="可一次性配置多条护理计划，系统会按频次自动拆分成具体任务"
      />
      <el-empty v-if="!taskPlans.length" description="暂未添加护理计划" class="plan-empty">
        <template #extra>
          <el-button type="primary" @click="addPlan()">新增护理计划</el-button>
        </template>
      </el-empty>
      <div v-else class="plan-collapse-wrapper">
        <el-collapse v-model="activePlanPanel" accordion class="plan-collapse">
          <el-collapse-item v-for="(plan, index) in taskPlans" :key="plan.uid" :name="plan.uid">
            <template #title>
              <div class="plan-collapse-title">
                <span>计划 {{ index + 1 }} · {{ planTypeMetaMap[plan.type]?.label || plan.type }}</span>
                <el-tag size="small" type="info">{{ plan.type }}</el-tag>
                <span class="plan-start">开始：{{ formatDate(plan.start_time) }}</span>
                <el-button type="text" size="small" @click.stop="removePlan(plan.uid)">删除</el-button>
              </div>
            </template>
            <el-form label-width="120px" class="plan-form">
              <el-row :gutter="16">
                <el-col :xs="24" :sm="12">
                  <el-form-item label="项目类型">
                    <el-select v-model="plan.type" placeholder="选择项目" teleported @change="onPlanTypeChange(plan)">
                      <el-option v-for="item in planTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12">
                  <el-form-item label="开始执行时间">
                    <el-date-picker
                      v-model="plan.start_time"
                      type="datetime"
                      placeholder="选择开始时间"
                      value-format="YYYY-MM-DDTHH:mm:ss"
                      format="YYYY-MM-DD HH:mm"
                      teleported
                      :disabled-date="disablePast"
                      style="width: 100%"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :xs="24" :sm="12">
                  <el-form-item label="持续天数">
                    <el-input-number v-model="plan.duration_days" :min="1" :max="30" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12">
                  <el-form-item label="频次模式">
                    <el-radio-group v-model="plan.frequencyMode" size="small" @change="onFrequencyModeChange(plan)">
                      <el-radio-button label="daily">每天 N 次</el-radio-button>
                      <el-radio-button label="interval">每 N 天一次</el-radio-button>
                    </el-radio-group>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item v-if="plan.frequencyMode === 'daily'" label="每天次数">
                <el-radio-group v-model="plan.times_per_day" size="small">
                  <el-radio-button :label="1">每天一次</el-radio-button>
                  <el-radio-button :label="2">每天两次</el-radio-button>
                  <el-radio-button :label="3">每天三次</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-else label="间隔天数">
                <el-input-number v-model="plan.interval_days" :min="1" :max="30" />
              </el-form-item>

              <el-form-item v-if="requiresDetail(plan.type)" label="项目详情">
                <el-input
                  v-model="plan.detail"
                  type="textarea"
                  :rows="3"
                  placeholder="请填写针灸/手术的部位、要点与注意事项"
                />
              </el-form-item>

              <div v-if="requiresMedicines(plan.type)" class="plan-medicine-panel">
                <div class="plan-subtitle">
                  <span>药品与用法</span>
                  <el-button size="small" type="primary" link @click="addMedicineRow(plan)">
                    添加药品
                  </el-button>
                </div>
                <el-empty v-if="!plan.medicines.length" description="暂未添加药品" />
                <el-table v-else :data="plan.medicines" size="small" border>
                  <el-table-column label="药品" min-width="220">
                    <template #default="{ row }">
                      <el-select
                        v-model="row.medicine_id"
                        filterable
                        placeholder="选择药品"
                        :loading="medicineLoading"
                        teleported
                      >
                        <el-option
                          v-for="med in medicineOptions"
                          :key="med.medicine_id"
                          :label="`${med.name} · 库存 ${med.stock}`"
                          :value="med.medicine_id"
                        />
                      </el-select>
                    </template>
                  </el-table-column>
                  <el-table-column label="数量" width="140">
                    <template #default="{ row }">
                      <el-input-number v-model="row.quantity" :min="1" :max="20" />
                    </template>
                  </el-table-column>
                  <el-table-column label="用法" min-width="220">
                    <template #default="{ row }">
                      <el-input v-model="row.usage" placeholder="剂量 / 途径 / 频次" />
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="90" align="center">
                    <template #default="{ row }">
                      <el-button type="text" size="small" @click="removeMedicineRow(plan, row.uid)">移除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-form>
          </el-collapse-item>
        </el-collapse>
      </div>
      <div class="plan-add-toolbar">
        <span>快速添加：</span>
        <el-space wrap>
          <el-button size="small" @click="addPlan()" plain>默认计划</el-button>
          <el-button
            v-for="item in planTypeOptions"
            :key="item.value"
            size="small"
            type="primary"
            plain
            @click="addPlan(item.value)"
          >
            {{ item.label }}
          </el-button>
        </el-space>
      </div>
      <template #footer>
        <el-button @click="taskVisible = false" :disabled="taskSubmitting">取消</el-button>
        <el-button type="primary" :loading="taskSubmitting" @click="submitTask">生成任务</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="historyDialogVisible"
      :title="'历史病历'"
      width="780px"
      destroy-on-close
    >
      <div v-if="historyContext" class="history-header">
        <div class="history-name">{{ historyContext.patient_name }}</div>
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
  createNurseTasks,
  fetchDoctorInpatients,
  fetchPatientRegistrationHistory,
  fetchDoctorRegistrationDetail,
  type DoctorInpatientItem,
  type NurseTaskBatchCreatePayload,
  type NurseTaskPlanPayload,
  type DoctorPatientRegistrationHistoryItem,
  type DoctorRegistrationDetail,
  type HistoryRange
} from "../../api/modules/doctor";
import { fetchMedicines, type MedicineItem } from "../../api/modules/pharmacy";

const inpatients = ref<DoctorInpatientItem[]>([]);
const loading = ref(false);
const detailVisible = ref(false);
const detailItem = ref<DoctorInpatientItem | null>(null);
const taskVisible = ref(false);
const taskSubmitting = ref(false);

type PlanFrequencyMode = "daily" | "interval";

interface PlanMedicineRow {
  uid: string;
  medicine_id?: number;
  quantity: number;
  usage: string;
}

interface PlanForm {
  uid: string;
  type: NurseTaskPlanPayload["type"];
  start_time: string;
  duration_days: number;
  frequencyMode: PlanFrequencyMode;
  times_per_day: number | null;
  interval_days: number | null;
  detail: string;
  medicines: PlanMedicineRow[];
}

const planTypeOptions = [
  { label: "输液", value: "输液", requiresMedicines: true },
  { label: "吃药", value: "吃药", requiresMedicines: true },
  { label: "针灸", value: "针灸", requiresDetail: true },
  { label: "手术", value: "手术", requiresDetail: true }
];
const planTypeMetaMap = planTypeOptions.reduce<Record<string, (typeof planTypeOptions)[number]>>((acc, cur) => {
  acc[cur.value] = cur;
  return acc;
}, {});

const taskPlans = ref<PlanForm[]>([]);
const activePlanPanel = ref<string | undefined>(undefined);
const activeHospId = ref<number | null>(null);
const medicineOptions = ref<MedicineItem[]>([]);
const medicineLoading = ref(false);

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

watch(taskVisible, (visible) => {
  if (!visible) {
    taskPlans.value = [];
    activePlanPanel.value = undefined;
    activeHospId.value = null;
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
    historyError.value = err?.response?.data?.detail ?? "历史病历加载失败";
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
  taskPlans.value = [createEmptyPlan()];
  activePlanPanel.value = taskPlans.value[0]?.uid;
  void ensureMedicinesLoaded();
  taskVisible.value = true;
}

function requiresMedicines(type: string) {
  return Boolean(planTypeMetaMap[type]?.requiresMedicines);
}

function requiresDetail(type: string) {
  return Boolean(planTypeMetaMap[type]?.requiresDetail);
}

function createMedicineRow(): PlanMedicineRow {
  return {
    uid: `med-${Math.random().toString(36).slice(2, 8)}${Date.now()}`,
    quantity: 1,
    usage: ""
  };
}

function createEmptyPlan(type: PlanForm["type"] = "输液"): PlanForm {
  const plan: PlanForm = {
    uid: `plan-${Math.random().toString(36).slice(2, 8)}${Date.now()}`,
    type,
    start_time: formatDateTimeLocal(),
    duration_days: 1,
    frequencyMode: "daily",
    times_per_day: 1,
    interval_days: null,
    detail: "",
    medicines: []
  };
  if (requiresMedicines(type)) {
    plan.medicines.push(createMedicineRow());
  }
  return plan;
}

async function ensureMedicinesLoaded() {
  if (medicineOptions.value.length || medicineLoading.value) return;
  medicineLoading.value = true;
  try {
    const { data } = await fetchMedicines();
    medicineOptions.value = data;
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "加载药品列表失败");
  } finally {
    medicineLoading.value = false;
  }
}

function addPlan(type?: PlanForm["type"]) {
  const plan = createEmptyPlan(type ?? "输液");
  taskPlans.value.push(plan);
  activePlanPanel.value = plan.uid;
}

function removePlan(uid: string) {
  const idx = taskPlans.value.findIndex((plan) => plan.uid === uid);
  if (idx !== -1) {
    taskPlans.value.splice(idx, 1);
  }
  activePlanPanel.value = taskPlans.value[0]?.uid;
}

function onPlanTypeChange(plan: PlanForm) {
  if (!requiresMedicines(plan.type)) {
    plan.medicines.splice(0, plan.medicines.length);
  }
  if (!requiresDetail(plan.type)) {
    plan.detail = "";
  }
}

function addMedicineRow(plan: PlanForm) {
  plan.medicines.push(createMedicineRow());
}

function removeMedicineRow(plan: PlanForm, rowUid: string) {
  const idx = plan.medicines.findIndex((row) => row.uid === rowUid);
  if (idx !== -1) {
    plan.medicines.splice(idx, 1);
  }
}

function getMedicineName(id?: number) {
  if (!id) return "";
  const item = medicineOptions.value.find((m) => m.medicine_id === id);
  return item?.name ?? "";
}

function onFrequencyModeChange(plan: PlanForm) {
  if (plan.frequencyMode === "daily") {
    plan.times_per_day = plan.times_per_day && [1, 2, 3].includes(plan.times_per_day) ? plan.times_per_day : 1;
  } else {
    plan.interval_days = plan.interval_days ?? 1;
  }
}

function disablePast(date: Date) {
  return date.getTime() < Date.now() - 60 * 1000;
}

function validatePlans(): string | null {
  if (!taskPlans.value.length) {
    return "请至少添加一个护理计划";
  }
  const now = Date.now();
  for (let i = 0; i < taskPlans.value.length; i += 1) {
    const plan = taskPlans.value[i];
    const label = `计划 ${i + 1}`;
    if (!plan.start_time) {
      return `${label} 缺少开始时间`;
    }
    if (new Date(plan.start_time).getTime() <= now) {
      return `${label} 的开始时间需晚于当前时间`;
    }
    if (!plan.duration_days || plan.duration_days < 1) {
      return `${label} 的持续天数需大于 0`;
    }
    if (plan.frequencyMode === "daily") {
      if (!plan.times_per_day || ![1, 2, 3].includes(plan.times_per_day)) {
        return `${label} 的每天次数仅支持 1、2 或 3 次`;
      }
      plan.interval_days = null;
    } else {
      if (!plan.interval_days || plan.interval_days < 1) {
        return `${label} 的间隔天数需大于 0`;
      }
      plan.times_per_day = null;
    }
    if (requiresMedicines(plan.type)) {
      if (!plan.medicines.length) {
        return `${label} 请添加至少一种药品`;
      }
      for (const med of plan.medicines) {
        if (!med.medicine_id) {
          return `${label} 存在未选择的药品`;
        }
        if (med.quantity <= 0) {
          return `${label} 的药品数量需大于 0`;
        }
        if (!med.usage.trim()) {
          return `${label} 的药品用法不能为空`;
        }
      }
    }
    if (requiresDetail(plan.type) && !plan.detail.trim()) {
      return `${label} 需填写详情说明`;
    }
  }
  return null;
}

function buildTaskPayload(): NurseTaskBatchCreatePayload {
  const plans: NurseTaskPlanPayload[] = taskPlans.value.map((plan) => {
    const payload: NurseTaskPlanPayload = {
      type: plan.type,
      start_time: plan.start_time,
      duration_days: plan.duration_days,
      detail: plan.detail.trim() || undefined,
      medicines: requiresMedicines(plan.type)
        ? plan.medicines.map((med) => ({
            medicine_id: med.medicine_id!,
            name: getMedicineName(med.medicine_id),
            quantity: med.quantity,
            usage: med.usage.trim(),
          }))
        : []
    };
    if (plan.frequencyMode === "daily") {
      payload.times_per_day = plan.times_per_day ?? 1;
    } else {
      payload.interval_days = plan.interval_days ?? 1;
    }
    return payload;
  });
  return { plans };
}

async function submitTask() {
  if (!activeHospId.value) return;
  const validationError = validatePlans();
  if (validationError) {
    ElMessage.error(validationError);
    return;
  }
  taskSubmitting.value = true;
  try {
    const payload = buildTaskPayload();
    const { data } = await createNurseTasks(activeHospId.value, payload);
    const count = data?.created ?? payload.plans.length;
    ElMessage.success(`已生成 ${count} 条护理任务`);
    taskVisible.value = false;
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "创建护理任务失败");
  } finally {
    taskSubmitting.value = false;
  }
}

onMounted(() => {
  void loadInpatients();
  void ensureMedicinesLoaded();
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

.task-plan-dialog :deep(.el-dialog__body) {
  max-height: 70vh;
  overflow-y: auto;
}

.plan-hint {
  margin-bottom: 12px;
}

.plan-empty {
  margin: 24px 0;
}

.plan-collapse-wrapper {
  max-height: 420px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.plan-collapse-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plan-collapse-title .plan-start {
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.plan-form {
  padding: 12px 0;
}

.plan-medicine-panel {
  margin-top: 8px;
}

.plan-subtitle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  margin-bottom: 8px;
}

.plan-add-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
