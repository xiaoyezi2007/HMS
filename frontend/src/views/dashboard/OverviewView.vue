<template>
  <div class="overview">
    <template v-if="isNurseRole">
      <div class="title-block">
        <div>
          <h2>病房总览</h2>
          <p class="subtitle">{{ auth.isHeadNurse ? "护士长可查看全部病房" : "仅展示您的值班病房" }}</p>
        </div>
        <el-button v-if="isLoading" type="primary" link :loading="isLoading">加载中</el-button>
      </div>
      <el-empty v-if="!isLoading && wards.length === 0" description="暂无病房数据" />
      <div v-else class="ward-grid">
        <div
          v-for="ward in wards"
          :key="ward.ward_id"
          class="ward-card"
          :class="wardCardClass(ward)"
          @click="handleWardClick(ward)"
        >
          <div class="ward-card__header">
            <div class="ward-badge">病房 {{ ward.ward_id }}</div>
            <span class="ward-type">{{ ward.ward_type }}</span>
          </div>
          <div class="ward-status">
            <div class="ward-occupancy">
              <strong>占用</strong>
              <span>{{ ward.occupied_count }} / {{ ward.bed_count }}</span>
            </div>
            <el-tag v-if="isDueSoon(ward)" type="danger" size="small" effect="dark">2 小时内有任务</el-tag>
            <el-tag v-else-if="hasPatient(ward)" type="success" size="small" effect="plain">有患者</el-tag>
            <el-tag v-else type="info" size="small" effect="plain">空房</el-tag>
          </div>
          <div class="bed-list" :style="bedGridStyle(ward)">
            <div v-for="bed in bedSlots(ward)" :key="bed" class="bed-slot">
              床 {{ bed }}
            </div>
          </div>
        </div>
      </div>

      <el-card v-if="auth.isHeadNurse" class="inpatient-card">
        <template #header>
          <div class="card-header">
            <div>
              <span>住院患者</span>
              <small>护士长可直接办理出院并生成费用</small>
            </div>
            <el-button type="primary" link @click="loadInpatients">刷新列表</el-button>
          </div>
        </template>
        <el-table
          class="inpatient-table"
          :data="inpatients"
          v-loading="inpatientsLoading"
          empty-text="当前无住院患者"
          border
          style="width: 100%"
        >
          <el-table-column prop="patient_name" label="患者姓名" min-width="140" />
          <el-table-column prop="ward_type" label="所在病房" min-width="140" />
          <el-table-column label="入院时间" min-width="180">
            <template #default="{ row }">
              {{ formatDate(row.in_date) }}
            </template>
          </el-table-column>
          <el-table-column label="已住院时长" min-width="160">
            <template #default="{ row }">
              {{ formatStayDuration(row.stay_hours) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="130">
            <template #default="{ row }">
              <el-button
                type="success"
                size="small"
                :loading="dischargeLoadingId === row.hosp_id"
                @click="handleDischarge(row)"
              >
                办理出院
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-drawer v-model="recordVisible" :title="activeWardTitle" size="40%" direction="rtl">
        <template #title>
          <div class="drawer-title">
            <span>{{ activeWardTitle }}</span>
            <el-tag size="small" type="info">病历列表</el-tag>
          </div>
        </template>
        <div v-if="recordLoading">
          <el-skeleton :rows="3" animated />
        </div>
        <el-empty v-else-if="wardRecords.length === 0" description="暂无在院病历" />
        <div v-else class="record-list">
          <el-card v-for="item in wardRecords" :key="item.record_id" shadow="hover" class="record-card">
            <div class="record-card__header">
              <div class="record-patient">{{ item.patient_name }}</div>
            </div>
            <div class="record-meta">
              <span>入院时间：{{ formatDate(item.in_date) }}</span>
            </div>
            <div class="record-field"><strong>主诉：</strong>{{ item.complaint }}</div>
            <div class="record-field"><strong>诊断：</strong>{{ item.diagnosis }}</div>
            <div class="record-field" v-if="item.suggestion"><strong>建议：</strong>{{ item.suggestion }}</div>

            <el-divider content-position="left">护理任务</el-divider>
            <el-empty
              v-if="!tasksForHosp(item.hosp_id).length"
              description="暂无护理任务"
              :image-size="60"
            />
            <el-table
              v-else
              :data="tasksForHosp(item.hosp_id)"
              size="small"
              border
              :show-header="true"
              class="task-table"
            >
              <el-table-column prop="type" label="项目" width="120" />
              <el-table-column label="时间" min-width="160">
                <template #default="scope">
                  {{ formatDate(scope.row.time) }}
                </template>
              </el-table-column>
              <el-table-column label="状态" width="110">
                <template #default="scope">
                  <el-tag :type="formatTaskStatus(scope.row.status).type" effect="plain">
                    {{ formatTaskStatus(scope.row.status).label }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="护士" width="120" prop="nurse_name" />
            </el-table>
          </el-card>
        </div>
      </el-drawer>
    </template>

    <template v-else-if="isDoctorRole">
      <div class="doctor-overview">
        <h2 class="page-title">首页</h2>
        <el-row :gutter="16">
          <el-col v-for="item in doctorShortcuts" :key="item.title" :lg="12" :md="12" :sm="12" :xs="24">
            <el-card shadow="hover" class="home-card" @click="item.onClick()">
              <div class="home-card__icon" :style="{ background: item.color }">
                <component :is="item.icon" />
              </div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.desc }}</p>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </template>
    <template v-else-if="isAdminRole">
      <div class="admin-overview">
        <div class="title-block">
          <div>
            <h2>首页</h2>
          </div>
        </div>
        <el-row :gutter="16">
          <el-col v-for="item in adminShortcuts" :key="item.title" :lg="12" :md="12" :sm="12" :xs="24">
            <el-card shadow="hover" class="admin-card" @click="item.onClick()">
              <div class="admin-card__icon" :style="{ background: item.color }">
                <component :is="item.icon" />
              </div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.desc }}</p>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </template>
    <template v-else>
      <el-page-header content="多角色联合工作台" icon="">
        <template #title>
          <span>医院管理系统</span>
        </template>
      </el-page-header>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import dayjs from "dayjs";
