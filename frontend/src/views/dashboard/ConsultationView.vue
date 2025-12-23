<template>
  <div class="consultation">
    <el-card>
      <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
        <div>
          <h4 style="margin:0; color: var(--el-text-color-secondary); font-weight:600;">接诊</h4>
          <div v-if="patient" style="margin-top:6px; font-size:18px; font-weight:700; color:#1f2d3d;">
            患者：{{ patient.name }}
          </div>
          <el-alert
            type="warning"
            effect="dark"
            :closable="false"
            show-icon
            class="inline-tip"
            title="请先完成病历填写，再进行检查、处方或住院操作"
          />
        </div>
        <div class="header-actions">
          <el-button type="primary" link @click="openHistoryDialog" style="margin-right:8px">查询历史病历</el-button>
          <el-button type="default" @click="onExit">退出接诊</el-button>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="admitDialogVisible" title="办理住院" width="780px">
      <div class="ward-card-header">
        <div>
          <h4>病房选择</h4>
          <small>展示所属科室的病房、床位、占用情况</small>
        </div>
        <div class="ward-actions">
          <el-button type="primary" size="small" plain :loading="transferLoading" @click="onTransfer">导出转院单</el-button>
        </div>
      </div>
      <div class="doctor-select-row">
        <span class="doctor-select-label">住院主管医生</span>
        <el-select
          v-model="selectedHospDoctorId"
          placeholder="选择医生"
          size="small"
          style="width: 240px"
          filterable
          :loading="deptDoctors.length === 0"
        >
          <el-option
            v-for="doc in deptDoctors"
            :key="doc.doctor_id"
            :label="doc.title ? `${doc.name}（${doc.title}）` : doc.name"
            :value="doc.doctor_id"
          />
        </el-select>
      </div>
      <el-table
        :data="wards"
        size="small"
        border
        row-key="ward_id"
        :row-class-name="wardRowClass"
      >
        <el-table-column prop="ward_id" label="病房号" width="100" />
        <el-table-column prop="type" label="病房类型" />
        <el-table-column prop="bed_count" label="床位" width="100" />
        <el-table-column prop="occupied" label="已入住" width="100" />
        <el-table-column prop="available" label="可用" width="90" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_full ? 'danger' : 'success'">
              {{ row.is_full ? '已满' : '可安排' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="选择" width="120">
          <template #default="{ row }">
            <el-button type="text" size="small" :disabled="row.is_full" @click="selectedWardId = row.ward_id">
              {{ selectedWardId === row.ward_id ? '已选中' : '选择该病房' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="selectedWard" class="selected-info">
        当前选择：{{ selectedWard.type }} · 剩余 {{ selectedWard.available }} 床
      </div>
      <template #footer>
        <el-button @click="admitDialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="admitLoading" @click="confirmAdmit">确认住院</el-button>
      </template>
    </el-dialog>

    <el-card class="mt-3">
      <div class="option-grid">
        <div class="option-row">
          <div class="option-col">
            <el-card class="option-card" :body-style="{ padding: '8px' }">
              <div class="option-head">
                <Document class="option-icon" />
                <div>
                  <div style="font-weight:700; font-size:14px">书写病历</div>
                  <div style="color:var(--el-text-color-secondary); font-size:12px">查看或编辑当前挂号的病历</div>
                </div>
              </div>
              <div class="action-row">
                <el-button class="action-btn-yellow" size="small" @click.stop="openRecordDialog">书写</el-button>
              </div>
            </el-card>
          </div>

          <div class="option-col">
            <el-card class="option-card" :body-style="{ padding: '8px' }">
              <div class="option-head">
                <FirstAidKit class="option-icon" />
                <div>
                  <div style="font-weight:700; font-size:14px">开具检查</div>
                  <div style="color:var(--el-text-color-secondary); font-size:12px">为患者申请检验或影像检查</div>
                </div>
              </div>
              <div class="action-row">
                <el-button class="action-btn-yellow" size="small" @click="onCreateExam">开具</el-button>
              </div>
            </el-card>
          </div>

          <div class="option-col">
            <el-card class="option-card" :body-style="{ padding: '8px' }">
              <div class="option-head">
                <List class="option-icon" />
                <div>
                  <div style="font-weight:700; font-size:14px">开具处方</div>
                  <div style="color:var(--el-text-color-secondary); font-size:12px">为患者选药并生成处方</div>
                </div>
              </div>
              <div class="action-row">
                <el-button class="action-btn-yellow" size="small" @click="onOpenPrescription">开具</el-button>
              </div>
            </el-card>
          </div>

          <div class="option-col">
            <el-card class="option-card" :body-style="{ padding: '8px' }">
              <div class="option-head">
                <BedIcon class="option-icon" />
                <div>
                  <div style="font-weight:700; font-size:14px">办理住院</div>
                  <div style="color:var(--el-text-color-secondary); font-size:12px">为患者办理住院手续</div>
                </div>
              </div>
              <div class="action-row">
                <el-button class="action-btn-yellow" size="small" @click="openAdmitDialog">办理</el-button>
              </div>
            </el-card>
          </div>

          <div class="option-col">
            <el-card class="option-card" :body-style="{ padding: '8px' }">
              <div class="option-head">
                <CreditCard class="option-icon" />
                <div>
                  <div style="font-weight:700; font-size:14px">完成办理</div>
                  <div style="color:var(--el-text-color-secondary); font-size:12px">结束本次接诊并归档</div>
                </div>
              </div>
              <div class="action-row">
                <el-button type="danger" size="small" :loading="finishing" @click="onFinish">完成</el-button>
              </div>
            </el-card>
          </div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="recordDialogVisible" title="书写病历" width="520px">
      <el-form :model="recordForm" label-width="90px">
        <el-form-item label="主诉">
          <el-input v-model="recordForm.complaint" type="textarea" rows="2" />
        </el-form-item>
        <el-form-item label="诊断结果">
          <el-input v-model="recordForm.diagnosis" type="textarea" rows="2" />
        </el-form-item>
        <el-form-item label="治疗建议">
          <el-input v-model="recordForm.suggestion" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="recordLoading" @click="submitRecord">保存并完成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="examDialogVisible" title="开具检查" width="420px">
      <el-form label-width="100px">
        <el-form-item label="检查类型">
          <el-input v-model="examType" placeholder="例如：血常规 / CT" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="examDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="examLoading" @click="submitExam">开具并获取结果</el-button>
      </template>
    </el-dialog>

    <el-card class="mt-3">
      <h4>检查记录</h4>
      <div v-if="exams.length === 0">
        <small class="muted">当前无检查记录</small>
      </div>
      <el-timeline v-else>
        <el-timeline-item v-for="e in exams" :key="e.exam_id" :timestamp="new Date(e.date).toLocaleString()">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
            <div>
              <div style="font-weight:600">{{ e.type }}</div>
              <div style="color:var(--el-text-color-secondary);font-size:12px">结果：{{ e.result }}</div>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-dialog
      v-model="historyDialogVisible"
      title="查询历史病历"
      width="760px"
      destroy-on-close
    >
      <div class="history-header">
        <div>
          <div class="history-name">{{ patient?.name || '患者' }}</div>
        </div>
        <el-radio-group v-model="historyRange" size="small" class="history-range">
          <el-radio-button label="current">上次</el-radio-button>
          <el-radio-button label="7d">近7天</el-radio-button>
          <el-radio-button label="30d">近1个月</el-radio-button>
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
              <span class="history-date">{{ new Date(item.reg_date).toLocaleString() }}</span>
              <el-tag size="small" type="info">{{ normalizeRegStatus(item.status) }}</el-tag>
              <el-tag size="small" type="warning">{{ item.reg_type }}</el-tag>
              <el-tag v-if="item.is_current" size="small" type="success">本次</el-tag>
            </div>
          </template>
          <div class="history-body">
            <p><strong>主诉：</strong>{{ item.record?.complaint || "尚未填写" }}</p>
            <p><strong>诊断：</strong>{{ item.record?.diagnosis || "尚未填写" }}</p>
            <p><strong>建议：</strong>{{ item.record?.suggestion || "—" }}</p>
            <div class="history-body-meta">
              <span>就诊日期：{{ item.visit_date ? new Date(item.visit_date).toLocaleString() : "-" }}</span>
              <span>费用：{{ item.fee?.toFixed ? item.fee.toFixed(2) : item.fee }}</span>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch, defineComponent, h } from "vue";
import { FirstAidKit, Document, List, CreditCard } from "@element-plus/icons-vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { startHandling, finishHandling, submitMedicalRecord, fetchConsultationInfo, fetchMedicalRecordByReg, createExamination, fetchExaminations, fetchDoctorWards, hospitalizePatient, exportTransferForm, fetchPatientRegistrationHistory, fetchDeptDoctors, type DoctorPatientRegistrationHistoryItem, type HistoryRange, type WardInfo, type DoctorBrief } from "../../api/modules/doctor";
import { fetchPatientById } from "../../api/modules/patient";

const BedIcon = defineComponent({
  name: "BedIcon",
  inheritAttrs: false,
  setup(_props, { attrs }) {
    return () =>
      h(
        "svg",
        {
          ...attrs,
          viewBox: "0 0 24 24",
          fill: "none",
          stroke: "currentColor",
          "stroke-width": 1.5,
          "stroke-linecap": "round",
          "stroke-linejoin": "round"
        },
        [
          h("path", { d: "M3.5 11.5 12 4l8.5 7.5V20a0.8 0.8 0 0 1-0.8 0.8H4.3A0.8 0.8 0 0 1 3.5 20Z" }),
          h("path", { d: "M12 10.5v5" }),
          h("path", { d: "M9.5 13h5" })
        ]
      );
  }
});

const route = useRoute();
const router = useRouter();
const regId = Number(route.params.reg_id || route.query.reg_id || 0);
const patientIdQuery = Number(route.query.patient_id || 0);
const currentDoctorId = ref<number | null>(null);

const patient = ref(null as any);
const recordDialogVisible = ref(false);
const recordLoading = ref(false);
const finishing = ref(false);

const recordForm = reactive({ complaint: "", diagnosis: "", suggestion: "" });
const exams = ref([] as Array<any>);
const examDialogVisible = ref(false);
const examType = ref("");
const examLoading = ref(false);
const wards = ref([] as Array<WardInfo>);
const selectedWardId = ref<number | null>(null);
const admitLoading = ref(false);
const transferLoading = ref(false);
const admitDialogVisible = ref(false);
const deptDoctors = ref<DoctorBrief[]>([]);
const selectedHospDoctorId = ref<number | null>(null);

// 历史病历
const historyDialogVisible = ref(false);
const historyRange = ref<HistoryRange>("current");
const historyItems = ref<DoctorPatientRegistrationHistoryItem[]>([]);
const historyLoading = ref(false);
const historyError = ref("");
const historyActivePanels = ref<string[]>([]);

async function ensureStarted() {
  // 检查挂号当前状态，仅在仍为“排队中/待就诊/WAITING”时才调用 startHandling
  try {
    const { data } = await fetchConsultationInfo(regId);
    const reg = data?.registration;
    if (data?.patient) {
      patient.value = data.patient;
    }
    if (reg?.doctor_id) {
      currentDoctorId.value = reg.doctor_id;
    }
    const status = reg?.status;
    if (isWaitingStatus(status)) {
      try {
        await startHandling(regId);
        ElMessage.success("已开始办理");
      } catch (err: any) {
        const msg = err?.response?.data?.detail;
        if (msg && !msg.includes("只有排队中的挂号可以开始办理")) {
          ElMessage.error(msg ?? "开始办理失败");
        }
      }
    } else {
      // 如果不是等待状态，直接进入接诊页继续操作
    }
  } catch (err: any) {
    // 若后端 info 接口不可用或返回错误，回退到原有行为：尝试用 query patientId 加载患者信息
    const msg = err?.response?.data?.detail ?? err?.message ?? null;
    if (msg) {
      console.debug("fetchConsultationInfo failed:", msg);
    }
    // 继续，不阻塞页面
  }
}

async function loadHistory() {
  const pid = patient.value?.patient_id || patientIdQuery;
  if (!pid) {
    historyError.value = "未获取到患者信息";
    historyItems.value = [];
    return;
  }
  historyLoading.value = true;
  historyError.value = "";
  try {
    // 后端的 range=current 仅返回当前挂号；为了拿到“最近一次已完成”的记录，这里在上次视图下用 30 天已完成记录再行筛选
    const rangeParam: HistoryRange = historyRange.value === "current" ? "30d" : historyRange.value;
    const { data } = await fetchPatientRegistrationHistory(pid, { range: rangeParam, current_reg_id: regId });
    let items = data || [];

    if (historyRange.value === "current") {
      // “上次”仅展示最近一次已完成的病历（若存在），否则为空
      const sorted = [...items].sort((a, b) => new Date(b.reg_date).getTime() - new Date(a.reg_date).getTime());
      const latestFinished = sorted.find((x) => isFinishedStatus(x.status) && x.reg_id !== regId)
        ?? sorted.find((x) => isFinishedStatus(x.status))
        ?? null;
      items = latestFinished ? [latestFinished] : [];
    }

    historyItems.value = items;
    historyActivePanels.value = items.length ? [String(items[0].reg_id)] : [];
  } catch (err: any) {
    historyError.value = err?.response?.data?.detail ?? "查询历史病历失败";
    historyItems.value = [];
  } finally {
    historyLoading.value = false;
  }
}

function openHistoryDialog() {
  historyDialogVisible.value = true;
  void loadHistory();
}

function isWaitingStatus(s: string | null | undefined) {
  if (!s) return false;
  const v = String(s).toLowerCase();
  return v === "排队中" || v === "待就诊" || v === "waiting" || v === "wait";
}

async function loadPatient() {
  // 优先通过 query 中的 patient_id 获取患者；如果没有，则请求后端的 consultation info
  if (patientIdQuery) {
    try {
      const { data } = await fetchPatientById(patientIdQuery);
      patient.value = data;
      return;
    } catch (err) {
      // fallback to consultation info
    }
  }

  try {
    const { data } = await fetchConsultationInfo(regId);
    // data.patient 包含患者信息
    patient.value = data.patient;
  } catch (err) {
    // ignore — 页面仍然可用
  }
}

async function openRecordDialog() {
  // 尝试拉取已有病历并填充表单
  try {
    const { data } = await fetchMedicalRecordByReg(regId);
    recordForm.complaint = data.complaint || "";
    recordForm.diagnosis = data.diagnosis || "";
    recordForm.suggestion = data.suggestion || "";
  } catch (err: any) {
    // 404 表示没有病历，清空表单以便新建
    if (!(err?.response?.status === 404)) {
      console.warn("加载已有病历失败", err);
      ElMessage.error(err?.response?.data?.detail ?? "加载病历失败");
    } else {
      recordForm.complaint = "";
      recordForm.diagnosis = "";
      recordForm.suggestion = "";
    }
  }
  recordDialogVisible.value = true;
}

async function loadExams() {
  try {
    const { data } = await fetchExaminations(regId);
    exams.value = data || [];
  } catch (err: any) {
    // ignore if not available yet
    exams.value = [];
  }
}

async function submitRecord() {
  if (!recordForm.complaint || !recordForm.diagnosis) {
    ElMessage.warning("主诉和诊断为必填项");
    return;
  }
  recordLoading.value = true;
  try {
    const { data } = await submitMedicalRecord(regId, { ...recordForm });
    ElMessage.success("病历提交成功");
    recordDialogVisible.value = false;
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "提交病历失败");
  } finally {
    recordLoading.value = false;
  }
}

async function onOpenPrescription() {
  // 始终跳转到医生处方页面，新页面会在必要时自动建立最小病历并提交处方
  router.push({ name: "doctor-prescription", params: { reg_id: String(regId) } });
}

async function onCreateExam() {
  // open dialog to enter exam type
  examType.value = "";
  examDialogVisible.value = true;
}

async function submitExam() {
  if (!examType.value) {
    ElMessage.warning("请填写检查类型");
    return;
  }
  examLoading.value = true;
  try {
    const { data } = await createExamination(regId, { type: examType.value });
    // backend returns created exam with randomized result
    exams.value.unshift(data);
    ElMessage.success(`检查已开具：结果 ${data.result}`);
    examDialogVisible.value = false;
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "开具检查失败");
  } finally {
    examLoading.value = false;
  }
}

function openAdmitDialog() {
  admitDialogVisible.value = true;
  void loadWards();
  void loadDeptDoctors();
}

async function onFinish() {
  finishing.value = true;
  try {
    await finishHandling(regId);
    ElMessage.success("已完成办理");
    router.push({ path: "/workspace/doctor" });
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "完成办理失败");
  } finally {
    finishing.value = false;
  }
}

