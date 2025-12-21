<template>
  <div class="patient-registrations">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>挂号申请</span>
          <small>请选择科室和医生，系统自动计算费用</small>
        </div>
      </template>
      <el-form label-width="80px">
        <el-form-item label="科室">
          <el-select v-model="regForm.dept_id" placeholder="请选择科室" @change="onDeptChange">
            <el-option v-for="dept in departments" :key="dept.dept_id" :label="dept.dept_name" :value="dept.dept_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="号别">
          <el-radio-group v-model="regForm.reg_type">
            <el-radio-button label="普通号" />
            <el-radio-button label="专家号" />
          </el-radio-group>
        </el-form-item>
        <el-form-item label="医生">
          <el-select
            v-model="regForm.doctor_id"
            placeholder="请选择医生"
            :disabled="!regForm.dept_id || !regForm.reg_type || doctorLoading"
          >
            <el-option
              v-for="doc in filteredDoctors"
              :key="doc.doctor_id"
              :label="`${doc.name} / ${normalizeDoctorLevel(doc.title)}`"
              :value="doc.doctor_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="就诊日期">
          <el-date-picker
            v-model="regForm.visit_date"
            type="date"
            placeholder="请选择就诊日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :disabled-date="disabledPastDates"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="success" :loading="regLoading" @click="submitRegistration">提交挂号</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="mt-3" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>我的挂号</span>
          <small>查看当前挂号及受理状态</small>
        </div>
      </template>
      <div class="filter-row">
        <el-checkbox-group v-model="statusFilters" class="filter-group">
          <el-checkbox label="ALL">全部</el-checkbox>
          <el-checkbox label="排队中">排队中</el-checkbox>
          <el-checkbox label="就诊中">就诊中</el-checkbox>
          <el-checkbox label="已过期">已过期</el-checkbox>
          <el-checkbox label="已完成">已完成</el-checkbox>
          <el-checkbox label="已取消">已取消</el-checkbox>
        </el-checkbox-group>
      </div>
      <div>
        <el-table v-if="!loading && filteredRegistrations.length" :data="filteredRegistrations" stripe>
          <el-table-column prop="reg_id" label="序号" width="100" />
          <el-table-column prop="reg_type" label="号别" width="120" />
          <el-table-column prop="fee" label="费用" width="100">
            <template #default="scope">￥{{ formatFee(scope.row.fee) }}</template>
          </el-table-column>
          <el-table-column label="挂号时间" min-width="260">
            <template #default="scope">
              <span>{{ formatDateTimeText(scope.row.reg_date) }}</span>
              <span style="margin-left: 10px; color: var(--el-text-color-secondary)">就诊：{{ formatDateText(scope.row.visit_date) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="当前状态" width="120">
            <template #default="scope">{{ deriveRegistrationStatus(scope.row) }}</template>
          </el-table-column>
          <el-table-column label="医生" width="160">
            <template #default="scope">{{ doctorNames[String(scope.row.doctor_id)] ?? scope.row.doctor_id }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="scope">
              <el-button type="text" @click="openDetails(scope.row)">查看详情</el-button>
              <el-button
                v-if="isCancellable(scope.row)"
                type="text"
                :loading="cancelLoading[String(scope.row.reg_id)] === true"
                @click="cancelMyRegistration(scope.row)"
              >取消</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-else-if="!loading && !filteredRegistrations.length" description="暂无挂号记录" />

        <div v-else style="text-align:center; padding:16px">
          <el-spin />
        </div>
      </div>
    </el-card>
  
    <el-dialog v-model="detailsDialogVisible" :title="`挂号 ${selectedRegistration?.reg_id} 详情`" width="720px">
        <div v-if="selectedRegistration">
          <p><strong>挂号号：</strong>{{ selectedRegistration.reg_id }}</p>
          <p><strong>挂号时间：</strong>{{ formatDateTimeText(selectedRegistration.reg_date) }}</p>
          <p><strong>就诊日期：</strong>{{ formatDateText(selectedRegistration.visit_date) }}</p>
          <p><strong>号别：</strong>{{ selectedRegistration.reg_type }}</p>
          <p><strong>费用：</strong>￥{{ formatFee(selectedRegistration.fee) }}</p>
          <p><strong>当前状态：</strong>{{ normalizeStatus(selectedRegistration.status) }}</p>
          <p><strong>医生：</strong>{{ doctorName ?? selectedRegistration.doctor_id }}</p>

          <el-divider />
          <div>
            <h4>病历摘要</h4>
            <div v-if="detailLoading">加载中……</div>
            <div v-else>
              <div v-if="registrationDetail.record">
                <p><strong>主诉：</strong>{{ registrationDetail.record.complaint }}</p>
                <p><strong>诊断：</strong>{{ registrationDetail.record.diagnosis }}</p>
                <p><strong>建议：</strong>{{ registrationDetail.record.suggestion || '—' }}</p>
              </div>
              <div v-else>
                <p>暂无病历记录</p>
              </div>
            </div>
          </div>

          <el-divider />
          <div>
            <h4>处方</h4>
            <div v-if="detailLoading">加载中……</div>
            <div v-else>
              <div v-if="registrationDetail.prescriptions && registrationDetail.prescriptions.length">
                <el-collapse>
                  <el-collapse-item v-for="p in registrationDetail.prescriptions" :title="`处方 ${p.pres_id} - ￥${p.total_amount}`" :name="String(p.pres_id)" :key="p.pres_id">
                    <el-table :data="p.details" style="width:100%" size="small">
                      <el-table-column prop="medicine_name" label="药品" />
                      <el-table-column prop="quantity" label="数量" width="80" />
                      <el-table-column prop="usage" label="用法" />
                    </el-table>
                  </el-collapse-item>
                </el-collapse>
              </div>
              <div v-else>
                <p>暂无处方</p>
              </div>
            </div>
          </div>

          <el-divider />
          <div>
            <h4>检查</h4>
            <div v-if="detailLoading">加载中……</div>
            <div v-else>
              <div v-if="registrationDetail.exams && registrationDetail.exams.length">
                <el-table :data="registrationDetail.exams" style="width:100%" size="small">
                  <el-table-column prop="type" label="检查类型" />
                  <el-table-column prop="result" label="结果" />
                  <el-table-column prop="date" label="时间">
                    <template #default="{ row }">{{ new Date(row.date).toLocaleString() }}</template>
                  </el-table-column>
                  <el-table-column prop="reg_id" label="挂号ID" width="100" />
                </el-table>
              </div>
              <div v-else>
                <p>暂无检查记录</p>
              </div>
            </div>

            <el-divider />
            <div>
              <h4>住院</h4>
              <div v-if="detailLoading">加载中……</div>
              <div v-else>
                <p v-if="registrationDetail.admissions && registrationDetail.admissions.length">住院信息（暂时占位）</p>
                <p v-else>暂无住院记录</p>
              </div>
            </div>
          </div>
        </div>
        <template #footer>
          <el-button @click="closeDetails">关闭</el-button>
        </template>
      </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  fetchDepartments,
  fetchDoctors,
  createRegistration,
  cancelRegistration,
  fetchMyRegistrations,
  fetchDoctorById,
  fetchRegistrationDetail,
  type Department,
  type DoctorItem,
  type RegistrationItem
} from "../../api/modules/patient";

const departments = ref<Department[]>([]);
const doctors = ref<DoctorItem[]>([]);
const doctorLoading = ref(false);
const regLoading = ref(false);

function getTodayYmd() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

const regForm = reactive({
  dept_id: undefined as number | undefined,
  doctor_id: undefined as number | undefined,
  reg_type: "普通号",
  visit_date: getTodayYmd()
});

const filteredDoctors = computed(() => {
  const type = regForm.reg_type;
  const expectedLevel = type === "专家号" ? "专家医师" : "普通医师";
  return doctors.value.filter((d) => normalizeDoctorLevel(d.title) === expectedLevel);
});

const registrations = ref<RegistrationItem[]>([]);
const loading = ref(true);

const cancelLoading = ref<Record<string, boolean>>({});

const detailsDialogVisible = ref(false);
const selectedRegistration = ref<RegistrationItem | null>(null);
const doctorName = ref<string | null>(null);
const doctorNames = ref<Record<string, string>>({});

// 多选筛选：默认展示全部
const statusFilters = ref<string[]>(["ALL"]);

function openDetails(reg: RegistrationItem) {
  selectedRegistration.value = reg;
  doctorName.value = null;
  // fetch doctor name for better UX
  if (reg.doctor_id) {
    fetchDoctorById(reg.doctor_id).then(r => {
      doctorName.value = (r.data && (r.data as any).name) || String(reg.doctor_id);
    }).catch(() => {
      doctorName.value = String(reg.doctor_id);
    });
  }
  detailsDialogVisible.value = true;
  // fetch registration detail (record, prescriptions, etc.) for the dialog
  loadRegistrationDetail(reg.reg_id);
}

const registrationDetail = ref<any>({ record: null, prescriptions: [], exams: [], admissions: [] });
const detailLoading = ref(false);

async function loadRegistrationDetail(regId: number) {
  detailLoading.value = true;
  registrationDetail.value = { record: null, prescriptions: [], exams: [], admissions: [] };
  try {
    const res = await fetchRegistrationDetail(regId);
    registrationDetail.value = res.data ?? registrationDetail.value;
  } catch (e) {
    console.error("fetchRegistrationDetail error", e);
  } finally {
    detailLoading.value = false;
  }
}

async function loadDoctorNamesFor(regs: RegistrationItem[]) {
  const ids = Array.from(new Set(regs.map(r => r.doctor_id).filter(Boolean)));
  for (const id of ids) {
    const key = String(id);
    if (doctorNames.value[key]) continue;
    try {
      const res = await fetchDoctorById(id);
      doctorNames.value[key] = (res.data && (res.data as any).name) || key;
    } catch (e) {
      doctorNames.value[key] = key;
    }
  }
}

function closeDetails() {
  detailsDialogVisible.value = false;
  selectedRegistration.value = null;
}



// removed: navigation to separate medical records page (now details include record/prescriptions)

function formatFee(f: number | null | undefined) {
  const n = Number(f ?? 0);
  return n.toFixed(2);
}

function normalizeDoctorLevel(value: string | null | undefined) {
  if (!value) return "";
  return value === "主治医师" ? "专家医师" : value;
}

watch(
  () => regForm.reg_type,
  () => {
    // 号别切换后重置医生选择，避免选到不匹配的医生
    regForm.doctor_id = undefined;
  }
);

function normalizeStatus(s: string | null | undefined) {
  if (!s) return "未知";
  // accept both old and new value sets
  if (s === "待就诊") return "排队中";
  if (s === "办理中") return "就诊中";
  if (s === "已就诊" || s === "已结束") return "已完成";
  // already new values
  if (s === "排队中" || s === "就诊中" || s === "已完成" || s === "已取消") return s;
  return s;
}

function parseLocalYmd(value: string) {
  const raw = (String(value).split("T")[0] ?? "").trim();
  if (!raw) return null;
  const [y, m, d] = raw.split("-").map((v) => Number(v));
  if (!y || !m || !d) return null;
  const dt = new Date(y, m - 1, d);
  dt.setHours(0, 0, 0, 0);
  return dt;
}

function isRegistrationExpired(reg: RegistrationItem) {
  if (!reg.visit_date) return false;
  const visit = parseLocalYmd(reg.visit_date);
  if (!visit) return false;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  if (visit >= today) return false;

  const s = normalizeStatus(reg.status);
  return s !== "已完成" && s !== "已取消";
}

function deriveRegistrationStatus(reg: RegistrationItem) {
  return isRegistrationExpired(reg) ? "已过期" : normalizeStatus(reg.status);
}

const filteredRegistrations = computed(() => {
  const filters = statusFilters.value;
  if (!filters.length || filters.includes("ALL")) return registrations.value;
  const set = new Set(filters);
  return registrations.value.filter((r) => set.has(deriveRegistrationStatus(r)));
});

watch(
  statusFilters,
  (next, prev) => {
    const nextHasAll = next.includes("ALL");
    const prevHasAll = prev.includes("ALL");

    // 用户勾选“全部”：清空其他选项，仅保留 ALL。
    if (nextHasAll && !prevHasAll) {
      statusFilters.value = ["ALL"];
      return;
    }

    // 已经选了“全部”时，用户再勾选具体状态：自动取消“全部”，让筛选生效。
    if (prevHasAll && nextHasAll && next.length > 1) {
      statusFilters.value = next.filter((v) => v !== "ALL");
      return;
    }

    // 如果用户把所有选项都取消了，则回退到“全部”。
    if (!next.length) {
      statusFilters.value = ["ALL"];
      return;
    }
  },
  { deep: true }
);

function isCancellable(reg: RegistrationItem) {
  return deriveRegistrationStatus(reg) === "排队中";
}

function formatDateTimeText(value?: unknown) {
  if (value === undefined || value === null) return "-";
  return String(value).replace("T", " ");
}

function formatDateText(value?: unknown) {
  if (value === undefined || value === null) return "-";
  // backend may return YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss; normalize for display
  return String(value).split("T")[0];
}

function disabledPastDates(time: Date) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const d = new Date(time);
  d.setHours(0, 0, 0, 0);
  return d < today;
}