import { Reading, UserFilled, Suitcase, Histogram, Management, OfficeBuilding, Coin } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAuthStore } from "../../stores/auth";
import {
  fetchWardOverview,
  fetchWardRecords,
  fetchWardTasks,
  fetchHeadInpatients,
  dischargeInpatient,
  type WardOverviewItem,
  type WardRecordItem,
  type WardTaskItem,
  type InpatientItem
} from "../../api/modules/nurse";
import { useRouter } from "vue-router";

const auth = useAuthStore();
const isNurseRole = computed(() => auth.currentRole === "护士");
const isDoctorRole = computed(() => auth.currentRole === "医生");
const isAdminRole = computed(() => auth.currentRole === "管理员");
const wards = ref<WardOverviewItem[]>([]);
const wardFlags = ref<Record<number, { hasPatient: boolean; dueSoon: boolean }>>({});
const isLoading = ref(false);
const recordVisible = ref(false);
const recordLoading = ref(false);
const wardRecords = ref<WardRecordItem[]>([]);
const wardTasks = ref<WardTaskItem[]>([]);
const activeWard = ref<WardOverviewItem | null>(null);
const inpatients = ref<InpatientItem[]>([]);
const inpatientsLoading = ref(false);
const dischargeLoadingId = ref<number | null>(null);
const router = useRouter();

const featureCards = [
  {
    title: "患者门户",
    desc: "完善档案、查看科室、医生并提交挂号申请",
    icon: UserFilled,
    color: "#fce7f3"
  },
  {
    title: "就诊处理",
    desc: "处理待诊挂号、填写病历并联动处方流",
    icon: Suitcase,
    color: "#e0f2fe"
  },
  {
    title: "护士/药房",
    desc: "排班总览、药品库存与处方编制",
    icon: Reading,
    color: "#e2e8f0"
  },
  {
    title: "管理驾驶舱",
    desc: "为管理员保留扩展入口，可挂接统计与营收分析",
    icon: Histogram,
    color: "#fef3c7"
  }
];

const doctorShortcuts = [
  {
    title: "就诊处理",
    desc: "查看待诊挂号，进入接诊与处方",
    icon: Suitcase,
    color: "#e0f2fe",
    onClick: () => router.push("/workspace/doctor")
  },
  {
    title: "住院管理",
    desc: "查看在院患者，管理医嘱与任务",
    icon: Reading,
    color: "#e2e8f0",
    onClick: () => router.push("/workspace/doctor/inpatients")
  }
];