watch(historyDialogVisible, (visible) => {
  if (!visible) {
    historyItems.value = [];
    historyError.value = "";
    historyActivePanels.value = [];
  }
});

function onExit() {
  // 仅退出接诊页面，不改变挂号状态（保持为就诊中）
  ElMessage.info("暂时退出接诊，可稍后继续处理~");
  router.push({ path: "/workspace/doctor" });
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

function isFinishedStatus(value?: string | null) {
  if (!value) return false;
  const v = String(value).toUpperCase();
  return v === "FINISHED" || v === "已完成";
}

async function loadWards() {
  try {
    const { data } = await fetchDoctorWards();
    wards.value = data;
    const preferred = data.find((w) => !w.is_full);
    if (selectedWardId.value && data.some((w) => w.ward_id === selectedWardId.value && !w.is_full)) {
      return;
    }
    selectedWardId.value = preferred?.ward_id ?? data[0]?.ward_id ?? null;
  } catch (err: any) {
    console.error("loadWards error", err);
  }
}

async function loadDeptDoctors() {
  try {
    const { data } = await fetchDeptDoctors();
    deptDoctors.value = data || [];
    const preferredId = currentDoctorId.value;
    if (selectedHospDoctorId.value && data.some((d) => d.doctor_id === selectedHospDoctorId.value)) {
      return;
    }
    if (preferredId && data.some((d) => d.doctor_id === preferredId)) {
      selectedHospDoctorId.value = preferredId;
      return;
    }
    selectedHospDoctorId.value = data[0]?.doctor_id ?? null;
  } catch (err) {
    console.error("loadDeptDoctors error", err);
  }
}

const selectedWard = computed(() => wards.value.find((w) => w.ward_id === selectedWardId.value) ?? null);

async function confirmAdmit() {
  if (!selectedWardId.value) {
    ElMessage.warning("请先选择一个可用病房");
    return;
  }
  if (!selectedHospDoctorId.value) {
    ElMessage.warning("请选择住院主管医生");
    return;
  }
  const ward = wards.value.find((w) => w.ward_id === selectedWardId.value);
  if (!ward || ward.is_full) {
    ElMessage.warning("所选病房已满，请选择其他病房");
    return;
  }
  admitLoading.value = true;
  try {
    await hospitalizePatient(regId, { ward_id: selectedWardId.value, hosp_doctor_id: selectedHospDoctorId.value });
    ElMessage.success("住院办理成功");
    admitDialogVisible.value = false;
    await loadWards();
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "住院办理失败");
  } finally {
    admitLoading.value = false;
  }
}

