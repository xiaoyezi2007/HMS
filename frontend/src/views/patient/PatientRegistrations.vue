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
    </el-card>

    <el-card class="mt-3" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>我的挂号</span>
          <small>查看当前挂号及受理状态</small>
        </div>
      </template>
      <div>
        <el-table v-if="!loading && registrations.length" :data="registrations" stripe>
          <el-table-column prop="reg_id" label="挂号号" width="100" />
          <el-table-column prop="reg_type" label="号别" width="120" />
          <el-table-column prop="fee" label="费用" width="100">
            <template #default="scope">￥{{ formatFee(scope.row.fee) }}</template>
          </el-table-column>
          <el-table-column prop="reg_date" label="挂号时间" />
          <el-table-column prop="status" label="当前状态" width="120">
            <template #default="scope">{{ normalizeStatus(scope.row.status) }}</template>
          </el-table-column>
          <el-table-column label="医生" width="160">
            <template #default="scope">{{ doctorNames[String(scope.row.doctor_id)] ?? scope.row.doctor_id }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="scope">
              <el-button type="text" @click="openDetails(scope.row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-else-if="!loading && !registrations.length" description="暂无挂号记录" />

        <div v-else style="text-align:center; padding:16px">
          <el-spin />
        </div>
      </div>
    </el-card>
  
    <el-dialog v-model="detailsDialogVisible" :title="`挂号 ${selectedRegistration?.reg_id} 详情`" width="720px">
        <div v-if="selectedRegistration">
          <p><strong>挂号号：</strong>{{ selectedRegistration.reg_id }}</p>
          <p><strong>挂号时间：</strong>{{ selectedRegistration.reg_date }}</p>
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
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  fetchDepartments,
  fetchDoctors,
  createRegistration,
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

const regForm = reactive({
  dept_id: undefined as number | undefined,
  doctor_id: undefined as number | undefined,
  reg_type: "普通号"
});

const registrations = ref<RegistrationItem[]>([]);
const loading = ref(true);

const detailsDialogVisible = ref(false);
const selectedRegistration = ref<RegistrationItem | null>(null);
const doctorName = ref<string | null>(null);
const doctorNames = ref<Record<string, string>>({});

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

async function loadRegistrations() {
  loading.value = true;
  try {
    const { data } = await fetchMyRegistrations();
    console.debug("fetchMyRegistrations response:", data);
    // ensure we always set an array
    registrations.value = Array.isArray(data) ? data : (data ? [data] : []);
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
    // 刷新我的挂号列表
    await loadRegistrations();
}

onMounted(() => {
  loadDepartments();
  loadRegistrations();
});
</script>

<style scoped>
.mt-3 {
  margin-top: 16px;
}

.card-header {
  display: flex;
  flex-direction: column;
}

.card-header small {
  color: #94a3b8;
}
</style>