const adminShortcuts = [
  {
    title: "医护管理",
    desc: "新增、导入并管理医护账号",
    icon: Management,
    color: "#eef2ff",
    onClick: () => router.push("/workspace/admin/staff")
  },
  {
    title: "科室管理",
    desc: "新增科室与病房设置",
    icon: OfficeBuilding,
    color: "#e0f2fe",
    onClick: () => router.push("/workspace/admin/dept")
  },
  {
    title: "营收记录",
    desc: "查看结算与费用流转",
    icon: Coin,
    color: "#fef3c7",
    onClick: () => router.push("/workspace/admin/revenue")
  },
  {
    title: "操作日志",
    desc: "查看系统操作审计记录",
    icon: Reading,
    color: "#e2f3ff",
    onClick: () => router.push("/workspace/admin/logs")
  },
  {
    title: "个人主页",
    desc: "查看账号信息与密码",
    icon: UserFilled,
    color: "#e2e8f0",
    onClick: () => router.push("/workspace/admin/profile")
  }
];

async function loadWardOverview() {
  if (!isNurseRole.value) return;
  isLoading.value = true;
  try {
    const { data } = await fetchWardOverview();
    wards.value = data;
    await loadWardAlerts(data);
  } finally {
    isLoading.value = false;
  }
}

async function loadInpatients() {
  if (!auth.isHeadNurse) return;
  inpatientsLoading.value = true;
  try {
    const { data } = await fetchHeadInpatients();
    inpatients.value = data;
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "加载住院患者失败");
  } finally {
    inpatientsLoading.value = false;
  }
}

async function loadWardAlerts(list: WardOverviewItem[]) {
  const now = dayjs();
  const tasksPromises = list.map(async (ward) => {
    const hasPatient = (ward.occupied_count ?? 0) > 0;
    let dueSoon = false;
    if (hasPatient) {
      try {
        const res = await fetchWardTasks(ward.ward_id);
        dueSoon = res.data.some((t) => {
          if (t.status !== "未完成") return false;
          const diff = dayjs(t.time).diff(now, "minute");
          return diff >= 0 && diff <= 120;
        });
      } catch (e) {
        // ignore fetch errors to avoid blocking overview
      }
    }
    wardFlags.value[ward.ward_id] = { hasPatient, dueSoon };
  });
  await Promise.all(tasksPromises);
}

const activeWardTitle = computed(() => {
  if (!activeWard.value) return "病房病历";
  return `病房 ${activeWard.value.ward_id} · ${activeWard.value.ward_type}`;
});

function formatDate(val: string) {
  return new Date(val).toLocaleString();
}

function formatStayDuration(hours: number) {
  if (hours < 24) return `${hours.toFixed(1)} 小时`;
  const days = hours / 24;
  return `${days.toFixed(1)} 天`;
}

function bedSlots(ward: WardOverviewItem) {
  const count = Number(ward.bed_count) || 0;
  return Array.from({ length: count }, (_, idx) => idx + 1);
}

function bedGridStyle(ward: WardOverviewItem) {
  const count = Number(ward.bed_count) || 0;
  // 四人房固定两列，避免 1-3 分行
  if (count === 4) {
    return { gridTemplateColumns: "repeat(2, minmax(0, 1fr))" };
  }
  return {};
}

function hasPatient(ward: WardOverviewItem) {
  return (ward.occupied_count ?? 0) > 0;
}

function isDueSoon(ward: WardOverviewItem) {
  const flags = wardFlags.value[ward.ward_id];
  return Boolean(flags?.dueSoon);
}

function wardCardClass(ward: WardOverviewItem) {
  const flags = wardFlags.value[ward.ward_id];
  if (flags?.dueSoon) return "ward-due-soon";
  if (flags?.hasPatient) return "ward-has-patient";
  return "";
}

async function handleWardClick(ward: WardOverviewItem) {
  activeWard.value = ward;
  recordVisible.value = true;
  recordLoading.value = true;
  try {
    const { data } = await fetchWardRecords(ward.ward_id);
    wardRecords.value = data;
    const taskRes = await fetchWardTasks(ward.ward_id);
    wardTasks.value = taskRes.data;
  } finally {
    recordLoading.value = false;
  }
}