async function onTransfer() {
  if (!regId) {
    return;
  }
  transferLoading.value = true;
  try {
    const response = await exportTransferForm(regId);
    const blob = new Blob([response.data], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `transfer_${regId}.docx`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "导出转院单失败");
  } finally {
    transferLoading.value = false;
  }
}

function wardRowClass({ row }: { row: WardInfo }) {
  if (row.ward_id === selectedWardId.value) {
    return "is-selected-row";
  }
  if (row.is_full) {
    return "is-full-row";
  }
  return "";
}

onMounted(async () => {
  await ensureStarted();
  await loadPatient();
  await loadExams();
  await loadWards();
  await loadDeptDoctors();
});

watch(historyRange, () => {
  if (historyDialogVisible.value) {
    void loadHistory();
  }
});
</script>

<style scoped>
.mt-3 {
  margin-top: 16px;
}

.option-grid {
  --card-bg: #ffffff;
}
.option-card {
  cursor: pointer;
  transition: box-shadow .18s ease, transform .12s ease;
  border-radius: 8px;
  min-height: 130px;
}

.inline-tip {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 8px;
}
.option-card:hover {
  box-shadow: 0 6px 14px rgba(13,27,42,0.10);
  transform: translateY(-2px);
}
.option-icon {
  font-size: 20px;
  color: var(--el-color-primary);
  width: 44px;
  height: 44px;
  flex-shrink: 0;
}