async function cancelMyRegistration(reg: RegistrationItem) {
  if (!isCancellable(reg)) return;
  try {
    await ElMessageBox.confirm(
      `确认取消挂号 ${reg.reg_id} 吗？取消后需要重新挂号才能就诊。`,
      "取消挂号",
      { type: "warning", confirmButtonText: "确认取消", cancelButtonText: "暂不取消" }
    );
  } catch {
    return;
  }

  const key = String(reg.reg_id);
  cancelLoading.value[key] = true;
  try {
    await cancelRegistration(reg.reg_id);
    ElMessage.success("挂号已取消");
    if (selectedRegistration.value?.reg_id === reg.reg_id) {
      // keep dialog open but refresh list/detail
      await loadRegistrationDetail(reg.reg_id);
    }
    await loadRegistrations();
  } catch (e: any) {
    const msg = e?.response?.data?.detail || "取消挂号失败";
    ElMessage.error(msg);
  } finally {
    cancelLoading.value[key] = false;
  }
}

async function loadRegistrations() {
  loading.value = true;
  try {
    const { data } = await fetchMyRegistrations();
    console.debug("fetchMyRegistrations response:", data);
    // ensure we always set an array
    const rows = Array.isArray(data) ? data : (data ? [data] : []);
    // sort newest first (fallback to reg_id)
    rows.sort((a, b) => {
      const ta = Date.parse(a.reg_date as any);
      const tb = Date.parse(b.reg_date as any);
      const va = Number.isFinite(ta) ? ta : 0;
      const vb = Number.isFinite(tb) ? tb : 0;
      if (vb !== va) return vb - va;
      return (b.reg_id ?? 0) - (a.reg_id ?? 0);
    });
    registrations.value = rows;
    // load doctor names for the fetched registrations
    await loadDoctorNamesFor(registrations.value);
  } catch (err: any) {
    console.error("fetchMyRegistrations error", err);
    const detail = err?.response?.data?.detail ?? err?.message ?? String(err);
    // show user-friendly message when request fails
    ElMessage.error(`获取挂号列表失败：${detail}`);
    registrations.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadDepartments() {
  const { data } = await fetchDepartments();
  departments.value = data;
}

async function onDeptChange(deptId: number) {
  if (!deptId) {
    doctors.value = [];
    regForm.doctor_id = undefined;
    return;
  }
  doctorLoading.value = true;
  try {
    const { data } = await fetchDoctors(deptId);
    doctors.value = data;
    // 科室切换后重置医生选择
    regForm.doctor_id = undefined;
  } finally {
    doctorLoading.value = false;
  }
}

async function submitRegistration() {
  if (!regForm.doctor_id) {
    ElMessage.warning("请选择医生");
    return;
  }
  if (!regForm.visit_date) {
    ElMessage.warning("请选择就诊日期");
    return;
  }
  regLoading.value = true;
  try {
    await createRegistration({ doctor_id: regForm.doctor_id, reg_type: regForm.reg_type, visit_date: regForm.visit_date });
    ElMessage.success("挂号成功，等待医生处理");
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail ?? "挂号失败");
  } finally {
    regLoading.value = false;
  }
    // 刷新我的挂号列表
    await loadRegistrations();
}

onMounted(() => {
  // Ensure local date default (avoid UTC toISOString() off-by-one).
  if (!regForm.visit_date) regForm.visit_date = getTodayYmd();
  loadDepartments();
  loadRegistrations();
});
</script>

<style scoped>
.mt-3 {
  margin-top: 16px;
}

.filter-row {
  margin-bottom: 12px;
}

.filter-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.card-header {
  display: flex;
  flex-direction: column;
}

.card-header small {
  color: #94a3b8;
}
</style>