async function handleDischarge(row: InpatientItem) {
  try {
    await ElMessageBox.confirm(`确认为 ${row.patient_name} 办理出院并生成住院费用吗？`, "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning"
    });
  } catch {
    return;
  }

  dischargeLoadingId.value = row.hosp_id;
  try {
    const { data } = await dischargeInpatient(row.hosp_id);
    ElMessage.success(`出院完成，住院费 ¥${data.bill_amount.toFixed(2)}`);
    await loadInpatients();
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "出院失败");
  } finally {
    dischargeLoadingId.value = null;
  }
}

function statusRank(status: string) {
  if (status === "未完成") return 0;
  if (status === "已过期") return 1;
  return 2;
}

function tasksForHosp(hospId: number) {
  return wardTasks.value
    .filter((t) => t.hosp_id === hospId)
    .slice()
    .sort((a, b) => {
      const rankDiff = statusRank(a.status) - statusRank(b.status);
      if (rankDiff !== 0) return rankDiff;
      return new Date(a.time).getTime() - new Date(b.time).getTime();
    });
}

function formatTaskStatus(status: string) {
  if (status === "已完成") return { type: "success", label: status };
  if (status === "已过期") return { type: "danger", label: status };
  return { type: "warning", label: status };
}

onMounted(() => {
  loadWardOverview();
  loadInpatients();
});
</script>

<style scoped>
.overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-title {
  margin: 0 0 16px;
}

.title-block {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.subtitle {
  color: #94a3b8;
  margin: 4px 0 0;
}

.ward-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 28px;
  align-items: stretch;
  justify-items: stretch;
  grid-auto-rows: 1fr;
  max-width: 1100px;
  margin: 0 auto;
}

.ward-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
  width: 100%;
  min-height: 230px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.ward-card.ward-has-patient {
  border-color: #16a34a;
  background: linear-gradient(180deg, #ecfdf3 0%, #dcfce7 100%);
}

.ward-card.ward-due-soon {
  border-color: #dc2626;
  background: linear-gradient(180deg, #fff1f2 0%, #ffe2e5 100%);
  box-shadow: 0 12px 24px rgba(220, 38, 38, 0.16);
}

.ward-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.ward-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ward-badge {
  padding: 6px 10px;
  border-radius: 10px;
  background: #312e81;
  color: #fff;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.ward-type {
  color: #475569;
  font-size: 13px;
}

.ward-status {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
}

.ward-occupancy {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  color: #0f172a;
}

.bed-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(56px, 1fr));
  gap: 8px;
  flex: 1;
  padding-bottom: 4px;
}

.bed-slot {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 8px 10px;
  background: #fff;
  text-align: center;
  font-size: 13px;
  color: #0f172a;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
  min-height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bed-slot.occupied {
  border-color: #16a34a;
  background: #dcfce7;
  color: #166534;
  font-weight: 600;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header small {
  color: #94a3b8;
}

.inpatient-card .el-table {
  font-size: 14px;
}

.inpatient-table .el-button {
  width: 100%;
}

.drawer-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.record-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.record-patient {
  font-weight: 600;
  color: #0f172a;
}

.record-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #475569;
  margin-bottom: 6px;
}

.record-field {
  font-size: 13px;
  color: #0f172a;
  line-height: 1.5;
}

.mt-4 {
  margin-top: 16px;
}

.feature-card {
  min-height: 150px;
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.card-icon :deep(svg) {
  width: 24px;
  height: 24px;
}

.task-table {
  margin-top: 6px;
}

.doctor-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.home-card {
  cursor: pointer;
  transition: transform 0.2s ease;
  min-height: 160px;
}

.home-card:hover {
  transform: translateY(-4px);
}

.home-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.home-card__icon :deep(svg) {
  width: 24px;
  height: 24px;
}

.home-card h3 {
  margin: 0 0 8px;
}

.admin-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.admin-card {
  cursor: pointer;
  transition: transform 0.2s ease;
  min-height: 160px;
}

.admin-card:hover {
  transform: translateY(-4px);
}

.admin-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.admin-card__icon :deep(svg) {
  width: 24px;
  height: 24px;
}

.admin-card h3 {
  margin: 0 0 8px;
}
</style>