.option-row {
  display: flex;
  gap: 8px;
  justify-content: space-between;
  align-items: stretch;
  flex-wrap: wrap;
}
.option-col {
  flex: 0 0 calc(20% - 6.4px);
  box-sizing: border-box;
}
@media (max-width: 900px) {
  .option-col { flex: 0 0 48%; margin-bottom:8px; }
}
@media (max-width: 600px) {
  .option-col { flex: 0 0 100%; }
}

/* Ensure cards are equal height and internal layout places action at bottom */
.option-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
}
.option-card > .el-card__body {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
  padding: 8px !important;
}
.option-col { min-height: 84px; }

.option-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 72px;
}
.option-head > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  justify-content: flex-start;
}

/* Align action button to card bottom/right */
.action-row {
  display: flex;
  justify-content: flex-end;
  align-items: flex-end;
  margin-top: auto; /* push buttons to the same baseline across cards */
}

.action-btn-yellow {
  background: #fcd34d;
  border-color: #fcd34d;
  color: #ffffff;
}

.action-btn-yellow:hover,
.action-btn-yellow:focus,
.action-btn-yellow:active {
  background: #fbbf24;
  border-color: #fbbf24;
  color: #ffffff;
}

.mt-3 { margin-top: 16px; }
.ward-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.ward-actions {
  display: flex;
  gap: 8px;
}
.doctor-select-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
}
.doctor-select-label {
  width: 96px;
  color: var(--el-text-color-regular);
  font-size: 14px;
}
.is-selected-row {
  background: rgba(59, 130, 246, 0.08);
}
.is-full-row {
  background: rgba(248, 113, 113, 0.08);
}
.selected-info {
  margin-top: 12px;
  color: #475569;
  font-size: 14px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.history-name {
  font-weight: 700;
  font-size: 15px;
}
.history-range {
  display: flex;
  gap: 8px;
}
.history-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.history-date {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.history-body {
  padding: 8px 4px 4px 4px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.history-body-meta {
  display: flex;
  gap: 16px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.history-alert {
  margin-bottom: 12px;
}
</style>
